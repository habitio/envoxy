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
import shlex
import subprocess
from urllib.parse import quote_plus

from sqlalchemy import pool  # type: ignore
from sqlalchemy import inspect  # type: ignore
from sqlalchemy.engine import engine_from_config  # type: ignore

try:
    from envoxy.db.orm.constants import AUX_TABLE_PREFIX  # authoritative prefix
except ImportError:  # pragma: no cover - fallback if ORM constants not available
    AUX_TABLE_PREFIX = "aux_"

from alembic import context

# this is the Alembic Config object, which provides access to the values within
# the .ini file in use.
config = context.config  # type: ignore[attr-defined]

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add repository src and repo root to path so rendering modules are importable
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
SRC_PATH = os.path.join(REPO_ROOT, "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

DEBUG = os.environ.get("ENVOXY_ALEMBIC_DEBUG") == "1"
log = logging.getLogger("envoxy.alembic.env")


# ---------------------------------------------------------------------------
# Service namespace -> managed prefix helper
# Use AUX_TABLE_PREFIX from the ORM (single source of truth). It already
# reflects ENVOXY_SERVICE_NAMESPACE at import time, yielding aux_<ns>_.
# Fall back to composing aux_<ns>_ only if the env var wasn’t reflected.
# ---------------------------------------------------------------------------
def _get_service_namespace() -> str | None:
    ns = os.environ.get("ENVOXY_SERVICE_NAMESPACE") or os.environ.get(
        "SERVICE_NAMESPACE"
    )
    if not ns:
        return None
    # sanitize: lowercase, alnum + underscore only
    safe = "".join(
        ch if (ch.isalnum() or ch == "_") else "_" for ch in ns.strip().lower()
    ).strip("_")
    return safe or None


def _compute_managed_prefix() -> str:
    ns = _get_service_namespace()
    if not ns:
        raise RuntimeError(
            "ENVOXY_SERVICE_NAMESPACE is required to run Alembic for this service"
        )
    if os.environ.get("ENVOXY_MANAGED_PREFIX") and DEBUG:
        log.warning(
            "[alembic] ENVOXY_MANAGED_PREFIX is ignored; deriving from ENVOXY_SERVICE_NAMESPACE"
        )
    # Prefer the framework constant, already namespaced when the env var is set
    prefix = AUX_TABLE_PREFIX
    if prefix == "aux_":
        # Defensive fallback: env var not reflected in constants for any reason
        prefix = f"aux_{ns}_"
    return prefix


# ---------------------------------------------------------------------------
# Per-service version table support
# We derive a stable identifier primarily from ENVOXY_SERVICE_NAMESPACE.
# If not set, we fall back to SERVICE_MODELS (first module name) or the managed prefix.
# Final format: alembic_version_<service_id>
# ---------------------------------------------------------------------------
def _derive_service_version_table() -> str:
    # Namespace is mandatory; derive version table strictly from it
    if os.environ.get("ENVOXY_VERSION_TABLE") and DEBUG:
        log.warning(
            "[alembic] ENVOXY_VERSION_TABLE is deprecated/ignored; using namespace-derived name instead"
        )
    ns = _get_service_namespace()
    if not ns:
        raise RuntimeError(
            "ENVOXY_SERVICE_NAMESPACE is required to determine the alembic version table name"
        )
    safe_ns = "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in str(ns))[:40]
    return f"alembic_version_{safe_ns}"


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
    service_models_raw = os.environ.get("SERVICE_MODELS")
    # Allow comma-separated list of modules
    service_models: list[str] = []
    if service_models_raw:
        service_models = [m.strip() for m in service_models_raw.split(",") if m.strip()]
    candidates: list[str] = []
    if service_models:
        candidates.extend(service_models)
    else:
        for p in ("examples", "src"):
            base = os.path.join(REPO_ROOT, p)
            if os.path.isdir(base):
                for entry in os.listdir(base):
                    candidates.append(f"{p}.{entry}.models")

    # Augment sys.path with current working directory (external service project) and optional SERVICE_MODELS_PATHS
    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)
    extra_paths_env = os.environ.get("SERVICE_MODELS_PATHS")
    if extra_paths_env:
        for extra in extra_paths_env.split(":"):
            extra = extra.strip()
            if extra and os.path.isdir(extra) and extra not in sys.path:
                sys.path.insert(0, extra)
                if DEBUG:
                    log.warning("[alembic] added extra models path: %s", extra)

    for candidate in candidates:
        try:
            module = importlib.import_module(candidate)
            md = getattr(module, "metadata", None)
            if md is not None:
                if DEBUG:
                    log.warning(
                        "[alembic] using metadata from %s with %d tables",
                        candidate,
                        len(md.tables),
                    )
                return md
        except Exception as exc:  # pragma: no cover - best effort
            if DEBUG:
                log.warning("[alembic] failed importing %s: %s", candidate, exc)
            continue
    try:
        from envoxy.db.orm import EnvoxyBase  # type: ignore

        if DEBUG:
            try:
                log.warning(
                    "[alembic] falling back to EnvoxyBase.metadata (%d tables)",
                    len(EnvoxyBase.metadata.tables),
                )  # type: ignore[attr-defined]
            except Exception:
                log.warning(
                    "[alembic] falling back to EnvoxyBase.metadata (table count unavailable)"
                )
        return EnvoxyBase.metadata  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover
        if DEBUG:
            log.warning("[alembic] could not import EnvoxyBase: %s", exc)
        return None


target_metadata = _discover_metadata()

# Robust fallback: if SERVICE_MODELS is set but no metadata resolved (or empty),
# try importing EnvoxyBase directly to populate metadata before autogenerate.
if (not target_metadata) or (
    len(getattr(target_metadata, "tables", {})) == 0
):  # pragma: no cover - defensive
    try:
        from envoxy.db.orm import EnvoxyBase  # type: ignore

        if len(EnvoxyBase.metadata.tables):  # type: ignore[attr-defined]
            target_metadata = EnvoxyBase.metadata  # type: ignore[attr-defined]
            if DEBUG:
                log.warning(
                    "[alembic] late fallback populated metadata (%d tables)",
                    len(target_metadata.tables),
                )
    except Exception as exc:  # pragma: no cover
        if DEBUG:
            log.warning("[alembic] late fallback failed: %s", exc)

# If autogenerate requested but still no tables, surface a clear error early.
cmd_opts = getattr(config, "cmd_opts", None)
if getattr(cmd_opts, "autogenerate", False) and (
    not target_metadata or len(getattr(target_metadata, "tables", {})) == 0
):
    raise RuntimeError(
        "Autogenerate requested but no models discovered. Set SERVICE_MODELS=<module[,module2]> and ensure each defines/exports 'metadata' or its models are imported. "
        "You can also set SERVICE_MODELS_PATHS=/abs/path1:/abs/path2 to help discovery. CWD added to sys.path was: "
        + os.getcwd()
    )

# Optional deep debug: list managed tables & columns (helps diagnose missing columns)
if DEBUG and target_metadata:  # pragma: no cover
    managed_prefix_dbg = _compute_managed_prefix()
    for _tname, _table in target_metadata.tables.items():  # type: ignore[attr-defined]
        if _tname.startswith(managed_prefix_dbg):
            try:
                cols = [
                    c.name + ":" + c.type.__class__.__name__ for c in _table.columns
                ]
                log.warning("[alembic] metadata table %s columns=%s", _tname, cols)
            except Exception as _exc:  # pragma: no cover
                log.warning("[alembic] failed listing columns for %s: %s", _tname, _exc)

# ---------------------------------------------------------------------------
# Dynamic database URL resolution (PostgreSQL REQUIRED)
# Priority:
#   1. SERVICE_DB_URL env var (must be postgresql://)
#   2. RC file (ENVOXY_RC_PATH or default /etc/zapata/rc.d/muzzley.rc)
# If neither yields a Postgres URL, abort. No sqlite fallback is allowed.
# ---------------------------------------------------------------------------


def _load_rc_vars(rc_path: str) -> dict[str, str] | None:
    """Source a shell RC file with bash and extract MUZZLEY_PGSQL_* vars safely.

    This approach lets bash handle quotes, exports, and variable expansions, avoiding
    brittle manual parsing. Returns a dict or None on failure.
    """
    script = (
        "set -a; "
        f"source {shlex.quote(rc_path)} >/dev/null 2>&1; "
        "printf 'MUZZLEY_PGSQL_ADDR=%s\n' \"${MUZZLEY_PGSQL_ADDR-}\"; "
        "printf 'MUZZLEY_PGSQL_PORT=%s\n' \"${MUZZLEY_PGSQL_PORT-}\"; "
        "printf 'MUZZLEY_PGSQL_USER=%s\n' \"${MUZZLEY_PGSQL_USER-}\"; "
        "printf 'MUZZLEY_PGSQL_PASSWD=%s\n' \"${MUZZLEY_PGSQL_PASSWD-}\"; "
        "printf 'MUZZLEY_PGSQL_DB=%s\n' \"${MUZZLEY_PGSQL_DB-}\"; "
    )
    try:
        out = subprocess.check_output(
            ["bash", "-c", script], text=True, stderr=subprocess.DEVNULL
        )
        result: dict[str, str] = {}
        for line in out.splitlines():
            if not line or "=" not in line:
                continue
            k, v = line.split("=", 1)
            result[k.strip()] = v
        return result
    except Exception as exc:  # pragma: no cover
        if DEBUG:
            log.warning("[alembic] failed sourcing RC file with bash: %s", exc)
        return None


def _maybe_set_sqlalchemy_url():  # noqa: D401
    env_url = os.environ.get("SERVICE_DB_URL")
    if env_url:
        if not env_url.startswith("postgresql://"):
            raise RuntimeError(
                "SERVICE_DB_URL must start with postgresql:// (got masked value)"
            )
        if DEBUG:
            log.warning("[alembic] using SERVICE_DB_URL (masked)")
        config.set_main_option("sqlalchemy.url", env_url)
        return

    # RC file with exported variables (e.g. /etc/zapata/rc.d/muzzley.rc)
    rc_path = os.environ.get("ENVOXY_RC_PATH", "/etc/zapata/rc.d/muzzley.rc")
    if os.path.isfile(rc_path):
        rc_vars = _load_rc_vars(rc_path)
        if rc_vars is not None:
            host = rc_vars.get("MUZZLEY_PGSQL_ADDR")
            port = rc_vars.get("MUZZLEY_PGSQL_PORT", "5432") or "5432"
            user = rc_vars.get("MUZZLEY_PGSQL_USER")
            pwd = rc_vars.get("MUZZLEY_PGSQL_PASSWD", "")
            dbname = (
                rc_vars.get("MUZZLEY_PGSQL_DB") or user
            )  # assume db = user if absent
            if host and user and dbname:
                user_enc = quote_plus(user)
                pwd_enc = quote_plus(pwd) if pwd else ""
                auth = f"{user_enc}:{pwd_enc}@" if pwd else f"{user_enc}@"
                url = f"postgresql://{auth}{host}:{port}/{dbname}"
                config.set_main_option("sqlalchemy.url", url)
                if DEBUG:
                    log.warning(
                        "[alembic] derived DB URL from RC file %s via bash (masked)",
                        rc_path,
                    )
                return
            if DEBUG:
                log.warning(
                    "[alembic] RC file %s missing required PG vars (host/user/db)",
                    rc_path,
                )

    raise RuntimeError(
        "PostgreSQL URL required: set SERVICE_DB_URL=postgresql://... or provide RC file with MUZZLEY_PGSQL_* variables"
    )


_maybe_set_sqlalchemy_url()

# Enforce final URL correctness (defensive)
final_url = config.get_main_option("sqlalchemy.url")
if not final_url or not final_url.startswith("postgresql://"):
    raise RuntimeError(
        "PostgreSQL sqlalchemy.url is mandatory (expected postgresql://...)"
    )


# Make sqlite relative paths in the alembic config absolute relative to the
# config file location. This avoids "unable to open database file" when
# alembic is executed from a different working directory.
# (Removed sqlite path normalization logic – Postgres required)


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    managed_prefix = _compute_managed_prefix()

    def include_object(object_, name, type_, _reflected, _compare_to):  # noqa: D401
        if type_ == "table":
            return name.startswith(managed_prefix)
        if type_ == "index":
            try:
                tbl_name = object_.table.name  # type: ignore[attr-defined]
            except Exception:  # pragma: no cover
                tbl_name = None
            return bool(tbl_name and tbl_name.startswith(managed_prefix))
        return True  # other object types (constraints) decided by parent table

    def include_name(name, type_, _parent_names):  # pragma: no cover - simple predicate
        if type_ == "table":
            return name.startswith(managed_prefix)
        return True

    context.configure(  # type: ignore[attr-defined]
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        include_name=include_name,
        include_object=include_object,
        version_table=VERSION_TABLE_NAME,
    )

    with context.begin_transaction():  # type: ignore[attr-defined]
        context.run_migrations()  # type: ignore[attr-defined]


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    managed_prefix = _compute_managed_prefix()

    def include_object(object_, name, type_, _reflected, _compare_to):  # noqa: D401
        if type_ == "table":
            return name.startswith(managed_prefix)
        if type_ == "index":
            try:
                tbl_name = object_.table.name  # type: ignore[attr-defined]
            except Exception:  # pragma: no cover
                tbl_name = None
            return bool(tbl_name and tbl_name.startswith(managed_prefix))
        return True

    def include_name(name, type_, _parent_names):  # pragma: no cover - simple predicate
        if type_ == "table":
            return name.startswith(managed_prefix)
        return True

    with connectable.connect() as connection:  # type: ignore[attr-defined]
        # Optional deep visibility: enumerate all prefixed tables in the live DB
        if DEBUG:
            try:  # pragma: no cover - debug/inspection path
                insp = inspect(connection)
                get_tables = getattr(insp, "get_table_names")  # type: ignore[attr-defined]
                prefixed_tables = [
                    t for t in get_tables() if t.startswith(managed_prefix)
                ]  # type: ignore[arg-type]
                for t in sorted(prefixed_tables):
                    log.warning(
                        "[alembic] table %s: MANAGED (matches prefix %s)",
                        t,
                        managed_prefix,
                    )
                log.warning(
                    "[alembic] table analysis summary: %d %s* tables managed",
                    len(prefixed_tables),
                    managed_prefix,
                )
            except Exception as exc:  # pragma: no cover
                log.warning("[alembic] table scan failed: %s", exc)
        context.configure(  # type: ignore[attr-defined]
            connection=connection,
            target_metadata=target_metadata,
            include_name=include_name,
            include_object=include_object,
            version_table=VERSION_TABLE_NAME,
        )

        with context.begin_transaction():  # type: ignore[attr-defined]
            context.run_migrations()  # type: ignore[attr-defined]


if context.is_offline_mode():  # type: ignore[attr-defined]
    run_migrations_offline()
else:
    run_migrations_online()
