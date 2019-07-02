from envoxy import View, Response, on, log, zmqc, pgsqlc, couchdbc, auth_required

@on(endpoint='/v3/cards', protocols=['http'])
class CardsCollection(View):


    @auth_required(['container', 'manager'])
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

    def get(self, request, uuid):
        return Response(
            zmqc.get(
                'muzzley-platform', 
                '/v3/data-layer/cards/{}'.format(uuid),
                params=request.args,
                headers=request.headers.items()
            )
        )

    def put(self, request, uuid):
        return Response(
            zmqc.post(
                'muzzley-platform', 
                '/v3/data-layer/cards/{}'.format(uuid), 
                params=request.args,
                payload=request.json(),
                headers=request.headers.items()
            )
        )

    def patch(self, request, uuid):
        return Response(
            zmqc.patch(
                'muzzley-platform', 
                '/v3/data-layer/cards/{}'.format(uuid), 
                params=request.args,
                payload=request.json(),
                headers=request.headers.items()
            )
        )

    def delete(self, request, uuid):
        return Response(
            zmqc.delete(
                'muzzley-platform', 
                '/v3/data-layer/cards/{}'.format(uuid),
                headers=request.headers.items()
            )
        )


