import base64

import redis

from ..constants import REDIS_DEFAULT_DB, REDIS_DEFAULT_HOST, REDIS_DEFAULT_PORT, REDIS_DEFAULT_TTL
from ..utils.encoders import envoxy_json_dumps, envoxy_json_loads


class RedisCache:

    def __init__(self, config):

        _bind = config.get('bind', '')
        _db = config.get('db', REDIS_DEFAULT_DB)

        self.ttl = config.get('ttl', REDIS_DEFAULT_TTL)
        self.key_prefix = config.get('key_prefix')

        if ':' in _bind:
            _host, _port = tuple(_bind.split(':'))
        else:
            _host = config.get('host', REDIS_DEFAULT_HOST)
            _port = config.get('port', REDIS_DEFAULT_PORT)

        self.r = redis.Redis(host=_host, port=_port, db=_db)

    def _encode_params(self, _json_params):
        _bytes_params = envoxy_json_dumps(_json_params)
        return base64.urlsafe_b64encode(_bytes_params).decode()

    def _decode_params(self, params):
        return envoxy_json_loads(base64.urlsafe_b64decode(params).decode())

    def _get_key(self, endpoint, method, params):

        _b64params = self._encode_params(params)
        _key = f'{self.key_prefix}:{endpoint}:{method}:{_b64params}'
        _data = self.r.get(_key)
        return envoxy_json_loads(_data) if _data else {}

    def _set_key(self, endpoint, method, params, json_data, ttl=None):

        _b64params = self._encode_params(params)
        _key = f'{self.key_prefix}:{endpoint}:{method}:{_b64params}'
        _data = envoxy_json_dumps(json_data)
        self.r.set(_key, _data)

        ttl = ttl if ttl else self.ttl
        
        return self.r.expire(_key, ttl)

    def get(self, endpoint, method, params):
        return self._get_key(endpoint, method, params)

    def set(self, endpoint, method, params, json_data, ttl=None):
        return self._set_key(endpoint, method, params, json_data, ttl=ttl)
