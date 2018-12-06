from .views.containers import Response

def event_wrapper(_object):
    return Response(_object).to_flask()

def on(**_kwargs):
    
    def _decorate(_klass):

        class Meta:
            pass

        _klass.__metaclass__ = Meta

        for _key, _value in _kwargs.items():
            setattr(_klass.__metaclass__, _key, _value)

        return _klass

    return _decorate