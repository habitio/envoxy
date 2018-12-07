import re

from typing import Dict, List
from flask import Response as FlaskResponse, Flask, request
from .containers import Response

from ..utils.logs import Log

REGEX_VAR_PATTERN = r'(?P<all>{(?P<var>[^:]+):(?P<type>[^}]+)})'


class View(object):

    __metaclass__ = None

    def __init__(self) -> None:
        self.__flask_app: Flask = None

    def get_methods(self) -> List[str]:
        return [_method for _method in dir(self) if _method in ['get', 'post', 'put', 'patch', 'delete', 'on_event']]

    def set_flask(self, app) -> None:

        self.__flask_app: Flask = app

        _endpoint = getattr(self.__metaclass__, 'endpoint', '')
        _protocols = getattr(self.__metaclass__, 'protocols', [])

        _regex = re.compile(REGEX_VAR_PATTERN)
        
        for _method in self.get_methods():

            if 'http' in _protocols:

                _flask_endpoint = _endpoint

                for _match in _regex.finditer(_endpoint):
                    _groups = _match.groupdict()
                    _flask_endpoint = _flask_endpoint.replace(_groups['all'], '<{}:{}>'.format(_groups['type'], _groups['var']))
            
                self.__flask_app.add_url_rule(
                    _flask_endpoint, 
                    view_func=self._dispatch(_method, 'http'), 
                    methods=[_method]
                )

                Log.system('{} [{}] Added the endpoint "{}" using the method "{}" calling the function "{}"'.format(
                    Log.style.apply('>>>', Log.style.BOLD),
                    Log.style.apply('HTTP', Log.style.GREEN_FG),
                    _endpoint,
                    _method,
                    getattr(self, _method, 'Not Found')
                ))

    def _dispatch(self, _method, _protocol):
        
        def _wrapper(*args, **kwargs):

            kwargs['request'] = request
            
            if _protocol == 'http':
                return getattr(self, _method)(*args, **kwargs)
        
        _wrapper.__name__ = '__wrapper__{}__{}__{}'.format(self.__class__.__name__, _method, _protocol)
        
        return _wrapper
        