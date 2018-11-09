import envoxy
import uwsgi


class HelloWorldView(envoxy.View):

    class Meta:
        endpoint = '/v3/hello-world'
        protocols = ['http']

    def get(self, request: envoxy.Any = None) -> envoxy.Response:
        return envoxy.Response({'text': 'Hello World!'}, status=500)

    def post(self, request: envoxy.Any = None) -> envoxy.Response:
        return envoxy.Response(
            [
                {
                    'id': 1,
                    'name': 'Matheus'
                }
            ],
            status=200
        )

class HelloWorld2View(envoxy.View):

    class Meta:
        endpoint = '/v3/hello-world2'
        protocols = ['http']

    def get(self, request: envoxy.Any = None) -> envoxy.Response:
        return envoxy.Response({'text': 'Hello World!'}, status=200)

    def post(self, request: envoxy.Any = None) -> envoxy.Response:
        return envoxy.Response(
            [
                {
                    'id': 1,
                    'name': 'Matheus'
                }
            ],
            status=200
        )