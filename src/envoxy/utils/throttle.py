import time
from collections import defaultdict
from functools import wraps

get_time = time.time

__nop = lambda: None
__throttle_last_time = defaultdict(__nop)

def throttle(duration=1, **kw):
    """ 
    Throttle a function on a duration. Prevent it to be called
    more than once within a period.
    For example:
        # normal use case
        @throttle(5)
        def echo(msg):
            print "echo %s" % msg
        # more sophisticated use case
        def _update_status():
            import datetime
            print "last updated: %s" % datetime.datetime.now()
        @throttle(duration=10, on_throttling=_update_status)
        def echo(msg):
            print "echo %s" % msg 
    @param duration: the number of seconds for throttling period
    @type duration: int or float
    @param on_throttling: a function to be called during the throttle period
    @type on_throttling: function or callable
    """
    on_throttling = kw.pop("on_throttling", __nop)

    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            last_time = __throttle_last_time[func]
            if last_time is None or get_time() >= last_time + duration:
                __throttle_last_time[func] = get_time()
                return func(*args, **kwargs)
            else:
                on_throttling()

        return wrapper

    return decorator
