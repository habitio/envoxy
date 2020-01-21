from functools import wraps
from .auth.backends import AuthBackendMixin
from .constants import CACHE_DEFAULT_TTL, GET
from .cache import Cache
from .utils.logs import Log
import requests
import json

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

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __call__(self, func):

        @wraps(func)
        def wrapped_func(view, request, *args, **kwargs):
            if self.kwargs: kwargs.update(**self.kwargs)

            headers = AuthBackendMixin().authenticate(request, *args, **kwargs)
            if headers: kwargs.update(**headers)

            return func(view, request, *args, **kwargs)
        return wrapped_func


class cache(object):

    def __init__(self, ttl=CACHE_DEFAULT_TTL):
        self.ttl = ttl
        self.cache = Cache().get_backend()

    def __call__(self, func):

        @wraps(func)
        def wrapped_func(view, request, *args, **kwargs):

            _endpoint = request.full_path
            _method = func.__name__
            _params = request.get_json() if _method != GET else {}
            result = self.cache.get(_endpoint, _method, _params)

            Log.verbose(f'cached method {_endpoint} {_method}')

            if result:
                return view.cached_response(result)

            response = func(view, request, *args, **kwargs)

            if response and not result and response.status_code == requests.codes.ok:
                self.cache.set(_endpoint, _method, _params, response.get_json(), ttl=self.ttl)

            return response

        return wrapped_func



class log_event(object):

    def __init__(self, func):
        self.func = func

    def __call__(self, client, userdata, msg, **kwargs):

        _message = '{} [{}] {}'.format(
            Log.style.apply('< ON_EVENT', Log.style.BOLD),
            Log.style.apply('MQTT', Log.style.GREEN_FG),
            Log.style.apply('{}'.format(msg.topic), Log.style.BLUE_FG)
        )
        Log.trace(_message)

        data = json.loads(msg.payload.decode("utf-8"))
        _message = '{} | Message{}'.format(_message, data)

        Log.verbose(_message)

        return self.func(self.func.__class__, data)


class auth_anonymous_allowed(object):

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __call__(self, func):

        @wraps(func)
        def wrapped_func(view, request, *args, **kwargs):
            if self.kwargs: kwargs.update(**self.kwargs)

            headers = AuthBackendMixin().anonymous(request, *args, **kwargs)
            if headers: kwargs.update(**headers)

            return func(view, request, *args, **kwargs)
        return wrapped_func
