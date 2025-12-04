# ruff: noqa: F403,F401,F405

# CRITICAL: Process .pth files for editable installs BEFORE any other imports
# This must run in each worker process (after fork), not just in the master
import sys
import os

_venv_path = os.environ.get('VIRTUAL_ENV')
if _venv_path:
    _site_packages = os.path.join(
        _venv_path,
        'lib',
        f'python{sys.version_info.major}.{sys.version_info.minor}',
        'site-packages',
    )
    if os.path.exists(_site_packages):
        # Ensure site-packages is present in THIS interpreter
        if _site_packages not in sys.path:
            sys.path.insert(0, _site_packages)

        # Process .pth files to register editable install finders
        try:
            _pth_files = sorted([f for f in os.listdir(_site_packages) if f.endswith('.pth')])
            for _pth_file in _pth_files:
                _pth_path = os.path.join(_site_packages, _pth_file)
                try:
                    with open(_pth_path, 'r', encoding='utf-8') as _f:
                        for _line in _f:
                            _line = _line.strip()
                            if _line and _line.startswith(('import ', 'from ')):
                                try:
                                    exec(_line)
                                except Exception:
                                    # Silently skip errors to keep init resilient
                                    pass
                except Exception:
                    # Skip unreadable .pth files
                    pass
        except Exception:
            # Defensive: never break import due to .pth processing
            pass

from .constants import *
from .decorators import *
from .views import *
from .utils import *
from .utils.logs import Log as log
from .utils.watchdog import Watchdog
from .cache import *

from .zeromq.dispatcher import Dispatcher as zmqc
from .db.dispatcher import (
    PgDispatcher as pgsqlc,
    CouchDBDispatcher as couchdbc,
    RedisDBDispatcher as redisc,
)
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
    return os.path.join(pkg_dir, "tools", "alembic", "alembic.ini")
