from typing import Dict, List
from flask import Response as FlaskResponse, Flask
from .containers import Response


class View(object):

    class Meta:
        endpoint: str = None
        protocols: List[str] = []

    def __init__(self) -> None:
        self.__flask_app: Flask = None

    def get_methods(self) -> List[str]:
        return [_method for _method in dir(self) if _method in ['get', 'post', 'put', 'patch', 'delete', 'on_event']]

    def set_flask(self, _app) -> None:

        self.__flask_app: Flask = _app
        
        for _method in self.get_methods():

            if 'http' in getattr(self.Meta, 'protocols', []):
            
                self.__flask_app.add_url_rule(
                    getattr(self.Meta, 'endpoint', ''), 
                    view_func=self._dispatch(_method, 'http'), 
                    methods=[_method]
                )

                print('>>> [HTTP] Added the endpoint "{}" using the method "{}" calling the function "{}"'.format(
                    getattr(self.Meta, 'endpoint', ''), 
                    _method, 
                    getattr(self, _method, 'Not Found')
                ))

    def _dispatch(self, _method, _protocol):
        
        def _wrapper(*args, **kwargs):
            
            if _protocol == 'http':
                return getattr(self, _method)(*args, **kwargs)
        
        _wrapper.__name__ = '_wrapper__{}__{}'.format(_method, _protocol)
        
        return _wrapper
        