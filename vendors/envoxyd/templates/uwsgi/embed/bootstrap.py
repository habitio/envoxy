import sys
import os
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
