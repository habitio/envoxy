from ..utils.singleton import Singleton
from ..utils.config import Config

from ..postgresql.client import Client as PgClient
from ..couchdb.client import Client as CouchDBClient
from ..redis.client import Client as RedisDBClient
from ..db.sqlalchemy import get_manager, session_scope, transactional, get_default_server_key

class Connector(Singleton):

    @property
    def postgres(self):
        return self.pgsql_client

    @property
    def couchdb(self):
        return self.couchdb_client

    @property
    def redis(self):
        return self.redis_client

    def start_postgres_conn(self):

        # find postgres configuration and start client

        self._psql_confs = Config.get('psql_servers')

        if not self._psql_confs:
            raise Exception('Error to find PSQL Servers config')

        self.pgsql_client = PgClient(self._psql_confs)

    def start_couchdb_conn(self):
        """
        example for another dbms
        :return:
        """

        self._couchdb_confs = Config.get('couchdb_servers')

        if not self._couchdb_confs:
            raise Exception('Error to find COUCHDB Servers config')

        self.couchdb_client = CouchDBClient(self._couchdb_confs)

    def start_redis_conn(self):

        # find redis configuration and start client

        self._redis_confs = Config.get('redis_servers')
        if not self._redis_confs:
            raise Exception('Error to find REDIS Servers config')

        self.redis_client = RedisDBClient(self._redis_confs)


class CouchConnector(Connector):

    def __init__(self):
        self.start_couchdb_conn()


class PgConnector(Connector):

    def __init__(self):
        self.start_postgres_conn()


class RedisConnector(Connector):

    def __init__(self):
        self.start_redis_conn()


class PgDispatcher:

    @staticmethod
    def query(server_key=None, sql=None, params=None):
        return PgConnector.instance().postgres.query(server_key, sql, params)

    @staticmethod
    def insert(db_table: str, data: dict):
        return PgConnector.instance().postgres.insert(db_table, data)

    @staticmethod
    def transaction(server_key):
        return PgConnector.instance().postgres.transaction(server_key)

    @staticmethod
    def client():
        """Return the underlying Postgres client instance (psycopg2 wrapper)."""
        return PgConnector.instance().postgres

    @staticmethod
    def sa_manager(server_key=None):
        """Return the SQLAlchemy manager for a server_key. If server_key is None,
        the SQLAlchemy helper will select the default configured server.
        """
        key = server_key or get_default_server_key()
        return get_manager(key)

    @staticmethod
    def manager(server_key=None):
        """Alias for sa_manager to match existing client-style API: pgsqlc.manager(...)"""
        return PgDispatcher.sa_manager(server_key)

    @staticmethod
    def session(server_key=None):
        """Return a contextmanager yielding a SQLAlchemy Session bound to server_key.

        Usage: with pgsqlc.session('muzzley') as session: session.query(...)
        """
        return PgDispatcher.sa_session_scope(server_key)

    @staticmethod
    def sa_session_scope(server_key=None):
        """Return a contextmanager for a session bound to server_key."""
        key = server_key or get_default_server_key()
        return session_scope(key)

    @staticmethod
    def sa_transactional(server_key=None):
        """Return a transactional decorator bound to server_key."""
        key = server_key or get_default_server_key()
        return transactional(key)

    @staticmethod
    def transactional(server_key=None):
        """Alias for sa_transactional so callers can use pgsqlc.transactional(server_key)"""
        return PgDispatcher.sa_transactional(server_key)


class CouchDBDispatcher():

    @staticmethod
    def find(db=None, fields=None, params=None):

        return CouchConnector.instance().couchdb.find(db, fields, params)


    @staticmethod
    def get(id:str, db=None):

        return CouchConnector.instance().couchdb.get(id, db)

    @staticmethod
    def post(db=None, payload=None):

        return CouchConnector.instance().couchdb.post(db, payload)

class RedisDBDispatcher():

    @staticmethod
    def get(server_key, key):
        return RedisConnector.instance().redis.get(server_key, key)

    @staticmethod
    def set(server_key, key, value):
        return RedisConnector.instance().redis.set(server_key, key, value)

    @staticmethod
    def client(server_key):
        return RedisConnector.instance().redis.get_client(server_key)
