"""Helpers to provide SQLAlchemy sessions wired from Envoxy config by server_key.

This module keeps the API extremely small so developers only need to pick a
`server_key` (already configured in the application's config) and get a safe
session context or decorator. The underlying Engine and SessionManager are
cached per server_key.
"""

from contextlib import contextmanager
from typing import Dict

from ...utils.config import Config
from ...utils.logs import Log
from ..exceptions import DatabaseException
from ...postgresql.sqlalchemy.session import EnvoxySessionManager

# Cache managers per server_key
_MANAGERS: Dict[str, EnvoxySessionManager] = {}


def _build_url_from_conf(conf: dict) -> str:
    # Expect the same keys used by the psycopg2 client
    _user = conf.get("user") or ""
    _passwd = conf.get("passwd") or ""
    _host = conf.get("host") or "localhost"
    _port = conf.get("port") or 5432
    _dbname = conf.get("db") or ""

    # Note: keep it simple and explicit. If credentials are provided elsewhere
    # projects can pre-compose a DSN in the config instead.
    # URL-escaping is intentionally minimal here; for complex setups provide
    # a full engine via EnvoxySessionManager(engine=...)
    return f"postgresql+psycopg2://{_user}:{_passwd}@{_host}:{_port}/{_dbname}"


def get_manager(server_key: str) -> EnvoxySessionManager:
    """Return a cached EnvoxySessionManager for the given server_key.

    The function reads the `psql_servers` section from the global `Config`.
    """
    if server_key in _MANAGERS:
        return _MANAGERS[server_key]

    _psql_confs = Config.get("psql_servers")
    if not _psql_confs:
        raise DatabaseException("No psql_servers configuration found")

    _conf = _psql_confs.get(server_key)
    if not _conf:
        raise DatabaseException(f"No psql server config for server_key: {server_key}")

    # If the consumer provided a full dsn/url in conf, use it
    _url = _conf.get("dsn") or _conf.get("url") or _build_url_from_conf(_conf)

    # Extract pool tuning options if provided by the configuration
    _engine_kwargs = {}
    _pool_size = _conf.get("pool_size")
    _max_overflow = _conf.get("max_overflow")
    _pool_timeout = _conf.get("pool_timeout")
    if _pool_size is not None:
        _engine_kwargs["pool_size"] = int(_pool_size)
    if _max_overflow is not None:
        _engine_kwargs["max_overflow"] = int(_max_overflow)
    if _pool_timeout is not None:
        _engine_kwargs["pool_timeout"] = int(_pool_timeout)

    _mgr = EnvoxySessionManager(url=_url, engine_kwargs=_engine_kwargs)
    _MANAGERS[server_key] = _mgr

    Log.info(f"Created EnvoxySessionManager for server_key={server_key}")

    return _mgr


def get_default_server_key() -> str:
    """Return a sensible default server_key: env var or first configured key."""

    _psql_confs = Config.get("psql_servers") or {}

    # prefer configuration 'default' key if set
    _default = _psql_confs.get("default")
    if isinstance(_default, str) and _default in _psql_confs:
        return _default

    # fallback: first key
    try:
        return next(iter(_psql_confs.keys()))
    except StopIteration as _exc:
        raise DatabaseException("No psql_servers configured") from _exc


def validate_server_key(server_key: str) -> bool:
    _psql_confs = Config.get("psql_servers") or {}
    return server_key in _psql_confs


def dispose_manager(server_key: str) -> None:
    """Dispose and remove the cached manager for server_key, if present."""
    _mgr = _MANAGERS.get(server_key)
    if not _mgr:
        return
    try:
        _mgr.dispose()
    except Exception as _e:
        Log.error(f"Error disposing manager for {server_key} - {_e}")
    try:
        del _MANAGERS[server_key]
    except KeyError:
        pass


def dispose_all() -> None:
    """Dispose all cached managers."""
    _keys = list(_MANAGERS.keys())
    for _key in _keys:
        dispose_manager(_key)


@contextmanager
def session_scope(server_key: str):
    """Context manager yielding a SQLAlchemy Session bound to the server_key.

    Usage:
        with session_scope('primary') as session:
            session.add(obj)
    """
    _mgr = get_manager(server_key)
    with _mgr.session_scope() as _session:
        yield _session


def transactional(server_key: str):
    """Decorator that runs the wrapped function inside a transaction for
    the given server_key. The wrapped function will receive a `session`
    keyword argument unless the caller provides one.
    """
    _mgr = get_manager(server_key)
    return _mgr.transactional()


__all__ = [
    "get_manager",
    "get_default_server_key",
    "validate_server_key",
    "dispose_manager",
    "dispose_all",
    "session_scope",
    "transactional",
]
