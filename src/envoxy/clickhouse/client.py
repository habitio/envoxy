# ruff: noqa: F401
"""
ClickHouse read-only client for Envoxy.

Design goals and ClickHouse-specific best practices applied here:

1. Read-only by contract — no insert/update/delete methods exist.
   At the protocol level `readonly=2` is passed as a session setting so that
   the server itself will reject any data-modification attempt even if a caller
   constructs a raw INSERT/ALTER query string.

2. One HTTP client per thread per server key — `clickhouse_connect` does NOT
   support concurrent queries on the same client/session.  We use
   ``threading.local()`` so each worker thread transparently gets its own
   client instance.  The main thread's client is created eagerly (startup
   health-check); worker-thread clients are created lazily on first use.

3. Retry with exponential back-off — only on transient/network errors
   (`OperationalError`).  Query-level errors (`DatabaseError`, bad SQL, type
   mismatches) propagate immediately so callers can react.

4. HTTP compression enabled by default — ClickHouse supports LZ4 / ZSTD
   compression at the HTTP layer.  For analytics payloads (large COUNT/GROUP BY
   result sets) this reduces transfer time significantly.

5. Per-query settings — callers can pass `query_settings` to override defaults
   on a single call (e.g. raise `max_execution_time` for a heavy report).

6. Uniform result shape — results are always `list[dict]` with Python-native
   types, matching the shape returned by the PostgreSQL client so that upper
   layers need no branching.

7. Type normalisation — ClickHouse returns `Decimal`, `uuid.UUID`, `datetime`,
   and `date` objects.  All are converted to the platform's standard wire
   format (strings / floats) so JSON serialisers and downstream code work
   without extra handling.

8. Health check via `client.ping()` — used on startup and optionally on retry.

Configuration block expected under `clickhouse_servers` in the app config:

    "clickhouse_servers": {
        "<server_key>": {
            "host":               "ch.example.com",
            "port":               8123,       # 8443 for HTTPS
            "db":                 "raw",       # default database
            "username":           "default",
            "passwd":             "",
            "secure":             false,       # true → HTTPS
            "compress":           true,        # HTTP-level compression
            "query_timeout":      30,          # HTTP socket timeout (seconds)
            "max_execution_time": 30,          # ClickHouse server-side timeout
            "max_threads":        4            # server-side query parallelism
        }
    }
"""

import math
import uuid
import decimal
import threading
from time import sleep
from threading import RLock
from datetime import datetime, date, timezone

try:
    import clickhouse_connect
    from clickhouse_connect.driver.exceptions import OperationalError, DatabaseError
except ImportError as _exc:  # pragma: no cover
    raise ImportError(
        "clickhouse-connect is required for the ClickHouse client. "
        "Install it with: pip install clickhouse-connect"
    ) from _exc

from ..db.exceptions import DatabaseException
from ..utils.logs import Log
from ..constants import TIMEOUT_CONN

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

# Session-level settings applied to every query unless overridden.
#   readonly=2  → server rejects INSERT/ALTER/DROP but allows SET (query opts)
_DEFAULT_SESSION_SETTINGS: dict = {
    "readonly": 2,
}

# Per-query defaults that callers can override via `query_settings=`.
_DEFAULT_QUERY_SETTINGS: dict = {
    "max_execution_time": 30,  # seconds before server cancels the query
}

# Retry knobs for transient connectivity failures.
_DEFAULT_RETRIES = 3
_DEFAULT_RETRY_DELAY = 1  # seconds (doubles on each attempt)


# ---------------------------------------------------------------------------
# Result normalisation
# ---------------------------------------------------------------------------


def _normalize_value(value: object) -> object:
    """Convert a single ClickHouse-typed value to a platform-standard type.

    ClickHouse-specific conversions:
    - ``datetime`` (DateTime / DateTime64)   → "YYYY-MM-DDTHH:MM:SS.fff+0000"
    - ``date``     (Date / Date32)           → "YYYY-MM-DD"
    - ``Decimal``  (Decimal32/64/128/256)    → float
    - ``uuid.UUID``                          → str (lowercase with dashes)
    - Everything else (int, float, str, bool, None) passes through unchanged.
    """
    if isinstance(value, datetime):
        dt_utc = value if value.tzinfo is None else value.astimezone(timezone.utc)
        return dt_utc.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+0000"
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


def _normalize_row(columns: tuple, row: tuple) -> dict:
    """Zip column names and values into a normalised dict."""
    return {col: _normalize_value(val) for col, val in zip(columns, row)}


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class Client:
    """
    Singleton ClickHouse client for Envoxy — read-only queries only.

    One ``clickhouse_connect.Client`` instance is kept alive **per thread**
    per server key (via ``threading.local()``).  This sidesteps the
    ``ProgrammingError: Attempt to execute concurrent queries within the same
    session`` that occurs when a single client is shared across threads.

    The underlying HTTP client manages its own urllib3 connection pool; this
    wrapper adds per-thread isolation, retry logic, type normalisation, and
    unified logging on top.
    """

    _instance = None
    _lock = (
        RLock()
    )  # Reentrant: reload_config holds the lock and calls _connect which re-acquires it

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, server_conf: dict):
        # Guard against re-initialisation in the singleton pattern.
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self._instances: dict = {}

        for server_key, conf in server_conf.items():
            session_settings = self._build_session_settings(conf)
            with self._lock:
                self._instances[server_key] = {
                    "server": server_key,
                    "conf": conf,
                    "session_settings": session_settings,
                    # Per-thread ch_client storage — each thread gets its own
                    # clickhouse_connect client to avoid concurrent-session errors.
                    "local": threading.local(),
                }
            # Eager connect on the main thread acts as a startup health-check.
            # Worker threads will lazy-create their own clients on first use.
            self._connect(self._instances[server_key])

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_session_settings(conf: dict) -> dict:
        """Compute the session-level ClickHouse settings from a server config."""
        session_settings = dict(_DEFAULT_SESSION_SETTINGS)
        if "max_threads" in conf:
            session_settings["max_threads"] = int(conf["max_threads"])
        return session_settings

    def _connect(
        self,
        instance: dict,
        reconnect_attempts: int = _DEFAULT_RETRIES,
        reconnect_delay: float = _DEFAULT_RETRY_DELAY,
    ) -> None:
        """Create a ``clickhouse_connect.Client`` for the CURRENT THREAD and store it
        in the instance's ``threading.local()`` slot.

        Each calling thread gets its own isolated client, preventing concurrent-
        session errors when multiple threads run queries simultaneously.
        """

        conf = instance["conf"]
        session_settings = instance.get(
            "session_settings"
        ) or self._build_session_settings(conf)

        ch_client = self._retry_connect(
            conf=conf,
            session_settings=session_settings,
            attempts=reconnect_attempts,
            delay=reconnect_delay,
        )

        # Store in the thread-local slot — invisible to other threads.
        instance["local"].ch_client = ch_client

        Log.trace(
            ">>> Connected to CLICKHOUSE: {}, {}:{}".format(
                instance["server"],
                conf.get("host", "localhost"),
                conf.get("port", 8123),
            )
        )

    def _retry_connect(
        self,
        conf: dict,
        session_settings: dict,
        attempts: int,
        delay: float,
    ):
        """Attempt to create a ClickHouse HTTP client, retrying on failure."""

        last_exc: Exception | None = None

        for attempt in range(attempts):
            try:
                ch_client = clickhouse_connect.get_client(
                    host=conf.get("host", "localhost"),
                    port=int(conf.get("port", 8123)),
                    username=conf.get("username", "default"),
                    password=conf.get("passwd", ""),
                    database=conf.get("db", "default"),
                    secure=bool(conf.get("secure", False)),
                    compress=bool(conf.get("compress", True)),
                    # HTTP-level socket timeout; ClickHouse server-side timeout
                    # is enforced separately via max_execution_time.
                    query_limit=0,  # no client-side row cap
                    settings=session_settings,
                )
                # Verify the connection is actually reachable.
                if not ch_client.ping():
                    raise OperationalError("ClickHouse ping failed")
                return ch_client

            except Exception as exc:
                last_exc = exc
                Log.error(
                    f"[CH] Connection attempt {attempt + 1}/{attempts} failed: {exc!r}"
                )
                sleep(delay * math.pow(2, attempt))

        raise DatabaseException(
            f"[CH] Failed to connect after {attempts} attempts: {last_exc}"
        ) from last_exc

    def _get_client(self, server_key: str):
        """Return the live ``clickhouse_connect.Client`` for *server_key* in the
        current thread, creating one lazily if this thread has never queried
        this server before.
        """

        instance = self._instances.get(server_key)

        if instance is None:
            raise DatabaseException(
                f"[CH] No configuration found for server key: '{server_key}'"
            )

        local = instance["local"]
        ch_client = getattr(local, "ch_client", None)

        if ch_client is None:
            # First use in this thread — create a dedicated client.
            self._connect(instance)
            ch_client = local.ch_client

        return ch_client

    def _is_healthy(self, server_key: str) -> bool:
        """Ping the server and return True if it responds."""
        try:
            return self._get_client(server_key).ping()
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def query(
        self,
        server_key: str,
        sql_query: str,
        params: dict | None = None,
        query_settings: dict | None = None,
    ) -> list[dict]:
        """
        Execute a read-only SQL query and return results as ``list[dict]``.

        Parameters
        ----------
        server_key:
            Identifier matching a key in ``clickhouse_servers`` config.
        sql_query:
            ClickHouse SQL string.  Use ``{name:Type}`` placeholders for
            parameters (e.g. ``WHERE app_id = {application_id:String}``).
        params:
            Dict of named parameters to bind — values are Python-typed and
            the library converts them to ClickHouse wire format automatically.
        query_settings:
            Optional per-query ClickHouse settings that override the defaults
            (e.g. ``{"max_execution_time": 120}`` for a heavier report).

        Returns
        -------
        list[dict]
            Each dict maps column name → normalised Python value.  The shape
            matches what the PostgreSQL client returns so callers need no
            special-casing.

        Raises
        ------
        DatabaseException
            On connection failure after retries, or when no config exists for
            *server_key*.
        clickhouse_connect.driver.exceptions.DatabaseError
            Propagated directly for bad SQL, type errors, or permission
            violations — these are not retried.
        """

        if not sql_query or not sql_query.strip():
            raise DatabaseException("[CH] SQL query cannot be empty")

        _params = params or {}

        # Merge default query settings with caller overrides.
        _settings = dict(_DEFAULT_QUERY_SETTINGS)
        if query_settings:
            _settings.update(query_settings)

        return self._execute_with_retry(server_key, sql_query, _params, _settings)

    def _execute_with_retry(
        self,
        server_key: str,
        sql_query: str,
        params: dict,
        settings: dict,
        attempts: int = _DEFAULT_RETRIES,
        delay: float = _DEFAULT_RETRY_DELAY,
    ) -> list[dict]:
        """Run the query, reconnecting on transient errors."""

        last_exc: Exception | None = None

        for attempt in range(attempts):
            try:
                ch_client = self._get_client(server_key)
                result = ch_client.query(
                    sql_query, parameters=params, settings=settings
                )
                columns = result.column_names
                return [_normalize_row(columns, row) for row in result.result_rows]

            except DatabaseError:
                # Bad SQL / type error / access violation — don't retry, let it
                # bubble up so the caller gets a clear error message.
                raise

            except Exception as exc:
                # Transient connectivity error — attempt to reconnect for this
                # thread and retry.
                last_exc = exc
                Log.error(
                    f"[CH:{server_key}] Query attempt {attempt + 1}/{attempts} failed: "
                    f"{exc!r}. Reconnecting…"
                )
                try:
                    self._connect(self._instances[server_key])
                except Exception as reconnect_exc:
                    Log.error(f"[CH:{server_key}] Reconnect failed: {reconnect_exc!r}")
                sleep(delay * math.pow(2, attempt))

        raise DatabaseException(
            f"[CH:{server_key}] Query failed after {attempts} attempts: {last_exc}"
        ) from last_exc

    def reload_config(self, server_conf: dict) -> None:
        """
        Hot-reload server configuration without restarting the process.

        - New keys are connected immediately (current thread).
        - Existing keys whose config changed get a fresh thread-local object
          so every thread will lazy-create a new client on next use.
        - Removed keys have the current thread's client closed gracefully.
        """

        with self._lock:
            existing_keys = set(self._instances)
            new_keys = set(server_conf)

            # Close this thread's client for removed servers.
            for removed_key in existing_keys - new_keys:
                self._close_client(self._instances.pop(removed_key, {}))

            for server_key, conf in server_conf.items():
                if server_key in self._instances:
                    old_conf = self._instances[server_key]["conf"]
                    if old_conf != conf:
                        # Config changed — close this thread's client, replace
                        # the thread-local object so all threads lazy-reconnect.
                        self._close_client(self._instances[server_key])
                        self._instances[server_key]["conf"] = conf
                        self._instances[server_key]["session_settings"] = (
                            self._build_session_settings(conf)
                        )
                        self._instances[server_key]["local"] = threading.local()
                        try:
                            self._connect(self._instances[server_key])
                        except Exception as exc:
                            Log.error(
                                f"[CH] Failed to reconnect '{server_key}' "
                                f"after config change: {exc!r}"
                            )
                else:
                    session_settings = self._build_session_settings(conf)
                    self._instances[server_key] = {
                        "server": server_key,
                        "conf": conf,
                        "session_settings": session_settings,
                        "local": threading.local(),
                    }
                    try:
                        self._connect(self._instances[server_key])
                    except Exception as exc:
                        Log.error(
                            f"[CH] Failed to connect new server '{server_key}': {exc!r}"
                        )

    @staticmethod
    def _close_client(instance: dict) -> None:
        """Best-effort close of the current thread's ``clickhouse_connect.Client``."""
        local = instance.get("local")
        if local is None:
            return
        ch_client = getattr(local, "ch_client", None)
        if ch_client is not None:
            try:
                ch_client.close()
            except Exception as exc:
                Log.error(f"[CH] Error closing client: {exc!r}")
            finally:
                local.ch_client = None
