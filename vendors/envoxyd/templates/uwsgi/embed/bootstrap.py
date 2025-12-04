import sys
import os
import site

# Debug: Print environment info
print(f"DEBUG: sys.prefix={sys.prefix}", file=sys.stderr)
print(f"DEBUG: sys.base_prefix={getattr(sys, 'base_prefix', 'N/A')}", file=sys.stderr)
print(f"DEBUG: sys.executable={sys.executable}", file=sys.stderr)
print(f"DEBUG: VIRTUAL_ENV={os.environ.get('VIRTUAL_ENV', 'N/A')}", file=sys.stderr)

# Detect venv from environment variable or binary location
venv_path = None

# Method 1: Check VIRTUAL_ENV environment variable
if 'VIRTUAL_ENV' in os.environ:
    venv_path = os.environ['VIRTUAL_ENV']
    print(f"DEBUG: Detected venv from VIRTUAL_ENV: {venv_path}", file=sys.stderr)

# Method 2: Check if running from venv using sys attributes
elif hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    venv_path = sys.prefix
    print(f"DEBUG: Detected venv from sys.prefix: {venv_path}", file=sys.stderr)

# Method 3: Infer from binary location (binary in venv's bin/ or site-packages/)
if not venv_path and sys.executable:
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    if '/bin' in exe_dir or '/site-packages/' in exe_dir:
        parts = exe_dir.split('/')
        for i, part in enumerate(parts):
            if part in ('bin', 'site-packages'):
                venv_path = '/'.join(parts[:i])
                print(f"DEBUG: Inferred venv from executable path: {venv_path}", file=sys.stderr)
                break

# Add venv site-packages to sys.path and call site.addsitedir
if venv_path:
    venv_site_packages = os.path.join(venv_path, 'lib', f'python{sys.version_info.major}.{sys.version_info.minor}', 'site-packages')
    print(f"DEBUG: Looking for site-packages at: {venv_site_packages}", file=sys.stderr)
    print(f"DEBUG: Path exists: {os.path.exists(venv_site_packages)}", file=sys.stderr)
    
    if os.path.exists(venv_site_packages) and venv_site_packages not in sys.path:
        print(f"DEBUG: Adding to sys.path: {venv_site_packages}", file=sys.stderr)
        sys.path.insert(0, venv_site_packages)
        site.addsitedir(venv_site_packages)
    else:
        if venv_site_packages in sys.path:
            print(f"DEBUG: Already in sys.path: {venv_site_packages}", file=sys.stderr)
else:
    print("DEBUG: No venv detected, using system Python", file=sys.stderr)

import uwsgi
import envoxy

# Simple bootstrap for dynamic Python linking
# No bundled stdlib needed - uses system Python
print(f"DEBUG: ENVOXY BOOTSTRAP: Using system Python {sys.version}", file=sys.stderr)
print(f"DEBUG: ENVOXY BOOTSTRAP: sys.executable={sys.executable}", file=sys.stderr)

_apply = envoxy.log.style.apply

envoxy.log.system('\n\n')
envoxy.log.system(_apply('======================================', envoxy.log.style.BLUE_FG))
envoxy.log.system(_apply('=== ENVOXY Bootstrap System Loader ===', envoxy.log.style.BLUE_FG))
envoxy.log.system(_apply('======================================', envoxy.log.style.BLUE_FG))
envoxy.log.system('\n\n')
envoxy.log.system(_apply('>>> I am the bootstrap for uwsgi.SymbolsImporter', envoxy.log.style.BOLD))
envoxy.log.system('\n\n')

# Place SymbolsImporter after default importers to avoid shadowing
# editable installs and standard resolution.
sys.meta_path.append(uwsgi.SymbolsImporter())
