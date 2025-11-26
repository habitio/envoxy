import json
import os
import sys
import site

# Detect venv and add site-packages (same logic as bootstrap.py)
venv_path = os.environ.get('VIRTUAL_ENV') or \
            (sys.prefix if hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix else None)

if venv_path:
    site_packages = os.path.join(venv_path, f'lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages')
    if os.path.exists(site_packages) and site_packages not in sys.path:
        sys.path.insert(0, site_packages)
        site.addsitedir(site_packages)

import uwsgi
import envoxy

if 'conf' in uwsgi.opt:

    _conf_path = uwsgi.opt['conf'].decode('utf-8')

    envoxy.log.system(f"[{envoxy.log.style.apply('OK', envoxy.log.style.GREEN_FG)}] Configuration file param found: {_conf_path}\n")

    if os.path.exists(_conf_path) and os.path.isfile(_conf_path):

        envoxy.log.system("[{envoxy.log.style.apply('---', envoxy.log.style.BLUE_FG)}] Configuration file exists! Trying to parse the file...\n")

        _module_name = os.path.basename(_conf_path).replace('.json', '')

        with open(_conf_path, encoding='utf-8') as _conf_file:
            _conf_content = json.loads(_conf_file.read())
        
        envoxy.log.system(f"[{envoxy.log.style.apply('OK', envoxy.log.style.GREEN_FG)}] The configuration file was parsed successfully!\n\n")

        uwsgi.opt['conf_content'] = _conf_content

        _log_conf = _conf_content.get('log') or _conf_content.get('$log')

        if _log_conf and _log_conf.get('level'):
            uwsgi.opt['log-level'] = bytes([int(_log_conf['level'])])

        if _log_conf and _log_conf.get('format'):
            uwsgi.opt['log-format'] = _log_conf['format']

    else:

        envoxy.log.emergency(
            'Configuration file not found in this path! Please check if the file exists or the permissions are enough.\n\n')
        exit(-10)

elif 'mode' not in uwsgi.opt:
    envoxy.log.emergency(
        'Configuration file not found! Please use ./envoxy [params] --set conf=<file> or ./envoxy [params] --set mode=test\n\n')
    exit(-10)
