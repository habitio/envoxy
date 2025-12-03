import importlib.util
import inspect
import json
import time
import os
import traceback

import envoxy

from envoxy import zmqc, mqttc, celeryc, Response

import uwsgi
from flask import Flask, request, g
from flask_cors import CORS
from envoxy.db.orm.listeners import register_envoxy_listeners


def _import_with_retry(module_name, retries=3, delay=0.1):
    """Import a module with retry logic for editable install timing issues.
    
    Args:
        module_name: Full module name to import (e.g., 'applications.loader')
        retries: Number of retry attempts
        delay: Delay in seconds between retries
        
    Returns:
        Imported module object
        
    Raises:
        ModuleNotFoundError: If module cannot be imported after all retries
    """
    for attempt in range(retries):
        try:
            return importlib.import_module(module_name)
        except ModuleNotFoundError as e:
            if attempt < retries - 1:
                envoxy.log.system(f'[RETRY] Import failed for {module_name}, retrying in {delay}s (attempt {attempt + 1}/{retries})\n')
                time.sleep(delay)
            else:
                raise


def load_modules(_modules_list):
    _view_classes = []

    for _module_path in _modules_list:

        envoxy.log.system('[{}] Module path: {}\n'.format(
            envoxy.log.style.apply('MMM', envoxy.log.style.BLUE_FG),
            _module_path
        ))

        _spec = importlib.util.spec_from_file_location(
            '__init__', _module_path)
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

        # Use retry mechanism for editable install timing issues
        _obj = _import_with_retry(f'{_package}.loader')

        if hasattr(_obj, '__loader__') and isinstance(_obj.__loader__, list) and len(_obj.__loader__) > 0:
            envoxy.log.system('[{}] Loader: {}\n'.format(
                envoxy.log.style.apply('...', envoxy.log.style.BLUE_FG),
                _obj
            ))

            _view_classes.extend(_obj.__loader__)

    return _view_classes


class AppContext(object):

    _app = None

    def __init__(self):
        raise Exception('call instance()')

    @classmethod
    def app(cls):

        if cls._app is None:

            cls._app = Flask(__name__)
            cls._app.response_class = envoxy.Response
            cls._app.url_map.converters['str'] = cls._app.url_map.converters['string']

            # Internal health check endpoint for systemd watchdog
            # This endpoint is registered before user routes and won't interfere
            @cls._app.route('/_health')
            def _internal_health():
                """Internal health check endpoint for systemd watchdog.
                
                Returns 200 OK with a simple JSON response indicating the service is healthy.
                This endpoint is automatically registered by the framework and should not be
                used by external clients - it's specifically for watchdog health checks.
                """
                return Response({"status": "healthy", "service": "envoxy"}, status=200, mimetype='application/json')

            if 'mode' in uwsgi.opt and uwsgi.opt['mode'] == b'test':

                @cls._app.route('/')
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

                if _conf_content.get('amqp_servers'):

                    # Start the AMQP app in the main thread
                    celeryc.initialize()

                # Load project modules and packages
                _modules_list = _conf_content.get('modules', [])
                _package_list = _conf_content.get('packages', [])

                if _modules_list and _package_list:
                    envoxy.log.emergency(
                        'Defining modules and packages at the same time is not allowed.\n\n')
                    exit(-10)

                _view_classes = []

                # Register ORM listeners before importing/loading modules so
                # mapper_configured events fire for each model as it's mapped.
                # This enforces EnvoxyBase inheritance and attaches id/ts listeners.
                register_envoxy_listeners()

                # Loading modules from path
                _view_classes.extend(load_modules(_modules_list))

                # Loading from installed packages
                _view_classes.extend(load_packages(_package_list))

                _protocols_enabled = []

                for _view_class in _view_classes:
                    _instance = _view_class()
                    _instance.set_flask(cls._app)

                    _protocols_enabled.extend(_instance.protocols)

                    uwsgi.log('\n')
                    envoxy.log.system('[{}] Loaded "{}".\n'.format(
                        envoxy.log.style.apply(
                            '###', envoxy.log.style.BLUE_FG),
                        str(_view_class)
                    ))

                if _conf_content.get('zmq_servers'):

                    # Start the ZMQ dispatcher in the main thread
                    zmqc.initialize()

                if _conf_content.get('mqtt_servers'):

                    # Start the MQTT dispatcher in the main thread
                    mqttc.initialize()

                _default_zmq_backend = _conf_content.get('default_zmq_backend')

                if _default_zmq_backend and _default_zmq_backend.get('enabled'):

                    _path_prefix = _default_zmq_backend.get('path_prefix', '/')

                    try:

                        _server_key = _default_zmq_backend.get(
                            'server_key', next(iter(zmqc.instance()._instances.keys())))

                        @cls._app.route(f'{_path_prefix}<path:path>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD'])
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

                                envoxy.log.error(
                                    f'Method "{request.method}" not found in "{_path_prefix}{path}" URI handler')

                        envoxy.log.system('[{}] Default ZMQ Backend enabled pointing to the: "{}"\n    - Listening all endpoints on: {}*\n'.format(
                            envoxy.log.style.apply(
                                '---', envoxy.log.style.BLUE_FG),
                            _server_key,
                            _path_prefix
                        ))

                    except StopIteration:

                        envoxy.log.error(
                            'There is no default ZMQ Server Backend enabled for V3 endpoints')

                debug_mode = _conf_content.get('debug', False)
                envoxy.log.system('[{}] App in debug mode {}!\n'.format(
                    envoxy.log.style.apply('---', envoxy.log.style.BLUE_FG),
                    debug_mode
                ))
                cls._app.debug_mode = debug_mode

                enable_cors = _conf_content.get('enable_cors', False)
                if enable_cors:
                    CORS(cls._app, supports_credentials=True)

                uwsgi.log('\n\n')

                # Fallback: if systemd watchdog expects notifications from the
                # master process (WATCHDOG_PID == this pid), ensure we start
                # a watchdog here so systemd receives WATCHDOG=1 from the
                # correct PID. This is a safe, reversible safeguard in case
                # the uwsgi embed hook didn't execute in the expected process.
                try:
                    _keep = int(_conf_content.get('keep_alive', 0))
                except Exception:
                    _keep = 0

                try:
                    wd_pid_env = os.environ.get('WATCHDOG_PID')
                    allowed_to_start = False

                    if _keep and _keep > 0:
                        if wd_pid_env:
                            try:
                                allowed_to_start = int(wd_pid_env) == os.getpid()
                            except Exception:
                                allowed_to_start = False
                        else:
                            # If WATCHDOG_PID not set, attempt to only start in
                            # the uwsgi master process (best-effort).
                            try:
                                allowed_to_start = hasattr(uwsgi, 'masterpid') and uwsgi.masterpid() == os.getpid()
                            except Exception:
                                allowed_to_start = False

                    if allowed_to_start:
                        try:
                            envoxy.Watchdog(int(_keep)).start()
                            envoxy.log.system('[{}] Watchdog started from bootstrap (master)'.format(
                                envoxy.log.style.apply('---', envoxy.log.style.GREEN_FG)
                            ))
                        except Exception:
                            envoxy.log.warning('[{}] failed to start watchdog from bootstrap: {}'.format(
                                envoxy.log.style.apply('Watchdog', envoxy.log.style.YELLOW_FG), traceback.format_exc(limit=2)
                            ))
                except Exception:
                    # Don't let any bootstrap watchdog logic break app startup
                    envoxy.log.warning('[{}] bootstrap watchdog guard failed: {}'.format(
                        envoxy.log.style.apply('Watchdog', envoxy.log.style.YELLOW_FG), traceback.format_exc(limit=2)
                    ))

        return cls._app


app = AppContext.app()


@app.before_request
def before_request():

    if envoxy.log.is_gte_log_level(envoxy.log.VERBOSE):
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
                _outputs.append(
                    f'Payload{json.dumps(request.get_json(), indent=None)}')

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
            envoxy.log.style.apply(
                str(response.status_code), _status_code_style)
        )
        envoxy.log.trace(_response)

        _outputs = [_response]

        if envoxy.log.is_gte_log_level(envoxy.log.VERBOSE):

            _outputs.append(f'Headers{dict(response.headers)}')

            if response.data:
                _outputs.append(
                    f'Payload{json.dumps(response.get_json(), indent=None)}')

        envoxy.log.verbose(' | '.join(_outputs))

        del _outputs

    # Last event used for watchdog
    _ts = time.time()
    uwsgi.opt['last_event_ms'] = _ts

    if envoxy.log.is_gte_log_level(envoxy.log.VERBOSE):

        envoxy.log.verbose('updating last_event_ms {}'.format(_ts))

        _duration = round(_ts - g.start, 2)

        envoxy.log.verbose(
            f"Request {request.full_path if request.full_path[-1] != '?' else request.path} took {_duration} sec")

    return response
