import redis
import json

from ..constants import REDIS_DEFAULT_PORT, REDIS_DEFAULT_HOST, REDIS_DEFAULT_DB, REDIS_DEFAULT_TTL
from ..utils.logs import Log

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

        config = instance['conf']

        _bind = config.get('bind', '')
        _db = config.get('db', REDIS_DEFAULT_DB)
        _ttl = config.get('ttl', REDIS_DEFAULT_TTL)

        if ':' in _bind:
            _host, _port = tuple(_bind.split(':'))
        else:
            _host = config.get('host', REDIS_DEFAULT_HOST)
            _port = config.get('port', REDIS_DEFAULT_PORT)

        instance['conn'] = redis.Redis(host=_host, port=_port, db=_db)

        Log.trace('>>> Successfully connected to REDIS: {}, {}:{}'.format(instance['server'], _host, _port))


    def get(self, server_key, key):
        conn = self.__conn if self.__conn is not None else self.get_client(server_key)

        data = conn.get(key)
        return json.loads(data) if data else None

    def set(self, server_key, key, value):
        conn = self.__conn if self.__conn is not None else self.get_client(server_key)

        data = json.dumps(value)
        return conn.set(key, data)

    def get_client(self, server_key):
        return self._instances[server_key]['conn']
