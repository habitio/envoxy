from psycopg2 import pool
import psycopg2.extras
import psycopg2.sql as sql
from contextlib import contextmanager

from ..db.exceptions import DatabaseException
from ..utils.logs import Log
from ..constants import MIN_CONN, MAX_CONN

class Client:

    _instances = {}

    __conn = None

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
        _max_conn = int(conf.get('max_conn', MAX_CONN))

        _conn_pool = pool.ThreadedConnectionPool(MIN_CONN, _max_conn, host=conf['host'], port=conf['port'],
                                        dbname=conf['db'], user=conf['user'], password=conf['passwd'])
        instance['conn_pool'] = _conn_pool

        Log.trace('>>> Successfully connected to POSTGRES: {}, {}:{}'.format(instance['server'],
                                                                                 conf['host'], conf['port']))


    def query(self, server_key=None, sql=None, params=None):
        """
        Executes any given sql query
        :param sql_query:
        :return:
        """

        conn = None

        try:

            if not sql:
                raise DatabaseException("Sql cannot be empty")

            conn = self.__conn if self.__conn is not None else self._get_conn(server_key)

            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            schema = self._get_conf(server_key, 'schema')
            if schema: cursor.execute(f"SET search_path TO {schema}")

            cursor.execute(sql, params)
            data = list(map(dict, cursor.fetchall()))

            if self.__conn is None :  self.release_conn(server_key, conn) # query is not using transaction

            return data

        except psycopg2.DatabaseError as e:
            Log.error(e)
            if conn is not None: self.release_conn(server_key, conn)

        return None


    def insert(self, db_table: str, data: dict):

        if not self.__conn:
            raise DatabaseException("Insert must be inside a transaction block")

        columns = data.keys()

        query = sql.SQL("""insert into {} ({}) values ({})""").format(
            sql.Identifier(db_table),
            sql.SQL(', ').join(map(sql.Identifier, columns)),
            sql.SQL(', ').join(sql.Placeholder() * len(columns)))

        conn = self.__conn
        cursor = conn.cursor()

        cursor.execute(query, list(data.values()))


    def _get_conn(self, server_key):
        """
        :param server_key: database identifier
        :return: raw psycopg2 connector instance
        """
        _instance = self._instances[server_key]

        return _instance['conn_pool'].getconn()

    def _get_conf(self, server_key, key):
        return self._instances[server_key]['conf'].get(key, None)

    def release_conn(self, server_key, conn):
        _instance = self._instances[server_key]
        _instance['conn_pool'].putconn(conn)


    @contextmanager
    def transaction(self, server_key):

        self.__conn = self._get_conn(server_key)
        self.__conn.autocommit = False

        try:
            yield self

        except (psycopg2.DatabaseError, DatabaseException) as e :
            Log.error("rollback transaction, {}".format(e))
            self.__conn.rollback()

        finally:
            self.__conn.commit()
            self.release_conn(server_key, self.__conn)
            self.__conn = None


