import threading


# Thread-safe per-class Singleton base.
#
# Notes:
# - We avoid double-underscore (name-mangling) class attributes because that
#   binds attribute names to this base class and causes subclasses to share
#   the same lock/instance unexpectedly. Instead we attach per-subclass
#   attributes on `cls` (e.g. `_instance`, `_instance_lock`) which ensures
#   isolation between subclasses.
class Singleton(object):
    """Simple thread-safe per-class singleton.

    Usage: subclass ``Singleton`` and call ``YourClass.instance()``. The first
    call will construct and cache the instance on the subclass object. An
    optional ``instance_with_queue(queue_)`` helper is kept for compatibility.
    """

    @classmethod
    def instance(cls, *args, **kwargs):
        # fast-path without lock
        if not getattr(cls, '_instance', None):
            # ensure a per-class lock exists
            if not getattr(cls, '_instance_lock', None):
                # benign race: first writer wins
                cls._instance_lock = threading.Lock()

            with cls._instance_lock:
                if not getattr(cls, '_instance', None):
                    cls._instance = cls(*args, **kwargs)

        return cls._instance

    @classmethod
    def instance_with_queue(cls, queue_):
        # Delegate to instance(), allowing queue_ to be passed to the ctor
        return cls.instance(queue_=queue_)


# Per-thread singleton using thread-local storage. Each thread gets its own
# instance of the subclass. This avoids an ever-growing mapping keyed by
# thread id and simplifies cleanup when threads exit.
class SingletonPerThread(object):
    """Per-thread singleton base class.

    Usage: subclass and call ``YourClass.instance()``; each thread will get its
    own instance. The implementation stores a `threading.local` container on
    the subclass to isolate instances to threads.
    """

    @classmethod
    def _get_thread_local(cls) -> threading.local:
        if not getattr(cls, '_thread_local', None):
            # benign race: first writer wins
            cls._thread_local = threading.local()
        return cls._thread_local

    @classmethod
    def instance(cls, *args, **kwargs):
        tl = cls._get_thread_local()
        inst = getattr(tl, 'instance', None)
        if inst is None:
            inst = cls(*args, **kwargs)
            tl.instance = inst
        return inst

    @classmethod
    def instance_with_queue(cls, queue_):
    # Delegate to the primary constructor path; pass queue_ through so
    # callers that expect to inject a queue can continue to do so. This
    # avoids static analysis complaints about unknown ctor parameters.
    return cls.instance(queue_=queue_)
