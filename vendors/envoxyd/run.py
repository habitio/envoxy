import sys
import os
import json
import uwsgi
import inspect

import importlib.util

from flask import Flask, request


import envoxy

app = Flask(__name__)
app.response_class = envoxy.Response
app.url_map.converters['str'] = app.url_map.converters['string']


@app.before_request
def before_request():

    if envoxy.log.is_gte_log_level(envoxy.log.INFO):

        _outputs = ['{} [{}] {}'.format(
            envoxy.log.style.apply('> Request', envoxy.log.style.BOLD),
            envoxy.log.style.apply('HTTP', envoxy.log.style.GREEN_FG),
            envoxy.log.style.apply('{} {}'.format(request.method.upper(), request.full_path if request.full_path[-1] != '?' else request.path), envoxy.log.style.BLUE_FG)
        )]

        if envoxy.log.is_gte_log_level(envoxy.log.VERBOSE):

            _outputs.append(str(request.headers))

            if request.data:
                _outputs.append(json.dumps(request.get_json(), sort_keys=True, indent=4))

        envoxy.log.info('\n'.join(_outputs))
        del _outputs

@app.after_request
def after_request(response):

    if envoxy.log.is_gte_log_level(envoxy.log.INFO):

        if response.status_code >= 100 and response.status_code <= 299:
            _status_code_style = envoxy.log.style.GREEN_FG
        elif response.status_code >= 300 and response.status_code <= 399:
            _status_code_style = envoxy.log.style.YELLOW_FG
        else:
            _status_code_style = envoxy.log.style.RED_FG

        _outputs = ['{} [{}] {} - {}'.format(
            envoxy.log.style.apply('< Response', envoxy.log.style.BOLD),
            envoxy.log.style.apply('HTTP', _status_code_style),
            envoxy.log.style.apply('{} {}'.format(request.method.upper(), request.full_path if request.full_path[-1] != '?' else request.path), envoxy.log.style.BLUE_FG),
            envoxy.log.style.apply(str(response.status_code), _status_code_style)
        )]

        if envoxy.log.is_gte_log_level(envoxy.log.VERBOSE):

            _outputs.append(str(response.headers))

            if response.data:
                _outputs.append(json.dumps(response.get_json(), sort_keys=True, indent=4))

        envoxy.log.info('\n'.join(_outputs))
        del _outputs

    return response

if 'mode' in uwsgi.opt and uwsgi.opt['mode'] == b'test':

    @app.route('/')
    def index():
        return "ENVOXY Working!"

elif 'conf' in uwsgi.opt:

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

        # Authentication

        _auth_conf = _conf_content.get('credentials')
        _credentials = envoxy.authenticate(_auth_conf)
        uwsgi.opt['credentials'] = _credentials

        # Add plugins to conf
        _plugins = _conf_content.get('plugins')
        uwsgi.opt['plugins'] = _plugins

        # Load project modules

        _modules_list = _conf_content.get('modules')

        for _module_path in _modules_list:

            envoxy.log.system('[{}] Module path: {}\n'.format(
                envoxy.log.style.apply('MMM', envoxy.log.style.BLUE_FG),
                _module_path
            ))

            #try:

            _spec = importlib.util.spec_from_file_location('__init__', _module_path)
            _module = importlib.util.module_from_spec(_spec)
            _spec.loader.exec_module(_module)

            for _name, _obj in inspect.getmembers(_module):

                if _name == '__loader__' and isinstance(_obj, list) and len(_obj)>0:

                    envoxy.log.system('[{}] Loader: {}\n'.format(
                        envoxy.log.style.apply('...', envoxy.log.style.BLUE_FG),
                        _obj
                    ))

                    for _view_class in _obj:
                        _instance = _view_class()
                        _instance.set_flask(app)
                        uwsgi.log('\n')
                        envoxy.log.system('[{}] Loaded "{}".\n'.format(
                            envoxy.log.style.apply('###', envoxy.log.style.BLUE_FG),
                            str(_view_class)
                        ))

        debug_mode = _conf_content.get('debug', False)

        envoxy.log.system('[{}] App in debug mode {}!\n'.format(
            envoxy.log.style.apply('---', envoxy.log.style.BLUE_FG),
            debug_mode
        ))

        app.debug_mode = debug_mode

    else:

        envoxy.log.emergency('Configuration file not found in this path! Please check if the file exists or the permissions are enough.\n\n')
        exit(-10)

else:
    envoxy.log.emergency('Configuration file not found! Please use ./envoxy [params] --set conf=<file> or ./envoxy [params] --set mode=test\n\n')
    exit(-10)

uwsgi.log('\n\n')
