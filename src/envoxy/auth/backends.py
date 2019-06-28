import requests
from ..utils.logs import Log
from ..db import CouchDBDispatcher as couchdbc
from datetime import datetime

def authenticate_container(credentials):

    auth_url = credentials.get("server")
    data = {
        "client_id": credentials.get("client_id"),
        "client_secret": credentials.get("client_secret"),
        "response_type": credentials.get("response_type"),
        "scope": credentials.get("scope"),
        "state": "active"
    }

    if not "" in data.values() and auth_url:
        try:
            resp = requests.get(auth_url, params=data)
            Log.info("Response >> {}".format(resp.status_code))
        except requests.RequestException as e:
            Log.emergency("Error while performing authorization {}".format(e))
            exit(-10)

        if resp.status_code == requests.codes.ok:
            return resp.json()

    Log.emergency("Authorization data incomplete")
    exit(-10)



class Auth(object):


    def authenticate(self, request):

        auth_header = request.headers.get('Authorization', '').split(' ')
        access_token = auth_header[0] if len(auth_header) == 1 else auth_header[1]

        if not self.validate(access_token):
            raise Exception('Invalid Token')

        return access_token

    def get_token(self, token):

        valid_token = couchdbc.get(
            token,
            db='muzzley.muzzley_tokens',
        )

        return valid_token

    def validate(self, token):

        valid_token = self.get_token(token)

        if not valid_token:
            raise Exception('Invalid Token')

        now = datetime.now()
        _expires = datetime.strptime(valid_token['expires'], '%Y-%m-%dT%H:%M:%S.%f+0000')

        if _expires < now:
            raise Exception('Token Expired')

        return valid_token


