import math
import uuid
import re
from time import sleep
from threading import BoundedSemaphore as _BoundedSemaphore, Lock, local
from datetime import datetime, timezone
from contextlib import contextmanager

from psycopg2.pool import ThreadedConnectionPool
from psycopg2 import OperationalError, DatabaseError, InterfaceError
import psycopg2.extras
import psycopg2.sql as sql

from ..db.orm.session import dispose_manager
from ..db.exceptions import DatabaseException
from ..utils.logs import Log
from ..constants import MIN_CONN, MAX_CONN, TIMEOUT_CONN, DEFAULT_OFFSET_LIMIT, DEFAULT_CHUNK_SIZE


class SemaphoreThreadedConnectionPool(ThreadedConnectionPool):
    
    def __init__(self, minconn, maxconn, *args, **kwargs):
        # use BoundedSemaphore to detect excessive releases
        self._semaphore = _BoundedSemaphore(maxconn)
        super().__init__(minconn, maxconn, *args, **kwargs)

    def getconn(self, *args, timeout=None, **kwargs):
        """
        Acquire the semaphore with an optional timeout before getting a connection
        from the underlying pool. If acquire fails within the timeout, raise a
        DatabaseException to avoid indefinite blocking.
        """
        acquired = self._semaphore.acquire(timeout=timeout)
        if not acquired:
            raise DatabaseException("Timeout waiting for DB connection")

        try:
            return super().getconn(*args, **kwargs)
        except Exception:
            # If obtaining the connection from the underlying pool failed,
            # release the semaphore to avoid leaks and re-raise.
            try:
                self._semaphore.release()
            except Exception:
                pass
            raise

    def putconn(self, *args, **kwargs):
        # Ensure we always attempt to return the connection to the pool and
        # release the semaphore. If super().putconn raises, we still attempt
        # to release the semaphore to avoid deadlock. Use a best-effort
        # pattern because releasing an un-acquired semaphore will raise, so
        # guard it in a try/except.
        try:
            super().putconn(*args, **kwargs)
        except Exception as e:
            Log.error(f"Connection pool putconn() raised: {e}")
            # still attempt to release the semaphore to avoid deadlock
            try:
                self._semaphore.release()
            except Exception as release_exc:
                Log.error(f"Failed to release semaphore after putconn error: {release_exc}")
            raise
        else:
            try:
                self._semaphore.release()
            except Exception as release_exc:
                # BoundedSemaphore raises ValueError on excessive release
                Log.error(f"Semaphore release error: {release_exc}")


class Client:
    """
    Client for PostgreSQL database.
    """

    _instance = None
    _lock = Lock()
    _thread_local_data = local()  # Used for thread-local storage

    def __new__(cls, *args, **kwargs):
        
        with cls._lock:
                
            if not cls._instance:
                cls._instance = super(Client, cls).__new__(cls)
        
        return cls._instance

    def __init__(self, server_conf):
        # make __init__ idempotent for singleton pattern
        if getattr(self, '_initialized', False):
            return
        self._initialized = True

        self._instances = {}

        for _server_key, _conf in server_conf.items():
            with self._lock:
                self._instances[_server_key] = {
                    'server': _server_key,
                    'conf': _conf,
                }

            self.connect(self._instances[_server_key])
    
    def _retry_on_failure(self, func, retries=3, delay=1):
        
        """
        Retry a function in case of exceptions.
        
        :param func: Function to be executed.
        :param retries: Number of retries.
        :param delay: Delay between retries.
        """
        
        last_exc = None
        for _attempt in range(retries):
            try:
                return func()
            except (OperationalError, InterfaceError, DatabaseError) as e:
                last_exc = e
                Log.error(f"Error: {repr(e)}. Retrying...")
                sleep(delay * (math.pow(2, _attempt)))  # exponential backoff

        raise DatabaseException(f"Failed after {retries} attempts: {last_exc}") from last_exc
                
    def _get_conn(self, server_key, max_retries=3, delay=1):
        """
        Returns a connection from the pool.

        :param server_key: Identifier for the server configuration.
        :param max_retries: Number of retries to get a healthy connection.
        :param delay: Delay between retries.
        :return: Database connection.
        """
  
        _instance = self._instances.get(server_key)
            
        if not _instance:
            raise DatabaseException(f"No configuration found for server key: {server_key}")

        if 'conn_pool' not in _instance:
            self.connect(_instance)

        # Determine per-connection acquire timeout from config (seconds)
        _conn_timeout = int(_instance['conf'].get('conn_timeout', TIMEOUT_CONN))

        for _attempt in range(max_retries):
            try:
                _conn = _instance['conn_pool'].getconn(timeout=_conn_timeout)
            except Exception as e:
                Log.error(f"[PSQL:{server_key}] Failed to get connection from pool: {e}")
                sleep(delay * (math.pow(2, _attempt)))
                continue

            if self._is_connection_healthy(_conn):
                return _conn

            # Return/close broken connection to the pool
            try:
                _instance['conn_pool'].putconn(_conn, close=True)
            except Exception:
                try:
                    _conn.close()
                except Exception:
                    pass

            Log.error(f"[PSQL:{server_key}] Connection is not healthy. Retrying...")

            sleep(delay * (math.pow(2, _attempt)))  # exponential backoff
            
        # If we reach here, it means we failed to get a healthy connection after max_retries
        raise DatabaseException("Failed to get a healthy connection")
    
    def _is_connection_healthy(self, conn):
        if not conn:
            return False

        try:
            with conn.cursor() as _cursor:
                _cursor.execute("SELECT 1")
            return True
        except (InterfaceError, DatabaseError):
            return False

    def reload_config(self, server_conf):
        """Reload the client configuration safely.

        This will update existing server entries and add new ones. It will
        not tear down existing pools for servers that remain unchanged.
        """

        with self._lock:
            # find removed keys
            existing_keys = set(self._instances.keys())
            new_keys = set(server_conf.keys())

            removed = existing_keys - new_keys
            for rk in removed:
                # dispose any SQLAlchemy managers tied to removed servers
                try:
                    dispose_manager(rk)
                except Exception:
                    Log.error(f"Failed to dispose manager for removed server {rk}")
                # attempt to close pool if present
                try:
                    inst = self._instances.pop(rk, None)
                    if inst and inst.get('conn_pool'):
                        try:
                            inst['conn_pool'].closeall()
                        except Exception:
                            pass
                except Exception:
                    pass

            for _server_key, _conf in server_conf.items():
                if _server_key in self._instances:
                    # update conf in-place; do not drop existing pool unless
                    # the configuration specifically changed (simple check).
                    old = self._instances[_server_key]['conf']
                    if old != _conf:
                        # replace conf and reconnect pool
                        self._instances[_server_key]['conf'] = _conf
                        try:
                            # dispose SQLAlchemy manager so callers get a fresh Engine
                            dispose_manager(_server_key)
                        except Exception:
                            Log.error(f"Failed to dispose manager for server {_server_key}")
                        try:
                            self.connect(self._instances[_server_key])
                        except Exception as e:
                            Log.error(f"Failed to reconnect server {_server_key}: {e}")
                else:
                    self._instances[_server_key] = {'server': _server_key, 'conf': _conf}
                    try:
                        self.connect(self._instances[_server_key])
                    except Exception as e:
                        Log.error(f"Failed to connect new server {_server_key}: {e}")
        
    def _get_conf(self, server_key, key):
        """
        Returns a configuration value for the server.

        :param server_key: Identifier for the server configuration.
        :param key: Configuration key.
        :return: Configuration value.
        """
        
        return self._instances[server_key]['conf'].get(key, None)
        
    def connect(self, instance, reconnect_attempts=3, reconnect_delay=1):
        """
        Connects to the database server.

        :param instance: Instance configuration.
        :param reconnect_attempts: Number of attempts to reconnect.
        :param reconnect_delay: Delay between reconnection attempts.
        :return: None
        """
    
        _conf = instance['conf']

        _max_conn = int(_conf.get('max_conn', MAX_CONN))
        _timeout = int(_conf.get('timeout', TIMEOUT_CONN))
                
        _conn_pool = self._retry_on_failure(
            lambda: SemaphoreThreadedConnectionPool(
                MIN_CONN, 
                _max_conn, 
                host=_conf['host'], 
                port=_conf['port'],
                dbname=_conf['db'], 
                user=_conf['user'], 
                password=_conf['passwd'],
                connect_timeout=_timeout
            ),
            retries=reconnect_attempts,
            delay=reconnect_delay
        )

        with self._lock:
            instance['conn_pool'] = _conn_pool

        Log.trace('>>> Successfully connected to POSTGRES: {}, {}:{}'.format(
            instance['server'],
            _conf['host'], 
            _conf['port']
        ))

    def release_conn(self, server_key, conn):
        """
        Releases a connection back to the pool.

        :param server_key: Identifier for the server configuration.
        :param conn: Database connection.
        :return: None
        """

        # Check and handle broken connections upon release
        _instance = self._instances.get(server_key)
        if not _instance:
            # Unknown server key; try to close the connection
            try:
                conn.close()
            except Exception:
                pass
            return

        pool = _instance.get('conn_pool')

        # consult per-instance config whether to run health checks on release
        health_check = True
        try:
            health_check = bool(_instance['conf'].get('health_check_on_release', True))
        except Exception:
            health_check = True

        if health_check and not self._is_connection_healthy(conn):
            # Return the broken connection to the pool and mark it closed.
            try:
                if pool is not None:
                    pool.putconn(conn, close=True)
                else:
                    conn.close()
            except Exception:
                try:
                    conn.close()
                except Exception:
                    pass
        else:
            try:
                pool.putconn(conn)
            except Exception:
                try:
                    conn.close()
                except Exception:
                    pass

    @contextmanager
    def transaction(self, server_key):
        """
        Context manager for database transactions.

        :param server_key: Identifier for the server configuration.
        :return: None
        """

        if hasattr(self._thread_local_data, 'conn'):
            raise DatabaseException("Nested transactions are not supported")

        conn = self._get_conn(server_key)
        prev_autocommit = getattr(conn, 'autocommit', True)
        conn.autocommit = False
        self._thread_local_data.conn = conn

        try:
            yield self
            conn.commit()
        except Exception as e:
            Log.error("Rolling back transaction due to error: {}".format(e))
            try:
                conn.rollback()
            except Exception as rollback_exc:
                Log.error(f"Rollback failed: {rollback_exc}")
            # Re-raise so callers can detect failures
            raise
        finally:
            # restore autocommit before releasing to the pool
            try:
                conn.autocommit = prev_autocommit
            except Exception:
                pass

            self.release_conn(server_key, conn)
            try:
                del self._thread_local_data.conn
            except Exception:
                pass


    def query(self, server_key=None, sql_query=None, params=None):
        """
        Executes the provided SQL query and returns the results.
        
        :param server_key: Identifier for the server configuration.
        :param sql_query: SQL query string to be executed.
        :param params: Parameters for the SQL query.
        :return: Query results as a list of dictionaries.
        """

        if params is None:
            params = {}

        if not sql_query:
            raise DatabaseException("Sql cannot be empty")

        _conn = getattr(self._thread_local_data, 'conn', None) or self._get_conn(server_key)

        try:
            with _conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as _cursor:

                _schema = self._get_conf(server_key, 'schema')
                if _schema:
                    # Safely quote the schema identifier
                    _cursor.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(_schema)))

                _data = []

                # copy params to avoid mutating caller's dictionary
                _local_params = dict(params)

                _chunk_size = _local_params.get('chunk_size', DEFAULT_CHUNK_SIZE)
                _offset_limit = _local_params.get('offset_limit', DEFAULT_OFFSET_LIMIT)

                _local_params.update({
                    'chunk_size': _chunk_size,
                    'offset_limit': _offset_limit
                })

                while True:
                    _cursor.execute(sql_query, _local_params)

                    _rowcount = _cursor.rowcount
                    _rows = _cursor.fetchall()

                    _data.extend(list(map(dict, _rows)))

                    _offset_limit += _chunk_size
                    _local_params.update({'offset_limit': _offset_limit})

                    if _rowcount != _chunk_size or 'limit' not in sql_query.lower():
                        break

                return _data
        finally:
            if not getattr(self._thread_local_data, 'conn', None):
                # query is not using transaction, release connection
                self.release_conn(server_key, _conn)

    def insert(self, db_table: str, data: dict, returning=None):
        """
        Inserts a row into the database table.

        :param db_table: Database table name.
        :param data: Dictionary with column names and values.
        :param returning: optional column name or list to RETURN
        :return: returned value(s) when using RETURNING, or None
        """

        if not hasattr(self._thread_local_data, 'conn'):
            raise DatabaseException("Insert must be inside a transaction block")

        # copy input so we don't mutate caller dict
        _data = dict(data)

        # Ensure id and timestamps and href are set by Python
        if 'id' not in _data or not _data.get('id'):
            _data['id'] = str(uuid.uuid4())

        now = datetime.now(timezone.utc)
        if 'created' not in _data or not _data.get('created'):
            _data['created'] = now
        # always set updated to now
        _data['updated'] = now

        # href: if not provided, derive from table name and id
        if 'href' not in _data or not _data.get('href'):
            # extract table name if schema-qualified
            if '.' in db_table:
                _entity = db_table.split('.', 1)[1]
            else:
                _entity = db_table
            _data['href'] = f"/v3/data-layer/{_entity}/{_data['id']}"

        # validate href pattern and length
        if len(_data['href']) > 1024:
            raise DatabaseException('href too long')

        _href_re = re.compile(r"^/v3/data-layer/[A-Za-z0-9_\-]+/[0-9a-fA-F\-]{36}$")
        if not _href_re.match(_data['href']):
            raise DatabaseException('href does not match required pattern')

        _columns = list(_data.keys())

        placeholders = sql.SQL(', ').join(sql.Placeholder() * len(_columns))
        cols_sql = sql.SQL(', ').join(map(sql.Identifier, _columns))

        # support schema-qualified table names
        parts = db_table.split('.', 1)
        table_ident = sql.Identifier(parts[0], parts[1]) if len(parts) == 2 else sql.Identifier(db_table)

        if returning:
            if isinstance(returning, (list, tuple)):
                returning_sql = sql.SQL(', ').join(map(sql.Identifier, returning))
            else:
                returning_sql = sql.Identifier(returning)

            _query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING {}")
            _query = _query.format(table_ident, cols_sql, placeholders, returning_sql)
        else:
            _query = sql.SQL("INSERT INTO {} ({}) VALUES ({})")
            _query = _query.format(table_ident, cols_sql, placeholders)

        with self._thread_local_data.conn.cursor() as _cursor:
            _cursor.execute(_query, list(_data.values()))

            if returning:
                # fetchone() for RETURNING; return scalar for single column
                row = _cursor.fetchone()
                if row is None:
                    return None
                if isinstance(returning, (list, tuple)):
                    return row
                return row[0]