from datetime import datetime

from flask import Response as FlaskResponse

from ..constants import SERVER_NAME
from ..utils.encoders import envoxy_json_dumps


class Response(FlaskResponse):

    default_mimetype: str = 'application/json'

    def __init__(self, *args, **kwargs):

        _response_headers = dict()
        _response_cookies = []

        if args:

            _arg_zero = args[0]

            # payload is defined in original body
            _payload = _arg_zero.get('payload', _arg_zero) if isinstance(_arg_zero, dict) else _arg_zero

            if isinstance(_arg_zero, dict):
                if 'status' in _arg_zero:
                    # get response status
                    kwargs['status'] = _arg_zero['status']
                if 'headers' in _arg_zero:
                    # headers are defined in original body
                    _response_headers = _arg_zero['headers']
                if 'cookies' in _arg_zero:
                    _response_cookies = _arg_zero['cookies']

            if isinstance(_payload, list):
                args = [envoxy_json_dumps({
                    'elements': _payload,
                    'size': len(_payload)
                })] + list(args[1:])

            elif isinstance(_payload, dict):
                args = [envoxy_json_dumps(_payload)] + list(args[1:])

        super(Response, self).__init__(*args, **kwargs)

        _response_headers.update({
            'Server': SERVER_NAME,
            'Date': datetime.now().isoformat()
        })

        for _header in _response_headers.items():
            self.headers.add_header(*_header)

        for _cookie in _response_cookies:
            self.set_cookie(**_cookie)

    @classmethod
    def force_type(cls, rv, environ=None):

        if isinstance(rv, dict):
            rv = envoxy_json_dumps(rv)

        return super(Response, cls).force_type(rv, environ)
