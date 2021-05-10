import enum

# HTTP methods
GET = 'get'
POST = 'post'
PUT = 'put'
PATCH = 'patch'
DELETE = 'delete'

SERVER_NAME = 'Envoxy Server'

ZEROMQ_POLLIN_TIMEOUT = 5 * 1000
ZEROMQ_RETRY_TIMEOUT = 2
ZEROMQ_POLLER_RETRIES = 5
ZEROMQ_CONTEXT = 1
ZEROMQ_MAX_WORKERS = 50

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
TIMEOUT_CONN = 5  # 5 seconds
DEFAULT_CHUNK_SIZE = 10000
DEFAULT_OFFSET_LIMIT = 0

# CACHE
CACHE_DEFAULT_TTL = 60 * 60 # ttl in seconds (1hr)

# REDIS
REDIS_BACKEND = 'redis'
REDIS_DEFAULT_DB = 1
REDIS_DEFAULT_TTL = CACHE_DEFAULT_TTL
REDIS_DEFAULT_HOST = '127.0.0.1'
REDIS_DEFAULT_PORT = '6379'

# ASSERTS

HASH_LENGTH = 45
HASH_CHARSET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
HASH_REGEX: str = r"[a-zA-Z0-9]{45}"

TOKEN_LENGHT = 128
TOKEN_CHARSET = "abcdefghijklmnopqrstuvwxyz0123456789"
TOKEN_REGEX: str = r"[a-z0-9]{128}"

URL_REGEX: str = r"([@>]{0,1})([a-zA-Z][a-zA-Z0-9+.-]+):" \
            "([^?#]*)" \
            "(?:\\?([^#]*))?" \
            "(?:#(.*))?"

URI_REGEX: str = r"([^?#]*)(?:\\?([^#]*))?(?:#(.*))?"

EMAIL_REGEX: str = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"

PHONE_REGEX: str = r"(?:\\(([0-9]){1,3}\\)([ ]*))?([0-9]){3,12}"
