import json

from requests import Response as RequestsResponse
from flask import Response as FlaskResponse

class Utils:

    @staticmethod
    def make_response(_object, _status) -> FlaskResponse:
        
        if type(_object) in [dict, list]:
            return FlaskResponse(json.dumps(_object), _status, {'Content-Type': 'application/json'})
        elif type(_object) in [str]:
            return FlaskResponse(_object, _status, {'Content-Type': 'text/html'})
        else:
            return FlaskResponse(json.dumps({'text':'Error in parsing the response object.'}), 500, {'Content-Type': 'text/html'})