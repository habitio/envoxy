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
        if _site_packages not in sys.path:
            sys.path.insert(0, _site_packages)

        # Process .pth files to register editable install finders
        _pth_count = 0
        _exec_count = 0
        try:
            _pth_files = sorted([f for f in os.listdir(_site_packages) if f.endswith('.pth')])
            for _pth_file in _pth_files:
                _pth_path = os.path.join(_site_packages, _pth_file)
                try:
                    with open(_pth_path, 'r', encoding='utf-8') as _f:
                        _pth_count += 1
                        for _line in _f:
                            _line = _line.strip()
                            if _line and _line.startswith(('import ', 'from ')):
                                try:
                                    exec(_line, globals())
                                    _exec_count += 1
                                except Exception:
                                    pass
                except Exception:
                    pass
        except Exception:
            pass
        
        # FIX: Resolve symlinks in editable finder MAPPING paths
        # Editable installs store absolute paths that may contain symlinks.
        # If the venv was copied/moved or deployment uses symlinks, paths become invalid.
        # We resolve any symlink components in the path to make them work.
        _editable_finders = [f for f in sys.meta_path if isinstance(f, type) and '_EditableFinder' in f.__name__]
        _patched_count = 0
        
        for _finder in _editable_finders:
            try:
                _mod_name = _finder.__module__
                _mod = sys.modules.get(_mod_name)
                if _mod and hasattr(_mod, 'MAPPING'):
                    for _pkg, _path in list(_mod.MAPPING.items()):
                        if not os.path.exists(_path):
                            # Resolve symlinks by checking each path component
                            _path_parts = _path.split(os.sep)
                            _resolved = ''
                            
                            for i, _part in enumerate(_path_parts):
                                if not _part:  # Skip empty parts (leading /)
                                    _resolved = os.sep
                                    continue
                                    
                                _current = os.path.join(_resolved, _part)
                                
                                # If this component is a symlink, resolve it
                                if os.path.islink(_current):
                                    _target = os.readlink(_current)
                                    # Handle absolute vs relative symlink targets
                                    if os.path.isabs(_target):
                                        _resolved = _target
                                    else:
                                        _resolved = os.path.join(os.path.dirname(_current), _target)
                                else:
                                    _resolved = _current
                            
                            # Verify the resolved path exists
                            if _resolved and os.path.exists(_resolved) and _resolved != _path:
                                _mod.MAPPING[_pkg] = _resolved
                                _patched_count += 1
                                print(f"[ENVOXY.__init__] Resolved symlink: {_pkg}: {_path} → {_resolved}", file=sys.stderr)
            except Exception:
                pass
        
        print(f"[ENVOXY.__init__] Processed {_pth_count} .pth files, executed {_exec_count} import statements", file=sys.stderr)
        print(f"[ENVOXY.__init__] Editable finder CLASSES in sys.meta_path: {len(_editable_finders)}", file=sys.stderr)
        if _patched_count > 0:
            print(f"[ENVOXY.__init__] Resolved {_patched_count} symlinked editable install paths", file=sys.stderr)

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
