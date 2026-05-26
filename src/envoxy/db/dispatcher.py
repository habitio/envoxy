"""
Database dispatcher module.
Provides access to configured database clients and SQLAlchemy session/transaction
managers.
"""

from ..utils.singleton import Singleton
from ..utils.config import Config

from ..postgresql.client import Client as PgClient
from ..couchdb.client import Client as CouchDBClient
from ..redis.client import Client as RedisDBClient
from ..clickhouse.client import Client as ClickHouseClient
from ..db.orm import get_manager, session_scope, transactional, get_default_server_key


class Connector(Singleton):
    """
    Connector is a singleton class responsible for managing database connections to PostgreSQL, CouchDB, and Redis.

    Attributes:
        postgres (PgClient): Property to access the PostgreSQL client instance.
        couchdb (CouchDBClient): Property to access the CouchDB client instance.
        redis (RedisDBClient): Property to access the Redis client instance.
    """

    @property
    def postgres(self):
        """
        Returns the PostgreSQL client instance.

        This method provides access to the underlying PostgreSQL client used for database operations.

        Returns:
            pgsql_client: The client instance for interacting with the PostgreSQL database.
        """
        return self.pgsql_client

    @property
    def clickhouse(self):
        """
        Returns the ClickHouse client instance.

        Returns:
            ClickHouseClient: The read-only client for ClickHouse analytics queries.
        """
        return self.clickhouse_client

    @property
    def couchdb(self):
        """
        Returns the CouchDB client instance.

        :return: The CouchDB client used for database operations.
        :rtype: CouchDBClient
        """
        return self.couchdb_client

    @property
    def redis(self):
        """
        Returns the Redis client instance used for database operations.

        Returns:
            redis.Redis: The Redis client object.
        """
        return self.redis_client

    def start_postgres_conn(self):
        """
        Initializes a PostgreSQL client connection using configuration settings.

        Retrieves PostgreSQL server configurations from the application's config.
        Raises an exception if the configuration is missing.
        Instantiates a PgClient with the retrieved configurations and assigns it to `self.pgsql_client`.
        """

        # find postgres configuration and start client

        self._psql_confs = Config.get("psql_servers")

        if not self._psql_confs:
            raise Exception("Error to find PSQL Servers config")

        self.pgsql_client = PgClient(self._psql_confs)

    def start_couchdb_conn(self):
        """
        Initializes a connection to CouchDB using server configurations.

        Retrieves CouchDB server configurations from the application's config.
        Raises an exception if the configuration is missing.
        Instantiates a CouchDBClient with the retrieved configurations.

        Raises:
            Exception: If CouchDB server configurations are not found.
        """

        self._couchdb_confs = Config.get("couchdb_servers")

        if not self._couchdb_confs:
            raise Exception("Error to find COUCHDB Servers config")

        self.couchdb_client = CouchDBClient(self._couchdb_confs)

    def start_redis_conn(self):
        """
        Initializes a Redis client connection using configuration settings.

        Retrieves Redis server configurations from the application's Config object.
        Raises an exception if the configuration is missing.
        Instantiates a RedisDBClient with the retrieved configurations and assigns it to self.redis_client.
        """

        # find redis configuration and start client

        self._redis_confs = Config.get("redis_servers")
        if not self._redis_confs:
            raise Exception("Error to find REDIS Servers config")

        self.redis_client = RedisDBClient(self._redis_confs)

    def start_clickhouse_conn(self):
        """
        Initializes a ClickHouse client using configuration settings.

        Retrieves ClickHouse server configurations from ``clickhouse_servers`` in
        the application config.  Raises an exception if the key is missing.
        Instantiates a ``ClickHouseClient`` and assigns it to
        ``self.clickhouse_client``.

        The ClickHouse client is read-only by design: no insert / update /
        delete methods are exposed.
        """

        self._ch_confs = Config.get("clickhouse_servers")

        if not self._ch_confs:
            raise Exception("Error to find ClickHouse Servers config")

        self.clickhouse_client = ClickHouseClient(self._ch_confs)


class CouchConnector(Connector):
    """
    CouchConnector is a Connector subclass responsible for establishing a connection to a CouchDB database.

    Methods
    -------
    __init__():
        Initializes the CouchConnector instance and starts the CouchDB connection by calling start_couchdb_conn().
    """

    def __init__(self):
        self.start_couchdb_conn()


class PgConnector(Connector):
    """
    PgConnector is a subclass of Connector that manages the initialization of a PostgreSQL database connection.

    Methods
    -------
    __init__():
        Initializes the PgConnector instance and starts the PostgreSQL connection by calling start_postgres_conn().
    """

    def __init__(self):
        self.start_postgres_conn()


class RedisConnector(Connector):
    """
    RedisConnector is a subclass of Connector that manages the connection to a Redis database.

    Methods
    -------
    __init__():
        Initializes the RedisConnector instance and starts the Redis connection by calling start_redis_conn().
    """

    def __init__(self):
        self.start_redis_conn()


class ChConnector(Connector):
    """
    ChConnector manages a read-only ClickHouse client singleton.

    Reads configuration from ``clickhouse_servers`` in the app config and
    instantiates a ``ClickHouseClient`` that enforces read-only access at the
    protocol level (``readonly=2``).

    Methods
    -------
    __init__():
        Initializes the connector by calling ``start_clickhouse_conn()``.
    """

    def __init__(self):
        self.start_clickhouse_conn()


class PgDispatcher:
    """
    PgDispatcher provides a static interface for interacting with PostgreSQL databases,
    including direct queries, inserts, transaction management, and SQLAlchemy integration.
    """

    @staticmethod
    def query(server_key=None, sql=None, params=None):
        """
        Executes a SQL query on the specified PostgreSQL server.

        Args:
            server_key (str, optional): Identifier for the target PostgreSQL server. Defaults to None.
            sql (str, optional): The SQL query to execute. Defaults to None.
            params (tuple or dict, optional): Parameters to pass with the SQL query. Defaults to None.

        Returns:
            Any: The result of the executed SQL query, as returned by the PgConnector.

        Raises:
            Exception: If the query execution fails.
        """
        return PgConnector.instance().postgres.query(server_key, sql, params)

    # Direct inserts are intentionally not exposed to encourage ORM usage.
    # Use SQLAlchemy models and sessions via sa_manager(), or raw query() if needed.

    @staticmethod
    def transaction(server_key):
        """
        Initiates a PostgreSQL transaction for the specified server.

        Args:
            server_key (str): The key identifying the PostgreSQL server.

        Returns:
            Transaction: An object representing the database transaction.

        Raises:
            Exception: If the transaction cannot be started.
        """
        return PgConnector.instance().postgres.transaction(server_key)

    @staticmethod
    def client():
        """
        Returns the underlying PostgreSQL client instance used for database operations.

        This function provides access to the internal PostgreSQL client, which is a
        psycopg2 wrapper managed by the PgConnector singleton. It can be used to
        perform direct database interactions when higher-level abstractions are not
        sufficient.

        Returns:
            psycopg2.extensions.connection: The PostgreSQL client instance.
        """
        return PgConnector.instance().postgres

    @staticmethod
    def sa_manager(server_key=None):
        """
        Retrieves a SQLAlchemy manager instance for the specified server key.
        If no server key is provided, the default server key is used.
        Args:
            server_key (str, optional): The key identifying the server configuration. Defaults to None.
        Returns:
            Manager: The SQLAlchemy manager instance associated with the given server key.
        """
        key = server_key or get_default_server_key()
        return get_manager(key)

    @staticmethod
    def sa_session(server_key=None):
        """
        Creates and returns a SQLAlchemy session for the specified server key.
        Args:
            server_key (str, optional): The key identifying the database server. If not provided, the default server key is used.
        Returns:
            Session: A SQLAlchemy session scoped to the specified server.
        """
        key = server_key or get_default_server_key()
        return session_scope(key)

    @staticmethod
    def sa_transactional(server_key=None):
        """
        Decorator to wrap a function in a SQLAlchemy transactional context.
        Args:
            server_key (str, optional): The key identifying the database server.
                If not provided, the default server key is used.
        Returns:
            function: A decorator that applies a transactional context using the specified server key.
        """
        key = server_key or get_default_server_key()
        return transactional(key)


class CouchDBDispatcher:
    """
    CouchDBDispatcher provides static methods to interact with a CouchDB database via a CouchConnector instance.
    """

    @staticmethod
    def find(db=None, fields=None, params=None):
        """
        Finds documents in the specified CouchDB database using given fields and parameters.

        Args:
            db (str, optional): The name of the database to query. Defaults to None.
            fields (list, optional): List of fields to include in the result. Defaults to None.
            params (dict, optional): Query parameters for filtering documents. Defaults to None.

        Returns:
            list: A list of documents matching the query criteria.
        """

        return CouchConnector.instance().couchdb.find(db, fields, params)

    @staticmethod
    def get(id: str, db=None):
        """
        Retrieve a document from the CouchDB database by its ID.

        Args:
            id (str): The unique identifier of the document to retrieve.
            db (optional): The database instance or name to query. Defaults to None.

        Returns:
            dict: The document retrieved from the database.

        Raises:
            Exception: If the document cannot be retrieved or does not exist.
        """

        return CouchConnector.instance().couchdb.get(id, db)

    @staticmethod
    def post(db=None, payload=None):
        """
        Posts the given payload to the specified CouchDB database.

        Args:
            db (str, optional): The name of the CouchDB database to post to.
            payload (dict, optional): The data to be posted to the database.

        Returns:
            dict: The response from the CouchDB server after posting the payload.
        """

        return CouchConnector.instance().couchdb.post(db, payload)


class RedisDBDispatcher:
    """
    RedisDBDispatcher provides static methods to interact with Redis through a RedisConnector instance.
    """

    @staticmethod
    def get(server_key, key):
        """
        Retrieve a value from Redis using the specified server key and key.

        Args:
            server_key (str): The key identifying the Redis server or namespace.
            key (str): The key whose value is to be retrieved from Redis.

        Returns:
            Any: The value associated with the given key in Redis, or None if the key does not exist.
        """
        return RedisConnector.instance().redis.get(server_key, key)

    @staticmethod
    def set(server_key, key, value):
        """
        Sets a value in the Redis database for the specified server and key.

        Args:
            server_key (str): The key identifying the Redis server or namespace.
            key (str): The key under which the value will be stored.
            value (Any): The value to store in Redis.

        Returns:
            bool: True if the operation was successful, False otherwise.
        """
        return RedisConnector.instance().redis.set(server_key, key, value)

    @staticmethod
    def client(server_key):
        """
        Retrieve a Redis client instance associated with the given server key.

        Args:
            server_key (str): The key identifying the Redis server.

        Returns:
            redis.client.Redis: A Redis client instance connected to the specified server.
        """
        return RedisConnector.instance().redis.get_client(server_key)


class ClickHouseDispatcher:
    """
    Static interface for executing read-only analytics queries against ClickHouse.

    This dispatcher mirrors the shape of ``PgDispatcher`` so that call sites can
    swap between the two with minimal friction.  Only ``query()`` is exposed —
    there are intentionally no insert / update / delete / transaction methods.

    Usage::

        from envoxy import chsqlc

        results = chsqlc.query(
            "analytics",
            "SELECT COUNT(*) AS count FROM raw.policies WHERE toString(application_id) = {app_id:String}",
            params={"app_id": "some-uuid"},
        )
        # results → [{"count": 42}]

    Per-query ClickHouse settings can be overridden::

        results = chsqlc.query(
            "analytics",
            heavy_sql,
            params=params,
            query_settings={"max_execution_time": 120, "max_threads": 8},
        )
    """

    @staticmethod
    def query(
        server_key: str,
        sql: str,
        params: dict | None = None,
        query_settings: dict | None = None,
    ) -> list[dict]:
        """
        Execute a read-only SQL query against ClickHouse.

        Args:
            server_key (str):
                Config key matching an entry under ``clickhouse_servers``.
            sql (str):
                ClickHouse SQL.  Use ``{name:Type}`` placeholders for
                parameter binding (e.g. ``{app_id:String}``).
            params (dict | None):
                Named parameters bound to the query.  Values are Python-typed;
                ``clickhouse_connect`` converts them to the correct wire format.
            query_settings (dict | None):
                Optional per-query ClickHouse server settings, e.g.
                ``{"max_execution_time": 120}``.  Merged on top of the
                client-level defaults.

        Returns:
            list[dict]: Each dict maps column name → normalised Python value.

        Raises:
            DatabaseException: On connection failure or missing config.
            clickhouse_connect.driver.exceptions.DatabaseError:
                Propagated directly for query-level errors (bad SQL, etc.).
        """
        return ChConnector.instance().clickhouse.query(
            server_key, sql, params, query_settings
        )

    @staticmethod
    def client() -> "ClickHouseClient":
        """
        Return the underlying ``ClickHouseClient`` instance for advanced usage.

        Returns:
            ClickHouseClient: The singleton client instance.
        """
        return ChConnector.instance().clickhouse
