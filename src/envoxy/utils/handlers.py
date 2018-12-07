import json

from requests import Response as RequestsResponse
from flask import Response as FlaskResponse


class Handler:

    @staticmethod
    def response(response: RequestsResponse) -> FlaskResponse:
        try:
            return FlaskResponse(response.text, response.status_code, headers=response.headers.items())
        except Exception as e:
            return FlaskResponse({'text': e}, 500)

    @staticmethod
    def make_response(object_, status) -> FlaskResponse:
        
        if type(object_) in [dict, list]:
            return FlaskResponse(json.dumps(object_), status, {'Content-Type': 'application/json'})
        elif type(object_) in [str]:
            return FlaskResponse(object_, status, {'Content-Type': 'text/html'})
        else:
            return FlaskResponse(json.dumps({'text':'Error in parsing the response object.'}), 500, {'Content-Type': 'text/html'})

    @staticmethod
    def freeze(object_):
        
        if isinstance(object_, dict):
            return frozenset((key, Handler.freeze(value)) for key, value in object_.items())
        elif isinstance(object_, list):
            return tuple(Handler.freeze(value) for value in object_)

        return object_