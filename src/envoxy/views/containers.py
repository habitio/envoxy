import json
from datetime import datetime

from ..constants import SERVER_NAME
from ..utils.encoders import EnvoxyJsonEncoder
from flask import Response as FlaskResponse


class Response(FlaskResponse):

    default_mimetype: str = 'application/json'

    def __init__(self, *args, **kwargs):

        response_headers = dict()
        response_cookies = []
        
        if len(args) > 0:

            payload = args[0]['payload'] if 'payload' in args[0] else args[0]  # payload is defined in original body
            if 'status' in args[0]: kwargs['status'] = args[0]['status']  # get response status
            if 'headers' in args[0] : response_headers = args[0]['headers']  # headers are defined in original body
            if 'cookies' in args[0] : response_cookies = args[0]['cookies']
            
            if isinstance(payload, list):
                args = list(args)
                args[0] = json.dumps({
                    'elements': payload,
                    'size': len(payload)
                }, cls=EnvoxyJsonEncoder)
            
            elif isinstance(args[0], dict):
                args = list(args)
                args[0] = json.dumps(payload, cls=EnvoxyJsonEncoder)
        
        super(Response, self).__init__(*args, **kwargs)

        response_headers.update({
            'Server': SERVER_NAME,
            'Date': datetime.now().isoformat()
        })

        list(map((lambda header: self.headers.add_header(header[0], header[1])), response_headers.items()))
        list(self.set_cookie(**cookie) for cookie in response_cookies)

    @classmethod
    def force_type(cls, rv, environ=None):
        
        if isinstance(rv, dict):
            rv = json.dumps(rv, cls=EnvoxyJsonEncoder)
        
        return super(Response, cls).force_type(rv, environ)
