from psycopg2 import pool
import psycopg2.extras

from ..utils.logs import Log
from . import MIN_CONN, MAX_CONN

class Client:

    _instances = {}

    def __init__(self, server_conf):

        for _server_key in server_conf.keys():

            _conf = server_conf[_server_key]
            self._instances[_server_key] = {
                'server': _server_key,
                'conf': _conf
            }

            self.connect(self._instances[_server_key])


    def connect(self, instance):

        conf = instance['conf']
        _max_conn = conf.get('max_conn', MAX_CONN)

        _conn_pool = pool.ThreadedConnectionPool(MIN_CONN, _max_conn, host=conf['host'], port=conf['port'],
                                        dbname=conf['db'], user=conf['user'], password=conf['passwd'])
        instance['conn_pool'] = _conn_pool

        Log.trace('>>> Successfully connected to POSTGRES: {}, {}:{}'.format(instance['server'],
                                                                                 conf['host'], conf['port']))


    def reconnect(self, instance):
        pass


    def disconnect(self, instance):
        pass


    def query(self, server_key, sql_query):
        """
        Executes any given sql query
        :param sql_query:
        :return:
        """

        conn = self._conn(server_key)

        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(sql_query)
        data = [dict(i) for i in cursor.fetchall()]

        self.release_conn(server_key, conn)

        return data


    def _conn(self, server_key):
        """
        :param server_key: database identifier
        :return: raw psycopg2 connector instance
        """
        _instance = self._instances[server_key]
        return _instance['conn_pool'].getconn()


    def release_conn(self, server_key, conn):
        _instance = self._instances[server_key]
        _instance['conn_pool'].putconn(conn)


