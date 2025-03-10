import re
import uuid
import traceback

from typing import List

from flask import Flask, request, Response as FlaskResponse, make_response, jsonify

from .containers import Response
from ..exceptions import ValidationException
from ..utils.logs import Log

from ..mqtt.dispatcher import Dispatcher as mqttc

REGEX_VAR_PATTERN: str = r'(?P<all>{(?P<var>[^:]+):(?P<type>[^}]+)})'
COMPILED_REGEX = re.compile(REGEX_VAR_PATTERN)


class View(object):

    __metaclass__ = None

    def __init__(self) -> None:
        self.__flask_app: Flask = None
        self.protocols = []

    def get_methods(self) -> List[str]:
        return [_method for _method in dir(self) if _method in ['get', 'post', 'put', 'patch', 'delete', 'on_event']]

    def set_flask(self, app) -> None:

        self.__flask_app: Flask = app

        _endpoint = getattr(self.__metaclass__, 'endpoint', '')
        _protocols = getattr(self.__metaclass__, 'protocols', [])
        _server = getattr(self.__metaclass__, 'server', '')

        for _method in self.get_methods():

            _method_attr = getattr(self, _method, 'Not Found')

            if 'http' in _protocols:

                if 'http' not in self.protocols:
                    self.protocols.append('http')

                _flask_endpoint = _endpoint

                for _match in COMPILED_REGEX.finditer(_endpoint):
                    _groups = _match.groupdict()
                    _flask_endpoint = _flask_endpoint.replace(
                        _groups['all'], '<{}:{}>'.format(_groups['type'], _groups['var']))

                self.__flask_app.add_url_rule(
                    _flask_endpoint,
                    view_func=self._dispatch(_method, _endpoint, 'http'),
                    methods=[_method]
                )

                Log.system('{} [{}] Added the endpoint "{}" using the method "{}" calling the function "{}"'.format(
                    Log.style.apply('>>>', Log.style.BOLD),
                    Log.style.apply('HTTP', Log.style.GREEN_FG),
                    _endpoint,
                    _method,
                    _method_attr
                ))

            if 'mqtt' in _protocols and _method == "on_event":

                if 'mqtt' not in self.protocols:
                    self.protocols.append('mqtt')

                Log.system('{} [{}] Subscribing to topic "{}" calling the function "{}"'.format(
                    Log.style.apply('>>>', Log.style.BOLD),
                    Log.style.apply('MQTT', Log.style.GREEN_FG),
                    _endpoint,
                    _method
                ))

                mqttc.subscribe(_server, _endpoint, _method_attr)

    def _dispatch(self, _method, _endpoint, _protocol):

        def _wrapper(*args, **kwargs):
            if _protocol == 'http':
                return self.dispatch(request, _method, _endpoint, *args, **kwargs)

        _wrapper.__name__ = '__wrapper__{}__{}__{}'.format(
            self.__class__.__name__, _method, _protocol)

        return _wrapper

    def dispatch(self, request, _method, _endpoint, *args, **kwargs):

        kwargs.update({'endpoint': _endpoint})

        try:
            return getattr(self, _method)(request, *args, **kwargs)
        except Exception as e:

            _code = 0
            _status = 500
            _error_log_ref = str(uuid.uuid4())

            if isinstance(e, ValidationException):

                if 'code' in e.kwargs:
                    _code = e.kwargs['code']

                if 'status' in e.kwargs:
                    _status = e.kwargs['status']

            if request.is_json:

                _resp = make_response(
                    jsonify({"error": f"{e} :: ELRC({_error_log_ref})", "code": _code}), _status)
                _resp.headers['X-Error'] = _code

                if _status not in [204, '204']:
                    Log.error(
                        f"ELRC({_error_log_ref}) - Traceback: {traceback.format_exc()}")
                else:
                    _resp.headers['X-Error-Msg'] = str(e)

                return _resp

            _headers = {
                "X-Error": _code
            }

            if _status not in [204, '204']:
                Log.error(
                    f"ELRC({_error_log_ref}) - Traceback: {traceback.format_exc()}")
            else:
                _headers['X-Error-Msg'] = str(e)  # For 204 there is no payload

            return FlaskResponse(str(f"error: {e} :: ELRC({_error_log_ref})"), _status, headers=_headers)

    def cached_response(self, result):
        return Response(result)
