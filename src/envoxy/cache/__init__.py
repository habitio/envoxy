from ..utils.config import Config
from ..constants import REDIS_BACKEND
from .redis import RedisCache

class Cache:

    def __init__(self):

        config = Config.get('cache')
        backend = config.get('backend')

        if backend == REDIS_BACKEND:
            self._redis = RedisCache(config)


    @property
    def redis(self):
        return self._redis

