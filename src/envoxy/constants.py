import enum

# HTTP methods
GET = 'get'
POST = 'post'
PUT = 'put'
PATCH = 'patch'
DELETE = 'delete'

SERVER_NAME = 'Envoxy Server'

ZEROMQ_POLLIN_TIMEOUT = 5 * 1000
ZEROMQ_REQUEST_RETRIES = 5
ZEROMQ_CONTEXT = 1

class Performative(enum.IntEnum):
    GET = 0
    PUT = 1
    POST = 2
    DELETE = 3
    HEAD = 4
    OPTIONS = 5
    PATCH = 6
    REPLY = 7
    SEARCH = 8
    NOTIFY = 9
    TRACE = 10
    CONNECT = 11

# DB
MIN_CONN = 1
MAX_CONN = 1

# CACHE
CACHE_DEFAULT_TTL = 60 * 60 # ttl in seconds (1hr)

# REDIS
REDIS_BACKEND = 'redis'
REDIS_DEFAULT_DB = 1
REDIS_DEFAULT_TTL = CACHE_DEFAULT_TTL
REDIS_DEFAULT_HOST = '127.0.0.1'
REDIS_DEFAULT_PORT = '6379'

