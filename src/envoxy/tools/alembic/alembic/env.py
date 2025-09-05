"""Generic Alembic environment for the framework.

This env.py attempts to discover models automatically using an environment
variable SERVICE_MODELS. If that's not set, it will scan a known set of
locations under the repository to import modules named `models`.

It exposes `target_metadata` for autogenerate and keeps the alembic runtime
lightweight so services don't have to provide their own env.py unless they
need custom logic.
"""
from __future__ import annotations

import importlib
import os
import sys
from logging.config import fileConfig
import logging

from sqlalchemy import pool  # type: ignore
from sqlalchemy.engine import engine_from_config  # type: ignore
try:
    from envoxy.db.orm.constants import AUX_TABLE_PREFIX  # authoritative prefix
except ImportError:  # pragma: no cover - fallback if ORM constants not available
    AUX_TABLE_PREFIX = 'aux_'

from alembic import context

# this is the Alembic Config object, which provides access to the values within
# the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add repository src and repo root to path so rendering modules are importable
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
SRC_PATH = os.path.join(REPO_ROOT, 'src')
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

DEBUG = os.environ.get("ENVOXY_ALEMBIC_DEBUG") == "1"
log = logging.getLogger("envoxy.alembic.env")

def _discover_metadata():  # noqa: D401
    """Locate service metadata.

    Order:
      1. SERVICE_MODELS env var (exact import path, e.g. 'models' or 'myservice.models')
      2. Scan examples/*/models and src/*/models as fallbacks (mainly for dev/examples)
      3. Fallback to EnvoxyBase.metadata
    """
    service_models_raw = os.environ.get('SERVICE_MODELS')
    # Allow comma-separated list of modules
    service_models: list[str] = []
    if service_models_raw:
        service_models = [m.strip() for m in service_models_raw.split(',') if m.strip()]
    candidates: list[str] = []
    if service_models:
        candidates.extend(service_models)
    else:
        for p in ('examples', 'src'):
            base = os.path.join(REPO_ROOT, p)
            if os.path.isdir(base):
                for entry in os.listdir(base):
                    candidates.append(f"{p}.{entry}.models")

    # Augment sys.path with current working directory (external service project) and optional SERVICE_MODELS_PATHS
    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)
    extra_paths_env = os.environ.get('SERVICE_MODELS_PATHS')
    if extra_paths_env:
        for extra in extra_paths_env.split(':'):
            extra = extra.strip()
            if extra and os.path.isdir(extra) and extra not in sys.path:
                sys.path.insert(0, extra)
                if DEBUG:
                    log.warning("[alembic] added extra models path: %s", extra)

    for candidate in candidates:
        try:
            module = importlib.import_module(candidate)
            md = getattr(module, 'metadata', None)
            if md is not None:
                if DEBUG:
                    log.warning("[alembic] using metadata from %s with %d tables", candidate, len(md.tables))
                return md
        except Exception as exc:  # pragma: no cover - best effort
            if DEBUG:
                log.warning("[alembic] failed importing %s: %s", candidate, exc)
            continue
    try:
        from envoxy.db.orm import EnvoxyBase  # type: ignore
        if DEBUG:
            try:
                log.warning("[alembic] falling back to EnvoxyBase.metadata (%d tables)", len(EnvoxyBase.metadata.tables))  # type: ignore[attr-defined]
            except Exception:
                log.warning("[alembic] falling back to EnvoxyBase.metadata (table count unavailable)")
        return EnvoxyBase.metadata  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover
        if DEBUG:
            log.warning("[alembic] could not import EnvoxyBase: %s", exc)
        return None


target_metadata = _discover_metadata()

# Robust fallback: if SERVICE_MODELS is set but no metadata resolved (or empty),
# try importing EnvoxyBase directly to populate metadata before autogenerate.
if (not target_metadata) or (len(getattr(target_metadata, 'tables', {})) == 0):  # pragma: no cover - defensive
    try:
        from envoxy.db.orm import EnvoxyBase  # type: ignore
        if len(EnvoxyBase.metadata.tables):  # type: ignore[attr-defined]
            target_metadata = EnvoxyBase.metadata  # type: ignore[attr-defined]
            if DEBUG:
                log.warning("[alembic] late fallback populated metadata (%d tables)", len(target_metadata.tables))
    except Exception as exc:  # pragma: no cover
        if DEBUG:
            log.warning("[alembic] late fallback failed: %s", exc)

# If autogenerate requested but still no tables, surface a clear error early.
cmd_opts = getattr(config, 'cmd_opts', None)
if getattr(cmd_opts, 'autogenerate', False) and (not target_metadata or len(getattr(target_metadata, 'tables', {})) == 0):
    raise RuntimeError(
        "Autogenerate requested but no models discovered. Set SERVICE_MODELS=<module[,module2]> and ensure each defines/exports 'metadata' or its models are imported. "
        "You can also set SERVICE_MODELS_PATHS=/abs/path1:/abs/path2 to help discovery. CWD added to sys.path was: " + os.getcwd()
    )

# Optional deep debug: list managed tables & columns (helps diagnose missing columns)
if DEBUG and target_metadata:  # pragma: no cover
    managed_prefix_dbg = os.environ.get('ENVOXY_MANAGED_PREFIX', AUX_TABLE_PREFIX)
    for _tname, _table in target_metadata.tables.items():  # type: ignore[attr-defined]
        if _tname.startswith(managed_prefix_dbg):
            try:
                cols = [c.name + ':' + c.type.__class__.__name__ for c in _table.columns]
                log.warning('[alembic] metadata table %s columns=%s', _tname, cols)
            except Exception as _exc:  # pragma: no cover
                log.warning('[alembic] failed listing columns for %s: %s', _tname, _exc)

# ---------------------------------------------------------------------------
# Dynamic database URL resolution
# Priority:
#   1. Explicit SERVICE_DB_URL env var
#   2. ENVOXY_SERVICE_CONF file (attempt to parse)
#   3. Existing alembic.ini sqlalchemy.url
# ---------------------------------------------------------------------------

def _maybe_set_sqlalchemy_url():  # noqa: D401
    existing = config.get_main_option('sqlalchemy.url')
    env_url = os.environ.get('SERVICE_DB_URL')
    if env_url:
        if DEBUG:
            log.warning('[alembic] using SERVICE_DB_URL (masked)')
        config.set_main_option('sqlalchemy.url', env_url)
        return
    # RC file with exported variables (e.g. /etc/zapata/rc.d/muzzley.rc)
    rc_path = os.environ.get('ENVOXY_RC_PATH', '/etc/zapata/rc.d/muzzley.rc')
    if os.path.isfile(rc_path):
        try:
            with open(rc_path, 'r', encoding='utf-8') as fh:
                lines = fh.readlines()
            rc_vars = {}
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith('export '):
                    line = line[len('export '):]
                if '=' in line:
                    k, v = line.split('=', 1)
                    rc_vars[k.strip()] = v.strip()
            host = rc_vars.get('MUZZLEY_PGSQL_ADDR')
            port = rc_vars.get('MUZZLEY_PGSQL_PORT', '5432')
            user = rc_vars.get('MUZZLEY_PGSQL_USER')
            pwd = rc_vars.get('MUZZLEY_PGSQL_PASSWD', '')
            dbname = rc_vars.get('MUZZLEY_PGSQL_DB') or user  # assume db = user if absent
            if host and user and dbname and (not existing or existing.startswith('sqlite:')):
                auth = f"{user}:{pwd}@" if pwd else f"{user}@"
                # Use generic 'postgresql://' so SQLAlchemy selects an installed driver (psycopg/psycopg2)
                url = f"postgresql://{auth}{host}:{port}/{dbname}"
                config.set_main_option('sqlalchemy.url', url)
                if DEBUG:
                    log.warning('[alembic] derived DB URL from RC file %s (masked)', rc_path)
        except Exception as exc:  # pragma: no cover
            if DEBUG:
                log.warning('[alembic] failed parsing RC file %s: %s', rc_path, exc)
    return

_maybe_set_sqlalchemy_url()


# Make sqlite relative paths in the alembic config absolute relative to the
# config file location. This avoids "unable to open database file" when
# alembic is executed from a different working directory.
cfg_file = config.config_file_name
if cfg_file:
    try:
        cfg_dir = os.path.dirname(os.path.abspath(cfg_file))
        url = config.get_main_option('sqlalchemy.url')
        if url and url.startswith('sqlite:///'):
            # strip the scheme (sqlite:///)
            db_path = url[len('sqlite:///'):]
            if not os.path.isabs(db_path):
                abs_db = os.path.normpath(os.path.join(cfg_dir, db_path))
                parent = os.path.dirname(abs_db)
                if parent and not os.path.isdir(parent):
                    os.makedirs(parent, exist_ok=True)
                new_url = f"sqlite:///{abs_db}"
                config.set_main_option('sqlalchemy.url', new_url)
    except Exception:
        # best-effort: let Alembic surface errors if something goes wrong here
        pass


def run_migrations_offline():
    url = config.get_main_option('sqlalchemy.url')
    managed_prefix = os.environ.get('ENVOXY_MANAGED_PREFIX', AUX_TABLE_PREFIX)

    def include_object(object_, name, type_, reflected, compare_to):  # noqa: D401
        # Only manage tables (and their indexes) matching the managed prefix.
        if type_ == 'table':
            return name.startswith(managed_prefix)
        if type_ == 'index':
            try:
                tbl_name = object_.table.name  # type: ignore[attr-defined]
            except Exception:  # pragma: no cover
                tbl_name = None
            return bool(tbl_name and tbl_name.startswith(managed_prefix))
        return True  # other object types (constraints) decided by parent table

    # Early reflection pruning: avoid inspecting unrelated tables (suppresses
    # warnings about unsupported reflection on expression indexes/types for
    # non-managed tables).
    def include_name(name, type_, parent_names):  # pragma: no cover - simple predicate
        if type_ == 'table':
            return name.startswith(managed_prefix)
        return True

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        include_name=include_name,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )

    managed_prefix = os.environ.get('ENVOXY_MANAGED_PREFIX', AUX_TABLE_PREFIX)

    def include_object(object_, name, type_, reflected, compare_to):  # noqa: D401
        if type_ == 'table':
            return name.startswith(managed_prefix)
        if type_ == 'index':
            try:
                tbl_name = object_.table.name  # type: ignore[attr-defined]
            except Exception:  # pragma: no cover
                tbl_name = None
            return bool(tbl_name and tbl_name.startswith(managed_prefix))
        return True

    def include_name(name, type_, parent_names):  # pragma: no cover - simple predicate
        if type_ == 'table':
            return name.startswith(managed_prefix)
        return True

    with connectable.connect() as connection:  # type: ignore[attr-defined]
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_name=include_name,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
