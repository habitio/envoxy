from .constants import *
from .decorators import *
from .http_handler import HttpHandler as http
from .event_handler import EventHandler as Event
from flask import Request, Response as FlaskResponse
from typing import *
import json

def Response(_object, _status) -> FlaskResponse:
    if type(_object) in [dict, list]:
        return FlaskResponse(json.dumps(_object), _status, {'Content-Type': 'application/json'})
    elif type(_object) in [str]:
        return FlaskResponse(_object, _status, {'Content-Type': 'text/html'})
    else:
        return FlaskResponse(json.dumps({'text':'Error in parsing the response object.'}), 500, {'Content-Type': 'text/html'})

