import redis

from ..constants import REDIS_DEFAULT_PORT, REDIS_DEFAULT_HOST, REDIS_DEFAULT_DB, REDIS_DEFAULT_TTL
from ..utils.logs import Log
from ..utils.encoders import envoxy_json_dumps, envoxy_json_loads

class Client:

    _instances = {}

    __conn = None

    def __init__(self, server_conf):

        for _server_key in server_conf.keys():

            _conf = server_conf[_server_key]
            _ttl = _conf.get('ttl', REDIS_DEFAULT_TTL)

            self._instances[_server_key] = {
                'server': _server_key,
                'conf': _conf,
                'ttl': _ttl
            }

            self.connect(self._instances[_server_key])

    def connect(self, instance):

        _config = instance['conf']

        _bind = _config.get('bind', '')
        _db = _config.get('db', REDIS_DEFAULT_DB)

        if ':' in _bind:
            _host, _port = tuple(_bind.split(':'))
        else:
            _host = _config.get('host', REDIS_DEFAULT_HOST)
            _port = _config.get('port', REDIS_DEFAULT_PORT)

        instance['conn'] = redis.Redis(host=_host, port=_port, db=_db)

        Log.trace('>>> Successfully connected to REDIS: {}, {}:{}'.format(instance['server'], _host, _port))


    def get(self, server_key, key):
        _conn = self.__conn if self.__conn is not None else self.get_client(server_key)

        _data = _conn.get(key)

        return envoxy_json_loads(_data.encode('utf-8')) if _data else None

    def set(self, server_key, key, value, ttl=None):
        _instance = self._instances[server_key]
        
        _conn = self.__conn if self.__conn is not None else _instance['conn']

        _data = envoxy_json_dumps(value).decode('utf-8')

        return _conn.set(key, _data, ex=ttl if ttl else _instance['ttl'])

    def get_client(self, server_key):
        return self._instances[server_key]['conn']
