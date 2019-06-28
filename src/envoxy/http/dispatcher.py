from typing import Dict

import requests
from flask import Response

from ..utils.handlers import Handler as UtilHandler


class Dispatcher:
    
    @staticmethod
    def get(_url: str, _params: Dict = {}) -> Response:
        try:
            return UtilHandler.response(requests.get(_url, _params))
        except Exception as e:
            return Response({'text': e}, 500)

    @staticmethod
    def post(_url: str, _payload: Dict = {}) -> Response:
        try:
            return UtilHandler.response(requests.post(_url, data=_payload))
        except Exception as e:
            return Response({'text': e}, 500)

    @staticmethod
    def put(_url: str, _payload: Dict = {}, _params: Dict = {}) -> Response:
        try:
            return UtilHandler.response(requests.put(_url, params=_params, data=_payload))
        except Exception as e:
            return Response({'text': e}, 500)

    @staticmethod
    def patch(_url: str, _payload: Dict = {}, _params: Dict = {}) -> Response:
        try:
            return UtilHandler.response(requests.patch(_url, data=_payload, params=_params))
        except Exception as e:
            return Response({'text': e}, 500)

    @staticmethod
    def delete(_url: str, _params: Dict = {}) -> Response:
        try:
            return UtilHandler.response(requests.delete(_url, params=_params))
        except Exception as e:
            return Response({'text': e}, 500)
