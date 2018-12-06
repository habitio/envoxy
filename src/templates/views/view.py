from envoxy import View, Response, on, log, zmqc

@on(endpoint='/v3/cards', protocols=['http'])
class HelloWorldCollection(View):

    def get(self, request):
        return Response(
            zmqc.get(
                'muzzley-platform', 
                '/v3/data-layer/cards', 
                params={'page_size': 100},
                headers=request.headers.items()
            )
        )

    def post(self, request):

        _payload = request.json()

        return Response(
            [
                {
                    'id': 1,
                    'name': 'Matheus'
                }
            ],
            status=200
        )

@on(endpoint='/v3/cards/{uuid:str}', protocols=['http'])
class HelloWorldDocument(View):

    def get(self, uuid, size, request):
        return Response(
            {
                'id': 1,
                'name': uuid
            }, 
            status=200
        )

    def put(self, uuid, request):

        log.info(request)

        return Response(
            {
                'id': size,
                'href': uuid
            },
            status=200
        )