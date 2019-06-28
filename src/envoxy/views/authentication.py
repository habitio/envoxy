import requests
from flask import Response

from .views import View
from ..utils.config import Config
from ..utils.logs import Log

_plugins = Config.plugins()

if 'auth' in _plugins.keys():
    import sys
    sys.path.append(_plugins.append(_plugins['auth']))
    from auth import Auth
else:
    from ..auth.backends import Auth


class AuthRequiredView(View):

    valid_token = 'admin'


    def authenticate(self, request):
        """

        :param request:
        :return:
        """

        return Auth().authenticate(request)
    
    def dispatch(self, request, *args, **kwargs):

        try:
            self.authenticate(request)
        except Exception as e:
            return self.unauthorized(e)

        return super(AuthRequiredView, self).dispatch(request, *args, **kwargs)


    def unauthorized(self, e):
        return Response(str(e), requests.codes.unauthorized)



