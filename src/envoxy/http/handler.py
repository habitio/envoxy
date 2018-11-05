import requests

from typing import Dict
from flask import Response

from ..event_handler import EventHandler
from ..utils import Utils


class Handler(EventHandler):
    
    @staticmethod
    def get(_url: str, _params: Dict = {}) -> Response:
        try:
            return Utils.response_handler(requests.get(_url, _params))
        except Exception as e:
            return Response({'text': e}, 500)

    @staticmethod
    def post(_url: str, _payload: Dict = {}) -> Response:
        try:
            return Utils.response_handler(requests.post(_url, data=_payload))
        except Exception as e:
            return Response({'text': e}, 500)

    @staticmethod
    def put(_url: str, _payload: Dict = {}, _params: Dict = {}) -> Response:
        try:
            return Utils.response_handler(requests.put(_url, params=_params, data=_payload))
        except Exception as e:
            return Response({'text': e}, 500)

    @staticmethod
    def patch(_url: str, _payload: Dict = {}, _params: Dict = {}) -> Response:
        try:
            return Utils.response_handler(requests.patch(_url, data=_payload, params=_params))
        except Exception as e:
            return Response({'text': e}, 500)

    @staticmethod
    def delete(_url: str, _params: Dict = {}) -> Response:
        try:
            return Utils.response_handler(requests.delete(_url, params=_params))
        except Exception as e:
            return Response({'text': e}, 500)
