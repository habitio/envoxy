from ..utils.singleton import Singleton
from ..utils.config import Config

from ..postgresql.dispatcher import Client as PgClient
from ..couchdb.client import Client as CouchDBClient


class Connector(Singleton):

    @property
    def postgres(self):
        return self.pgsql_client

    @property
    def couchdb(self):
        return self.couchdb_client

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


class CouchConnector(Connector):

    def __init__(self):
        self.start_couchdb_conn()

class PgConnector(Connector):

    def __init__(self):
        self.start_postgres_conn()

class PgDispatcher():

    @staticmethod
    def query(server_key=None, sql=None, params=None):

        return PgConnector.instance().postgres.query(server_key, sql, params)

    @staticmethod
    def insert(db_table: str, data: dict):

        return PgConnector.instance().postgres.insert(db_table, data)

    @staticmethod
    def transaction(server_key):

        return PgConnector.instance().postgres.transaction(server_key)


class CouchDBDispatcher():

    @staticmethod
    def find(db=None, fields=None, params=None):

        return CouchConnector.instance().couchdb.find(db, fields, params)


    @staticmethod
    def get(id:str, db=None):

        return CouchConnector.instance().couchdb.get(id, db)
