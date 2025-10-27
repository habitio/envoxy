from .constants import *
from .decorators import *
from .views import *
from .utils import *
from .utils.logs import Log as log
from .utils.watchdog import Watchdog
from .cache import *

from .zeromq.dispatcher import Dispatcher as zmqc
from .db.dispatcher import PgDispatcher as pgsqlc, CouchDBDispatcher as couchdbc, RedisDBDispatcher as redisc
from .auth.backends import authenticate_container as authenticate
from .mqtt.dispatcher import Dispatcher as mqttc
from .views.containers import Response
from .celery.client import Client as celeryc

# Version information
try:
	from importlib.metadata import version, PackageNotFoundError
	__version__ = version("envoxy")
except PackageNotFoundError:
	__version__ = "unknown"

envoxy = locals()


def alembic_config_path() -> str:
	"""Return the absolute path to the bundled alembic.ini inside the envoxy package.

	This helper allows downstream services to discover the framework-provided
	alembic configuration without hard-coding package installation paths.
	"""
	import os

	pkg_dir = os.path.dirname(__file__)
	return os.path.join(pkg_dir, 'tools', 'alembic', 'alembic.ini')
