import re
import sys
import importlib

import requests
import datetime
from ..utils.config import Config
from ..utils.logs import Log


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

def get_auth_module(module_name=None):
    _plugins = Config.plugins()

    if 'auth' in _plugins.keys():

        if _plugins['auth'] not in sys.path:
            sys.path.append(_plugins['auth'])

        if module_name:
            module = importlib.import_module(module_name)
            return module

        from auth import Auth
        return Auth
    else:
        from ..auth.backends import Auth
        return Auth

    return None

def get_topic(_topic):

    REGEX_VAR_PATTERN = '{(?P<all>(?P<var>[^:]+):(?P<type>[^}]+))}'
    _regex = re.compile(REGEX_VAR_PATTERN)

    for _match in _regex.finditer(_topic):
        _groups = _match.groupdict()
        var = _groups['var']
        _topic = _topic.replace(_groups['all'], f"{var}")

    return _topic



class AuthBackendMixin:

    @property
    def AuthorizationException(self):
        AuthBackend = get_auth_module()
        try:
            return AuthBackend.exception
        except AttributeError:
            return Exception

    def authenticate(self, request, *args, **kwargs):
        """

        :param request:
        :return:
        """

        _endpoint = kwargs.get('endpoint', '')
        topic = get_topic(_endpoint)
        AuthBackend = get_auth_module()
        return AuthBackend().authenticate(request, topic=topic, **kwargs)

    def anonymous(self, request, *args, **kwargs):
        """

        :param request:
        :return:
        """
        _endpoint = kwargs.get('endpoint', '')
        topic = get_topic(_endpoint)
        AuthBackend = get_auth_module()
        return AuthBackend().anonymous(request, topic=topic, **kwargs)
