import json
import os

import envoxy
import uwsgi

if 'conf' in uwsgi.opt:

    _conf_path = uwsgi.opt['conf'].decode('utf-8')

    envoxy.log.system('[{}] Configuration file param found: {}\n'.format(
        envoxy.log.style.apply('OK', envoxy.log.style.GREEN_FG),
        _conf_path
    ))

    if os.path.exists(_conf_path) and os.path.isfile(_conf_path):

        envoxy.log.system('[{}] Configuration file exists! Trying to parse the file...\n'.format(
            envoxy.log.style.apply('---', envoxy.log.style.BLUE_FG)
        ))

        _module_name = os.path.basename(_conf_path).replace('.json', '')

        # try:
        _conf_file = open(_conf_path, encoding='utf-8')
        _conf_content = json.loads(_conf_file.read(), encoding='utf-8')
        envoxy.log.system('[{}] The configuration file was parsed successfully!\n\n'.format(
            envoxy.log.style.apply('OK', envoxy.log.style.GREEN_FG)
        ))

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
