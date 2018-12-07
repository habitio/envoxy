from .views.containers import Response

def event_wrapper(object_):
    return Response(object_).to_flask()

def on(**kwargs):
    
    def _decorate(klass):

        class Meta:
            pass

        klass.__metaclass__ = Meta

        for _key, _value in kwargs.items():
            setattr(klass.__metaclass__, _key, _value)

        return klass

    return _decorate