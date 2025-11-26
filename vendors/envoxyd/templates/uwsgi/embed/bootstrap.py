import sys
import os
import site

# Add virtual environment site-packages if we're running from a venv
# This ensures envoxy/envoxyd modules are found when binary is in a venv
if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    # We're in a virtual environment
    venv_site_packages = os.path.join(sys.prefix, 'lib', f'python{sys.version_info.major}.{sys.version_info.minor}', 'site-packages')
    if os.path.exists(venv_site_packages) and venv_site_packages not in sys.path:
        sys.path.insert(0, venv_site_packages)
        site.addsitedir(venv_site_packages)

import uwsgi
import envoxy

# Simple bootstrap for dynamic Python linking
# No bundled stdlib needed - uses system Python
print(f"ENVOXY BOOTSTRAP: Using system Python {sys.version}", file=sys.stderr)
print(f"ENVOXY BOOTSTRAP: sys.executable={sys.executable}", file=sys.stderr)

_apply = envoxy.log.style.apply

envoxy.log.system('\n\n')
envoxy.log.system(_apply('======================================', envoxy.log.style.BLUE_FG))
envoxy.log.system(_apply('=== ENVOXY Bootstrap System Loader ===', envoxy.log.style.BLUE_FG))
envoxy.log.system(_apply('======================================', envoxy.log.style.BLUE_FG))
envoxy.log.system('\n\n')
envoxy.log.system(_apply('>>> I am the bootstrap for uwsgi.SymbolsImporter', envoxy.log.style.BOLD))
envoxy.log.system('\n\n')

sys.meta_path.insert(0, uwsgi.SymbolsImporter())
