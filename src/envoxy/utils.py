import json

from requests import Response as RequestsResponse
from flask import Response as FlaskResponse

class Utils:

    @staticmethod
    def response_handler(response: RequestsResponse) -> FlaskResponse:
        try:
            return FlaskResponse(response.text, response.status_code, headers=response.headers.items())
        except Exception as e:
            return FlaskResponse({'text': e}, 500)