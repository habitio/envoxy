from psycopg2.pool import ThreadedConnectionPool
from psycopg2 import OperationalError, DatabaseError, InterfaceError
import psycopg2.extras
import psycopg2.sql as sql
from contextlib import contextmanager
from threading import Semaphore, Lock, local
from time import sleep
import math

from ..db.exceptions import DatabaseException
from ..utils.logs import Log
from ..constants import MIN_CONN, MAX_CONN, TIMEOUT_CONN, DEFAULT_OFFSET_LIMIT, DEFAULT_CHUNK_SIZE


class SemaphoreThreadedConnectionPool(ThreadedConnectionPool):
    
    def __init__(self, minconn, maxconn, *args, **kwargs):
        self._semaphore = Semaphore(maxconn)
        super().__init__(minconn, maxconn, *args, **kwargs)

    def getconn(self, *args, **kwargs):
        self._semaphore.acquire()
        return super().getconn(*args, **kwargs)

    def putconn(self, *args, **kwargs):
        super().putconn(*args, **kwargs)
        self._semaphore.release()


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
        
        for _attempt in range(retries):
        
            try:
            
                return func()
            
            except OperationalError as e:  # Narrowing down the exception
                
                Log.error(f"Error: {repr(e)}. Retrying...")
                
                sleep(delay * (math.pow(2, _attempt)))  # exponential backoff

        raise DatabaseException(f"Failed after {retries} attempts")
                
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

        for _attempt in range(max_retries):
            
            _conn = _instance['conn_pool'].getconn()
            
            if self._is_connection_healthy(_conn):
                return _conn
            
            _conn.close()

            Log.error(f"[PSQL:{server_key}] Connection is not healthy. Retrying...")

            sleep(delay * (math.pow(2, _attempt)))  # exponential backoff
            
        # If we reach here, it means we failed to get a healthy connection after max_retries
        raise DatabaseException("Failed to get a healthy connection")
    
    def _is_connection_healthy(self, conn):
        
        try:
            with conn.cursor() as _cursor:
                _cursor.execute("SELECT 1")
            return True
        except (InterfaceError, DatabaseError): 
            return False
        
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
        if not self._is_connection_healthy(conn):    
            
            conn.close()
            
            _instance = self._instances[server_key]
            
            self.connect(_instance)

        else:
            
            self._instances[server_key]['conn_pool'].putconn(conn)

    @contextmanager
    def transaction(self, server_key):
        """
        Context manager for database transactions.

        :param server_key: Identifier for the server configuration.
        :return: None
        """

        if hasattr(self._thread_local_data, 'conn'):
            raise DatabaseException("Nested transactions are not supported")

        self._thread_local_data.conn = self._get_conn(server_key)
        self._thread_local_data.conn.autocommit = False

        try:
            yield self
            self._thread_local_data.conn.commit()
        except (DatabaseError, DatabaseException) as e:
            Log.error("Rolling back transaction due to error: {}".format(e))
            self._thread_local_data.conn.rollback()
        finally:
            self.release_conn(server_key, self._thread_local_data.conn)
            del self._thread_local_data.conn


    def query(self, server_key=None, sql=None, params=None):
        """
        Executes the provided SQL query and returns the results.
        
        :param server_key: Identifier for the server configuration.
        :param sql_query: SQL query string to be executed.
        :param params: Parameters for the SQL query.
        :return: Query results as a list of dictionaries.
        """

        if params is None:
            params = {}

        if not sql:
            raise DatabaseException("Sql cannot be empty")

        _conn = getattr(self._thread_local_data, 'conn', None) or self._get_conn(server_key)

        try:

            with _conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as _cursor:

                _schema = self._get_conf(server_key, 'schema')
                
                if _schema:
                    _cursor.execute(f"SET search_path TO {_schema}")

                _data = []

                _chunk_size = params.get('chunk_size', DEFAULT_CHUNK_SIZE)
                _offset_limit = params.get('offset_limit', DEFAULT_OFFSET_LIMIT)
                
                params.update({
                    'chunk_size': _chunk_size,
                    'offset_limit': _offset_limit
                })

                while True:
                    
                    _cursor.execute(sql, params)
                    
                    _rowcount = _cursor.rowcount
                    _rows = _cursor.fetchall()

                    _data.extend(list(map(dict, _rows)))

                    _offset_limit += _chunk_size
                    
                    params.update({'offset_limit': _offset_limit})

                    if _rowcount != _chunk_size or 'limit' not in sql.lower():
                        break

                return _data
        
        finally:
            
            if not getattr(self._thread_local_data, 'conn', None):
                # query is not using transaction, release connection
                self.release_conn(server_key, _conn)

    def insert(self, db_table: str, data: dict):
        """
        Inserts a row into the database table.

        :param db_table: Database table name.
        :param data: Dictionary with column names and values.
        :return: None
        """

        if not hasattr(self._thread_local_data, 'conn'):
            raise DatabaseException("Insert must be inside a transaction block")

        _columns = data.keys()

        _query = sql.SQL("""insert into {} ({}) values ({})""").format(
            sql.Identifier(db_table),
            sql.SQL(', ').join(map(sql.Identifier, _columns)),
            sql.SQL(', ').join(sql.Placeholder() * len(_columns)))

        with self._thread_local_data.conn.cursor() as _cursor:
            _cursor.execute(_query, list(data.values()))