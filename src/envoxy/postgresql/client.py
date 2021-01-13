from psycopg2 import pool
import psycopg2.extras
import psycopg2.sql as sql
from contextlib import contextmanager

from ..db.exceptions import DatabaseException
from ..utils.logs import Log
from ..constants import MIN_CONN, MAX_CONN, TIMEOUT_CONN, DEFAULT_OFFSET_LIMIT, DEFAULT_CHUNK_SIZE
from ..asserts import assertz


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
        _timeout = int(conf.get('timeout', TIMEOUT_CONN))

        try:
            _conn_pool = pool.ThreadedConnectionPool(MIN_CONN, _max_conn, host=conf['host'], port=conf['port'],
                                            dbname=conf['db'], user=conf['user'], password=conf['passwd'],
                                                     connect_timeout=_timeout)
            instance['conn_pool'] = _conn_pool

            Log.trace('>>> Successfully connected to POSTGRES: {}, {}:{}'.format(instance['server'],
                                                                                     conf['host'], conf['port']))
        except psycopg2.OperationalError as e:
            Log.error('>>PGSQL ERROR {} {}'.format(conf.get('server'), e))


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

            data = []
            chunk_size = params.get('chunk_size') or DEFAULT_CHUNK_SIZE
            offset_limit = params.get('offset_limit') or DEFAULT_OFFSET_LIMIT
            params.update({
                'chunk_size': chunk_size,
                'offset_limit': offset_limit
            })

            try:
                while True:
                    cursor.execute(sql, params)
                    rowcount = cursor.rowcount
                    rows = cursor.fetchall()

                    data.extend(list(map(dict, rows)))

                    offset_limit += chunk_size
                    params.update({'offset_limit': offset_limit})

                    if rowcount != chunk_size or 'limit' not in sql.lower():
                        break

                if self.__conn is None :  self.release_conn(server_key, conn) # query is not using transaction

                return data

            except KeyError as e:
                Log.error(e)
                if conn is not None: self.release_conn(server_key, conn)

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

        assertz('conn_pool' in _instance, f"getconn failed on {server_key} db", _error_code=0, _status_code=412)

        return _instance.get('conn_pool').getconn()

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


