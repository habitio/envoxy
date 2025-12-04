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
    # Check if binary is in a venv structure
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    if '/bin' in exe_dir or '/site-packages/' in exe_dir:
        # Go up to find venv root
        parts = exe_dir.split('/')
        for i, part in enumerate(parts):
            if part in ('bin', 'site-packages'):
                venv_path = '/'.join(parts[:i])
                print(f"DEBUG: Inferred venv from executable path: {venv_path}", file=sys.stderr)
                break

# Add venv site-packages to sys.path
if venv_path:
    venv_site_packages = os.path.join(venv_path, 'lib', f'python{sys.version_info.major}.{sys.version_info.minor}', 'site-packages')
    print(f"DEBUG: Looking for site-packages at: {venv_site_packages}", file=sys.stderr)
    print(f"DEBUG: Path exists: {os.path.exists(venv_site_packages)}", file=sys.stderr)
    
    if os.path.exists(venv_site_packages):
        if venv_site_packages not in sys.path:
            print(f"DEBUG: Adding to sys.path: {venv_site_packages}", file=sys.stderr)
            sys.path.insert(0, venv_site_packages)
            
            # Process .pth files synchronously BEFORE site.addsitedir()
            # This ensures editable install finders are registered immediately
            print(f"DEBUG: Pre-processing .pth import statements", file=sys.stderr)
            pth_files = sorted([f for f in os.listdir(venv_site_packages) if f.endswith('.pth')])
            
            exec_count = 0
            for pth_file in pth_files:
                pth_path = os.path.join(venv_site_packages, pth_file)
                try:
                    with open(pth_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            # Only execute import statements (editable install finders)
                            if line and line.startswith(('import ', 'from ')):
                                print(f"DEBUG:   Exec: {pth_file}: {line[:60]}", file=sys.stderr)
                                exec(line)
                                exec_count += 1
                except Exception as e:
                    print(f"DEBUG:   Error in {pth_file}: {e}", file=sys.stderr)
            
            # DIAGNOSTIC: Check for placeholder paths after .pth processing
            print(f"DEBUG: Executed {exec_count} import statements from .pth files", file=sys.stderr)
            print(f"DEBUG: sys.path length after .pth processing: {len(sys.path)}", file=sys.stderr)
            placeholder_paths = [p for p in sys.path if '__path_hook__' in p]
            print(f"DEBUG: Found {len(placeholder_paths)} placeholder paths in sys.path", file=sys.stderr)
            if placeholder_paths:
                print(f"DEBUG: Sample placeholder paths (first 3):", file=sys.stderr)
                for p in placeholder_paths[:3]:
                    print(f"DEBUG:   - {p}", file=sys.stderr)
            
            # Now call site.addsitedir for path entries and other setup
            site.addsitedir(venv_site_packages)
            
            # DIAGNOSTIC: Check if placeholder paths persist after site.addsitedir
            print(f"DEBUG: sys.path length after site.addsitedir: {len(sys.path)}", file=sys.stderr)
            placeholder_after_site = [p for p in sys.path if '__path_hook__' in p]
            print(f"DEBUG: Placeholder paths after site.addsitedir: {len(placeholder_after_site)}", file=sys.stderr)
        else:
            print(f"DEBUG: Already in sys.path: {venv_site_packages}", file=sys.stderr)
else:
    print("DEBUG: No venv detected, using system Python", file=sys.stderr)

import uwsgi
import envoxy

# DIAGNOSTIC: Check placeholder paths after uwsgi/envoxy imports
print(f"DEBUG: sys.path length after uwsgi/envoxy imports: {len(sys.path)}", file=sys.stderr)
placeholder_after_imports = [p for p in sys.path if '__path_hook__' in p]
print(f"DEBUG: Placeholder paths after uwsgi/envoxy imports: {len(placeholder_after_imports)}", file=sys.stderr)
if 'placeholder_after_site' in dir() and len(placeholder_after_imports) < len(placeholder_after_site):
    print(f"DEBUG: WARNING! Lost {len(placeholder_after_site) - len(placeholder_after_imports)} placeholder paths after imports!", file=sys.stderr)

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
