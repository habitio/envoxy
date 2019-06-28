import requests
from ..utils.logs import Log
from ..utils.config import Config
import sys

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

def get_auth_module():
    _plugins = Config.plugins()

    if 'auth' in _plugins.keys():

        if _plugins['auth'] not in sys.path:
            sys.path.append(_plugins['auth'])
        from auth import Auth
        return Auth
    else:
        from ..auth.backends import Auth
        return Auth
    return None

class Auth(object):

    def authenticate(self, request):
        raise NotImplementedError