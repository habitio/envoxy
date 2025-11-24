import sys
import os
import uwsgi

# Configure Python to use bundled stdlib instead of system paths
# The binary is at: {prefix}/bin/envoxyd
# The stdlib is at: {prefix}/lib/python3.12/site-packages/envoxyd/lib/python3.12
binary_dir = os.path.dirname(sys.executable)
prefix = os.path.dirname(binary_dir)
bundled_stdlib = os.path.join(prefix, 'lib', 'python3.12', 'site-packages', 'envoxyd', 'lib', 'python3.12')

if os.path.isdir(bundled_stdlib):
    # Clear system paths and use only our bundled stdlib
    sys.path = [
        bundled_stdlib,
        os.path.join(bundled_stdlib, 'lib-dynload'),
        os.path.join(prefix, 'lib', 'python3.12', 'site-packages'),
    ]
    print(f"ENVOXY: Using bundled Python stdlib from {bundled_stdlib}", file=sys.stderr)
else:
    print(f"ENVOXY: WARNING - Bundled stdlib not found at {bundled_stdlib}, using system paths", file=sys.stderr)

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
