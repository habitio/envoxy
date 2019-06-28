import requests
from flask import Response

from .views import View

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



