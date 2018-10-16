from .utils import Utils

class route(object):

    def __init__(self, _endpoint):
        self.__endpoint = _endpoint

    def __call__(self, _f):

        def _wrapped_f(*_args, **kwargs):
            _f(*_args, **kwargs)
        
        return _wrapped_f

route = Utils.make_registering_decorator_factory(route)