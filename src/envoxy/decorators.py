from .views.containers import Response
from functools import wraps
from .auth.backends import AuthBackendMixin

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


class auth_required(object):

    def __init__(self, roles=None):
        self.role_list = roles

    def __call__(self, func):

        @wraps(func)
        def wrapped_func(view, request, *args, **kwargs):

            if self.role_list:
                kwargs.update({
                    'roles_needed': self.role_list
                })
            AuthBackendMixin().authenticate(request, *args, **kwargs)

            return func(view, request, *args, **kwargs)
        return wrapped_func
