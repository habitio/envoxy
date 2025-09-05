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
from sqlalchemy import inspect  # type: ignore
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

# ---------------------------------------------------------------------------
# Per-service version table support
# You can set ENVOXY_VERSION_TABLE explicitly. Otherwise we derive a stable
# identifier from SERVICE_MODELS (first module name) or the managed prefix.
# Generates table name: alembic_version_<service_id>
# ---------------------------------------------------------------------------
def _derive_service_version_table() -> str:
    explicit = os.environ.get('ENVOXY_VERSION_TABLE')
    if explicit:
        return explicit
    raw_models = os.environ.get('SERVICE_MODELS', '')
    candidate = None
    if raw_models:
        first_mod = raw_models.split(',')[0].strip()
        if first_mod:
            candidate = first_mod.split('.')[0]
    if not candidate:
        candidate = os.environ.get('ENVOXY_MANAGED_PREFIX', AUX_TABLE_PREFIX).strip('_') or 'service'
    # Sanitize: only alnum + underscore
    safe = ''.join(ch if (ch.isalnum() or ch == '_') else '_' for ch in candidate.lower())[:40]
    return f"alembic_version_{safe}"

VERSION_TABLE_NAME = _derive_service_version_table()
if DEBUG:
    log.warning("[alembic] using version table: %s", VERSION_TABLE_NAME)

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
# Dynamic database URL resolution (PostgreSQL REQUIRED)
# Priority:
#   1. SERVICE_DB_URL env var (must be postgresql://)
#   2. RC file (ENVOXY_RC_PATH or default /etc/zapata/rc.d/muzzley.rc)
# If neither yields a Postgres URL, abort. No sqlite fallback is allowed.
# ---------------------------------------------------------------------------

def _maybe_set_sqlalchemy_url():  # noqa: D401
    env_url = os.environ.get('SERVICE_DB_URL')
    if env_url:
        if not env_url.startswith('postgresql://'):
            raise RuntimeError("SERVICE_DB_URL must start with postgresql:// (got masked value)")
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
            if host and user and dbname:
                auth = f"{user}:{pwd}@" if pwd else f"{user}@"
                url = f"postgresql://{auth}{host}:{port}/{dbname}"
                config.set_main_option('sqlalchemy.url', url)
                if DEBUG:
                    log.warning('[alembic] derived DB URL from RC file %s (masked)', rc_path)
                return
            else:
                if DEBUG:
                    log.warning('[alembic] RC file %s missing required PG vars (host/user/db)', rc_path)
        except Exception as exc:  # pragma: no cover
            if DEBUG:
                log.warning('[alembic] failed parsing RC file %s: %s', rc_path, exc)

    raise RuntimeError('PostgreSQL URL required: set SERVICE_DB_URL=postgresql://... or provide RC file with MUZZLEY_PGSQL_* variables')

_maybe_set_sqlalchemy_url()

# Enforce final URL correctness (defensive)
final_url = config.get_main_option('sqlalchemy.url')
if not final_url or not final_url.startswith('postgresql://'):
    raise RuntimeError('PostgreSQL sqlalchemy.url is mandatory (expected postgresql://...)')


# Make sqlite relative paths in the alembic config absolute relative to the
# config file location. This avoids "unable to open database file" when
# alembic is executed from a different working directory.
# (Removed sqlite path normalization logic – Postgres required)


def run_migrations_offline():
    url = config.get_main_option('sqlalchemy.url')
    managed_prefix = os.environ.get('ENVOXY_MANAGED_PREFIX', AUX_TABLE_PREFIX)
    manage_all_prefixed = os.environ.get('ENVOXY_MANAGE_ALL_PREFIXED') == '1'
    allow_drops = os.environ.get('ENVOXY_ALLOW_DROPS') == '1'
    metadata_names = set(getattr(target_metadata, 'tables', {}).keys()) if target_metadata else set()
    drop_list_env = os.environ.get('ENVOXY_DROP_TABLES', '')
    drop_tables = {t.strip() for t in drop_list_env.split(',') if t.strip()}

    def include_object(object_, name, type_, reflected, compare_to):  # noqa: D401
        # Manage only tables declared in this service's metadata to avoid cross-service drops.
        if type_ == 'table':
            if not name.startswith(managed_prefix):
                return False
            if manage_all_prefixed:
                return True
            # If table not in metadata we normally skip (prevents accidental drop)
            if name in metadata_names:
                return True
            # Explicit per-table drop list has priority over global flags.
            if name in drop_tables:
                return True
            # Allow broader drops only when allow_drops toggled.
            return allow_drops
        if type_ == 'index':
            try:
                tbl_name = object_.table.name  # type: ignore[attr-defined]
            except Exception:  # pragma: no cover
                tbl_name = None
            if not tbl_name or not tbl_name.startswith(managed_prefix):
                return False
            if manage_all_prefixed:
                return True
            if tbl_name in metadata_names:
                return True
            if tbl_name in drop_tables:
                return True
            return allow_drops
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
        version_table=VERSION_TABLE_NAME,
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
    manage_all_prefixed = os.environ.get('ENVOXY_MANAGE_ALL_PREFIXED') == '1'
    allow_drops = os.environ.get('ENVOXY_ALLOW_DROPS') == '1'
    metadata_names = set(getattr(target_metadata, 'tables', {}).keys()) if target_metadata else set()
    drop_list_env = os.environ.get('ENVOXY_DROP_TABLES', '')
    drop_tables = {t.strip() for t in drop_list_env.split(',') if t.strip()}

    def include_object(object_, name, type_, reflected, compare_to):  # noqa: D401
        if type_ == 'table':
            if not name.startswith(managed_prefix):
                return False
            if manage_all_prefixed:
                return True
            if name in metadata_names:
                return True
            if name in drop_tables:
                return True
            return allow_drops
        if type_ == 'index':
            try:
                tbl_name = object_.table.name  # type: ignore[attr-defined]
            except Exception:  # pragma: no cover
                tbl_name = None
            if not tbl_name or not tbl_name.startswith(managed_prefix):
                return False
            if manage_all_prefixed:
                return True
            if tbl_name in metadata_names:
                return True
            if tbl_name in drop_tables:
                return True
            return allow_drops
        return True

    def include_name(name, type_, parent_names):  # pragma: no cover - simple predicate
        if type_ == 'table':
            return name.startswith(managed_prefix)
        return True

    with connectable.connect() as connection:  # type: ignore[attr-defined]
        # Optional deep visibility: enumerate all prefixed tables in the live DB and
        # classify which ones this service will manage vs ignore. Enabled when
        # ENVOXY_ALEMBIC_DEBUG=1. This gives operators confidence that cross-service
        # tables (same prefix but not in metadata) are being deliberately skipped.
        if DEBUG:
            try:  # pragma: no cover - debug/inspection path
                insp = inspect(connection)
                get_tables = getattr(insp, 'get_table_names')  # type: ignore[attr-defined]
                prefixed_tables = [t for t in get_tables() if t.startswith(managed_prefix)]  # type: ignore[arg-type]
                managed: list[str] = []
                ignored: list[str] = []
                log.warning(
                    '[alembic] analyzing %s* tables (manage_all=%s allow_drops=%s drop_list=%s metadata_tables=%d)',
                    managed_prefix,
                    manage_all_prefixed,
                    allow_drops,
                    ','.join(sorted(drop_tables)) or '-',
                    len(metadata_names),
                )
                for t in sorted(prefixed_tables):
                    if manage_all_prefixed:
                        managed.append(t)
                        log.warning('[alembic] table %s: MANAGED (manage_all_prefixed)', t)
                    elif t in metadata_names:
                        managed.append(t)
                        log.warning('[alembic] table %s: MANAGED (in service metadata)', t)
                    elif t in drop_tables:
                        managed.append(t)
                        log.warning('[alembic] table %s: MANAGED (explicit ENVOXY_DROP_TABLES)', t)
                    elif allow_drops:
                        managed.append(t)
                        log.warning('[alembic] table %s: MANAGED (ENVOXY_ALLOW_DROPS=1)', t)
                    else:
                        ignored.append(t)
                        log.warning('[alembic] table %s: IGNORED (other service / not in metadata)', t)
                log.warning(
                    '[alembic] table analysis summary: %d %s* tables: %d managed, %d ignored',
                    len(prefixed_tables),
                    managed_prefix,
                    len(managed),
                    len(ignored),
                )
                if ignored:
                    log.warning('[alembic] IGNORED tables (will NOT be altered/dropped): %s', ', '.join(ignored))
            except Exception as exc:  # pragma: no cover
                log.warning('[alembic] table scan failed: %s', exc)
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_name=include_name,
            include_object=include_object,
            version_table=VERSION_TABLE_NAME,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
