from ..utils.config import Config
from ..constants import REDIS_BACKEND
from .redis import RedisCache

class Cache:

    def __init__(self):

        config = Config.get('cache')
        self.backend = config.get('backend')

        if self.backend == REDIS_BACKEND:
            self._redis = RedisCache(config)


    @property
    def redis(self):
        return self._redis


    def get_backend(self):
        if self.backend == REDIS_BACKEND:
            return self.redis

        raise NotImplementedError

