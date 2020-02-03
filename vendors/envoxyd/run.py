import importlib.util
import inspect
import json
import time

import envoxy

from envoxy import zmqc, Response

import uwsgi
from flask import Flask, request, g
from flask_cors import CORS

app = Flask(__name__)
app.response_class = envoxy.Response
app.url_map.converters['str'] = app.url_map.converters['string']


@app.before_request
def before_request():
    g.start = time.time()
    
    if envoxy.log.is_gte_log_level(envoxy.log.INFO):

        _request = '{} [{}] {}'.format(
            envoxy.log.style.apply('> Request', envoxy.log.style.BOLD),
            envoxy.log.style.apply('HTTP', envoxy.log.style.GREEN_FG),
            envoxy.log.style.apply('{} {}'.format(request.method.upper(),
                                                  request.full_path if request.full_path[-1] != '?' else request.path),
                                   envoxy.log.style.BLUE_FG)
        )
        envoxy.log.trace(_request)

        _outputs = [_request]

        if envoxy.log.is_gte_log_level(envoxy.log.VERBOSE):
            _outputs.append(f'Headers:{dict(request.headers)}')

            if request.data:
                _outputs.append(f'Payload{json.dumps(request.get_json(), indent=None)}')

        envoxy.log.verbose(' | '.join(_outputs))
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

        _response = '{} [{}] {} - {}'.format(
            envoxy.log.style.apply('< Response', envoxy.log.style.BOLD),
            envoxy.log.style.apply('HTTP', _status_code_style),
            envoxy.log.style.apply('{} {}'.format(request.method.upper(),
                                                  request.full_path if request.full_path[-1] != '?' else request.path),
                                   envoxy.log.style.BLUE_FG),
            envoxy.log.style.apply(str(response.status_code), _status_code_style)
        )
        envoxy.log.trace(_response)

        _outputs = [_response]

        if envoxy.log.is_gte_log_level(envoxy.log.VERBOSE):

            _outputs.append(f'Headers{dict(response.headers)}')

            if response.data:
                _outputs.append(f'Payload{json.dumps(response.get_json(), indent=None)}')

        envoxy.log.verbose(' | '.join(_outputs))
        del _outputs

    _ts = time.time()
    envoxy.log.verbose('updating last_event_ms {}'.format(_ts))

    uwsgi.opt['last_event_ms'] = _ts

    duration = round(_ts - g.start, 2)

    envoxy.log.verbose(f"Request {request.full_path if request.full_path[-1] != '?' else request.path} took {duration} sec")

    return response


def load_modules(_modules_list):
    _view_classes = []

    for _module_path in _modules_list:

        envoxy.log.system('[{}] Module path: {}\n'.format(
            envoxy.log.style.apply('MMM', envoxy.log.style.BLUE_FG),
            _module_path
        ))

        _spec = importlib.util.spec_from_file_location('__init__', _module_path)
        _module = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_module)

        for _name, _obj in inspect.getmembers(_module):

            if _name == '__loader__' and isinstance(_obj, list) and len(_obj) > 0:
                envoxy.log.system('[{}] Loader: {}\n'.format(
                    envoxy.log.style.apply('...', envoxy.log.style.BLUE_FG),
                    _obj
                ))

                _view_classes.extend(_obj)

    return _view_classes


def load_packages(_package_list):
    _view_classes = []

    for _package in _package_list:

        envoxy.log.system('[{}] Package: {}\n'.format(
            envoxy.log.style.apply('PPP', envoxy.log.style.BLUE_FG),
            _package
        ))

        _obj = importlib.import_module(f'{_package}.loader')

        if hasattr(_obj, '__loader__') and isinstance(_obj.__loader__, list) and len(_obj.__loader__) > 0:
            envoxy.log.system('[{}] Loader: {}\n'.format(
                envoxy.log.style.apply('...', envoxy.log.style.BLUE_FG),
                _obj
            ))

            _view_classes.extend(_obj.__loader__)

    return _view_classes


if 'mode' in uwsgi.opt and uwsgi.opt['mode'] == b'test':

    @app.route('/')
    def index():
        return "ENVOXY Working!"

else:
    # Authentication
    _conf_content = uwsgi.opt.get('conf_content', {})

    _auth_conf = _conf_content.get('credentials')
    _credentials = envoxy.authenticate(_auth_conf)
    uwsgi.opt['credentials'] = _credentials

    # Add plugins to conf
    _plugins = _conf_content.get('plugins')
    uwsgi.opt['plugins'] = _plugins

    # Load project modules and packages
    _modules_list = _conf_content.get('modules', [])
    _package_list = _conf_content.get('packages', [])

    if _modules_list and _package_list:
        envoxy.log.emergency('Defining modules and packages at the same time is not allowed.\n\n')
        exit(-10)

    _view_classes = []

    # Loading modules from path
    _view_classes.extend(load_modules(_modules_list))

    # Loading from installed packages
    _view_classes.extend(load_packages(_package_list))

    _protocols_enabled = []

    for _view_class in _view_classes:
        _instance = _view_class()
        _instance.set_flask(app)

        _protocols_enabled.extend(_instance.protocols)

        uwsgi.log('\n')
        envoxy.log.system('[{}] Loaded "{}".\n'.format(
            envoxy.log.style.apply('###', envoxy.log.style.BLUE_FG),
            str(_view_class)
        ))

    
    _default_zmq_backend = _conf_content.get('default_zmq_backend')

    if _default_zmq_backend and _default_zmq_backend.get('enabled'):

        _path_prefix = _default_zmq_backend.get('path_prefix', '/')

        try:
            
            _server_key = _default_zmq_backend.get('server_key', next(iter(zmqc.instance()._instances.keys())))
            
            @app.route(f'{_path_prefix}<path:path>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD'])
            def default_zmq_backend(path):
                
                _method = request.method.lower()

                _fn = getattr(zmqc, _method, None)

                if _fn:

                    return Response(
                        _fn.__call__(
                            _server_key, 
                            f'{_path_prefix}{path}', 
                            params=request.args if request.args else None,
                            headers=request.headers.items() if request.headers else None,
                            payload=request.get_json() if request.is_json else None
                        )
                    )
                                
                else:

                    envoxy.log.error(f'Method "{request.method}" not found in "{_path_prefix}{path}" URI handler')

            envoxy.log.system('[{}] Default ZMQ Backend enabled pointing to the: "{}"\n    - Listening all endpoints on: {}*\n'.format(
                envoxy.log.style.apply('---', envoxy.log.style.BLUE_FG),
                _server_key,
                _path_prefix
            ))

        except StopIteration as e:

            envoxy.log.error(f'There is no default ZMQ Server Backend enabled for V3 endpoints')


    debug_mode = _conf_content.get('debug', False)
    envoxy.log.system('[{}] App in debug mode {}!\n'.format(
        envoxy.log.style.apply('---', envoxy.log.style.BLUE_FG),
        debug_mode
    ))
    app.debug_mode = debug_mode

    enable_cors = _conf_content.get('enable_cors', False)
    if enable_cors: CORS(app, supports_credentials=True)

uwsgi.log('\n\n')
