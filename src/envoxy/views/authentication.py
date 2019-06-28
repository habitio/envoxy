import requests
from flask import Response

from .views import View
from ..auth.backends import get_auth_module

class AuthRequiredView(View):

    valid_token = 'admin'


    def authenticate(self, request):
        """

        :param request:
        :return:
        """

        AuthBackend = get_auth_module()
        return AuthBackend().authenticate(request)
    
    def dispatch(self, request, *args, **kwargs):
        try:
            self.authenticate(request)
        except Exception as e:
            return self.unauthorized(e)

        return super(AuthRequiredView, self).dispatch(request, *args, **kwargs)


    def unauthorized(self, e):
        return Response(str(e), requests.codes.unauthorized)



