from envoxy import View, Response, on, log, zmqc, pgsqlc

@on(endpoint='/v3/cards', protocols=['http'])
class CardsCollection(View):

    def get(self, request):
        return Response(
            zmqc.get(
                'muzzley-platform', 
                '/v3/data-layer/cards', 
                params=request.args,
                headers=request.headers.items()
            )
        )

    def post(self, request):
        return Response(
            zmqc.post(
                'muzzley-platform', 
                '/v3/data-layer/cards', 
                payload=request.json(),
                headers=request.headers.items()
            )
        )

@on(endpoint='/v3/cards/{uuid:str}', protocols=['http'])
class CardsDocument(View):

    def get(self, uuid, request):
        return Response(
            zmqc.get(
                'muzzley-platform', 
                '/v3/data-layer/cards/{}'.format(uuid),
                params=request.args,
                headers=request.headers.items()
            )
        )

    def put(self, uuid, request):
        return Response(
            zmqc.post(
                'muzzley-platform', 
                '/v3/data-layer/cards/{}'.format(uuid), 
                params=request.args,
                payload=request.json(),
                headers=request.headers.items()
            )
        )

    def patch(self, uuid, request):
        return Response(
            zmqc.patch(
                'muzzley-platform', 
                '/v3/data-layer/cards/{}'.format(uuid), 
                params=request.args,
                payload=request.json(),
                headers=request.headers.items()
            )
        )

    def delete(self, uuid, request):
        return Response(
            zmqc.delete(
                'muzzley-platform', 
                '/v3/data-layer/cards/{}'.format(uuid),
                headers=request.headers.items()
            )
        )
