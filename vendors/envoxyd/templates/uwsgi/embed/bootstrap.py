import sys
import os

# CRITICAL: Override sys.path BEFORE any other imports to prevent loading from system stdlib
# This must happen before 'import uwsgi' because that triggers site module processing
print(f"ENVOXY BOOTSTRAP: Starting, sys.executable={sys.executable}", file=sys.stderr)
print(f"ENVOXY BOOTSTRAP: Initial sys.path={sys.path[:3] if len(sys.path) >= 3 else sys.path}", file=sys.stderr)

# Calculate paths
binary_dir = os.path.dirname(sys.executable)
prefix = os.path.dirname(binary_dir)
bundled_stdlib = os.path.join(prefix, 'lib', 'python3.12', 'site-packages', 'envoxyd', 'lib', 'python3.12')

print(f"ENVOXY BOOTSTRAP: Looking for bundled stdlib at: {bundled_stdlib}", file=sys.stderr)
print(f"ENVOXY BOOTSTRAP: Directory exists: {os.path.isdir(bundled_stdlib)}", file=sys.stderr)

if os.path.isdir(bundled_stdlib):
    # Ensure bundled stdlib is FIRST in sys.path
    # early-python-path already added it, but let's verify it takes precedence
    bundled_paths = [
        bundled_stdlib,
        os.path.join(bundled_stdlib, 'lib-dynload'),
    ]
    
    # Remove any existing references to bundled paths to avoid duplicates
    sys.path = [p for p in sys.path if p not in bundled_paths]
    
    # PREPEND bundled stdlib (must be BEFORE any system paths)
    sys.path = bundled_paths + sys.path
    
    print(f"ENVOXY: Using bundled Python stdlib from {bundled_stdlib}", file=sys.stderr)
    print(f"ENVOXY: Bundled stdlib takes precedence over system stdlib", file=sys.stderr)
    print(f"ENVOXY: sys.path[0:3]={sys.path[0:3]}", file=sys.stderr)
else:
    print(f"ENVOXY: WARNING - Bundled stdlib not found at {bundled_stdlib}, using system paths", file=sys.stderr)
    if os.path.isdir(prefix):
        print(f"ENVOXY: Contents of {prefix}: {os.listdir(prefix)[:10]}", file=sys.stderr)
        lib_dir = os.path.join(prefix, 'lib')
        if os.path.isdir(lib_dir):
            print(f"ENVOXY: Contents of {lib_dir}: {os.listdir(lib_dir)[:10]}", file=sys.stderr)

# NOW import uwsgi after sys.path is fixed
import uwsgi

import envoxy

_apply = envoxy.log.style.apply

envoxy.log.system('\n\n')
envoxy.log.system(_apply('======================================', envoxy.log.style.BLUE_FG))
envoxy.log.system(_apply('=== ENVOXY Bootstrap System Loader ===', envoxy.log.style.BLUE_FG))
envoxy.log.system(_apply('======================================', envoxy.log.style.BLUE_FG))
envoxy.log.system('\n\n')
envoxy.log.system(_apply('>>> I am the bootstrap for uwsgi.SymbolsImporter', envoxy.log.style.BOLD))
envoxy.log.system('\n\n')

sys.meta_path.insert(0, uwsgi.SymbolsImporter())
