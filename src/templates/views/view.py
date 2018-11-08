import envoxy
import uwsgi


class HelloWorldView(envoxy.View):

    class Meta:
        endpoint = '/v3/hello-world'
        protocols = ['http']

    def get(self, request: envoxy.Any = None) -> envoxy.Response:
        
        envoxy.log.trace('>>> uwsgi: {}\n'.format(dir(uwsgi)))
        envoxy.log.trace('>>> uwsgi: {}\n'.format(uwsgi.opt))
        envoxy.log.trace('Test trace: {}\n'.format(request.headers))
        envoxy.log.error('Test trace: {}\n'.format(request))
        envoxy.log.emergency('Test trace: {}\n'.format(request))
        envoxy.log.debug('Test trace: {}\n'.format(request))

        envoxy.log.emergency('Test trace: {}\n'.format(request))
        envoxy.log.alert('Test trace: {}\n'.format(request))
        envoxy.log.critical('Test trace: {}\n'.format(request))
        envoxy.log.error('Test trace: {}\n'.format(request))
        envoxy.log.warning('Test trace: {}\n'.format(request))
        envoxy.log.notice('Test trace: {}\n'.format(request))
        envoxy.log.info('Test trace: {}\n'.format(request))
        envoxy.log.debug('Test trace: {}\n'.format(request))
        envoxy.log.trace('Test trace: {}\n'.format(request))
        envoxy.log.verbose('Test trace: {}\n'.format(request))

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