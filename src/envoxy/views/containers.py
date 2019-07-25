import json
from datetime import datetime

from ..constants import SERVER_NAME
from ..utils.encoders import EnvoxyJsonEncoder
from flask import Response as FlaskResponse


class Response(FlaskResponse):

    default_mimetype: str = 'application/json'

    def __init__(self, *args, **kwargs):
        
        if len(args) > 0:
            
            if isinstance(args[0], list):
                args = list(args)
                args[0] = json.dumps({
                    'elements': args[0],
                    'size': len(args[0])
                }, cls=EnvoxyJsonEncoder)
            
            elif isinstance(args[0], dict):
                args = list(args)
                args[0] = json.dumps(args[0], cls=EnvoxyJsonEncoder)
        
        super(Response, self).__init__(*args, **kwargs)

        self.headers.add_header('Server', SERVER_NAME)
        self.headers.add_header('Date', datetime.now().isoformat())

    @classmethod
    def force_type(cls, rv, environ=None):
        
        if isinstance(rv, dict):
            rv = json.dumps(rv, cls=EnvoxyJsonEncoder)
        
        return super(Response, cls).force_type(rv, environ)
