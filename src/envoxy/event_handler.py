from typing import Dict
from flask import Response


class EventHandler(object):

    def __init__(self, _flask_app) -> None:
        self.__flask_app = _flask_app
        self.__methods = getattr(self.Meta, 'methods', [])
        self.__protocols = getattr(self.Meta, 'protocols', [])
        self.__endpoint = getattr(self.Meta, 'endpoint', '')

            
        if 'http' in self.__protocols:

            for _method in self.__methods:
            
                self.__flask_app.add_url_rule(
                    self.__endpoint, 
                    view_func=getattr(self, _method, EventHandler.not_implemented), 
                    methods=[_method]
                )

                print('>>> Added the endpoint "{}" using the method "{}" calling the function "{}"'.format(self.__endpoint, _method, getattr(self, _method, 'Not Found')))

    class Meta:
        protocols = []

    @staticmethod
    def not_implemented():
        return Response('{"text":"Not implemented yet."}', 503, {'Content-Type': 'application/json'})
        
        