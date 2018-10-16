import envoxy

class HelloWorldView(envoxy.Event):

    class Meta:
        protocols = ['http']
        endpoint = '/v3/hello-world'
        methods = ['get', 'post']

    def get(self, request={}) -> envoxy.Response:
        return envoxy.Response({'text': 'Hello World!'}, 200)