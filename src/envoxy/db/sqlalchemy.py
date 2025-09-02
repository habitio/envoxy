"""Helpers to provide SQLAlchemy sessions wired from Envoxy config by server_key.

This module keeps the API extremely small so developers only need to pick a
`server_key` (already configured in the application's config) and get a safe
session context or decorator. The underlying Engine and SessionManager are
cached per server_key.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Dict
import logging

from sqlalchemy.engine import Engine

from ..utils.config import Config
from ..db.exceptions import DatabaseException
from envoxy.sqlalchemy.session import EnvoxySessionManager

logger = logging.getLogger(__name__)

# Cache managers per server_key
_MANAGERS: Dict[str, EnvoxySessionManager] = {}


def _build_url_from_conf(conf: dict) -> str:
    # Expect the same keys used by the psycopg2 client
    user = conf.get('user') or ''
    passwd = conf.get('passwd') or ''
    host = conf.get('host') or 'localhost'
    port = conf.get('port') or 5432
    dbname = conf.get('db') or ''

    # Note: keep it simple and explicit. If credentials are provided elsewhere
    # projects can pre-compose a DSN in the config instead.
    # URL-escaping is intentionally minimal here; for complex setups provide
    # a full engine via EnvoxySessionManager(engine=...)
    return f"postgresql+psycopg2://{user}:{passwd}@{host}:{port}/{dbname}"


def get_manager(server_key: str) -> EnvoxySessionManager:
    """Return a cached EnvoxySessionManager for the given server_key.

    The function reads the `psql_servers` section from the global `Config`.
    """
    if server_key in _MANAGERS:
        return _MANAGERS[server_key]

    psql_confs = Config.get('psql_servers')
    if not psql_confs:
        raise DatabaseException('No psql_servers configuration found')

    conf = psql_confs.get(server_key)
    if not conf:
        raise DatabaseException(f'No psql server config for server_key: {server_key}')

    # If the consumer provided a full dsn/url in conf, use it
    url = conf.get('dsn') or conf.get('url') or _build_url_from_conf(conf)

    # Extract pool tuning options if provided by the configuration
    engine_kwargs = {}
    pool_size = conf.get('pool_size')
    max_overflow = conf.get('max_overflow')
    pool_timeout = conf.get('pool_timeout')
    if pool_size is not None:
        engine_kwargs['pool_size'] = int(pool_size)
    if max_overflow is not None:
        engine_kwargs['max_overflow'] = int(max_overflow)
    if pool_timeout is not None:
        engine_kwargs['pool_timeout'] = int(pool_timeout)

    mgr = EnvoxySessionManager(url=url, engine_kwargs=engine_kwargs)
    _MANAGERS[server_key] = mgr
    logger.info("Created EnvoxySessionManager for server_key=%s", server_key)
    return mgr


def get_default_server_key() -> str:
    """Return a sensible default server_key: env var or first configured key."""
    import os

    psql_confs = Config.get('psql_servers') or {}
    # prefer explicit environment variable
    env_key = os.getenv('ENVOXY_PSQL_SERVER')
    if env_key:
        return env_key

    # prefer configuration 'default' key if set
    default = psql_confs.get('default')
    if isinstance(default, str) and default in psql_confs:
        return default

    # fallback: first key
    try:
        return next(iter(psql_confs.keys()))
    except StopIteration as exc:
        raise DatabaseException('No psql_servers configured') from exc


def validate_server_key(server_key: str) -> bool:
    psql_confs = Config.get('psql_servers') or {}
    return server_key in psql_confs


def dispose_manager(server_key: str) -> None:
    """Dispose and remove the cached manager for server_key, if present."""
    mgr = _MANAGERS.get(server_key)
    if not mgr:
        return
    try:
        mgr.dispose()
    except Exception:
        logger.exception("Error disposing manager for %s", server_key)
    try:
        del _MANAGERS[server_key]
    except KeyError:
        pass


def dispose_all() -> None:
    """Dispose all cached managers."""
    keys = list(_MANAGERS.keys())
    for k in keys:
        dispose_manager(k)


@contextmanager
def session_scope(server_key: str):
    """Context manager yielding a SQLAlchemy Session bound to the server_key.

    Usage:
        with session_scope('primary') as session:
            session.add(obj)
    """
    mgr = get_manager(server_key)
    with mgr.session_scope() as session:
        yield session


def transactional(server_key: str):
    """Decorator that runs the wrapped function inside a transaction for
    the given server_key. The wrapped function will receive a `session`
    keyword argument unless the caller provides one.
    """
    mgr = get_manager(server_key)
    return mgr.transactional()
