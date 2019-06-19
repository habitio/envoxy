from ..utils.singleton import Singleton
from ..utils.config import Config

from ..postgresql.dispatcher import Client as PgClient


class Connector(Singleton):

    def __init__(self):
        self.start_postgres_conn()

    @property
    def postgres(self):
        return self.postgres_client


    def start_postgres_conn(self):

        # find postgres configuration and start client

        self._server_confs = Config.get('psql_servers')

        if not self._server_confs:
            raise Exception('Error to find PSQL Servers config')

        self.postgres_client = PgClient(self._server_confs)


    def start_couchdb_conn(self):
        """
        example for another dbms
        :return:
        """

        self._server_confs = Config.get('couchdb_servers')

        if not self._server_confs:
            raise Exception('Error to find COUCHDB Servers config')



class PgDispatcher():

    @staticmethod
    def query(server_key=None, sql=None):

        return Connector.instance().postgres.query(server_key, sql)

    @staticmethod
    def insert(db_table: str, data: dict):

        return Connector.instance().postgres.insert(db_table, data)

    @staticmethod
    def transaction(server_key):

        return Connector.instance().postgres.transaction(server_key)
