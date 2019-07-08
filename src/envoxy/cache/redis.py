import redis
import base64
import json

from ..constants import REDIS_DEFAULT_PORT, REDIS_DEFAULT_HOST, REDIS_DEFAULT_DB, REDIS_DEFAULT_TTL

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
        _string_params = json.dumps(_json_params)
        return base64.urlsafe_b64encode(_string_params.encode()).decode()

    def _decode_params(self, _string_params):
        return json.loads(base64.urlsafe_b64decode(_string_params.encode()).decode())

    def _get_key(self, _endpoint, _method, _params):

        b64params = self._encode_params(_params)
        key = f'{self.key_prefix}:{_endpoint}:{_method}:{b64params}'
        data = self.r.get(key)
        return json.loads(data) if data else {}

    def _set_key(self, _endpoint, _method, _params, _json_data, ttl=None):

        b64params = self._encode_params(_params)
        key = f'{self.key_prefix}:{_endpoint}:{_method}:{b64params}'
        data = json.dumps(_json_data)
        self.r.set(key, data)

        ttl = ttl if ttl else self.ttl
        return self.r.expire(key, ttl)

    def get(self, _endpoint, _method, _params):
        return self._get_key(_endpoint, _method, _params)

    def set(self, _endpoint, _method, _params, _json_data, ttl=None):
        return self._set_key(_endpoint, _method, _params, _json_data, ttl=ttl)
