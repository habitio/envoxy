import threading

# A thread-safe implementation of Singleton pattern
# To be used as mixin or base class
class Singleton(object):
    
    # use special name mangling for private class-level lock
    # we don't want a global lock for all the classes that use Singleton
    # each class should have its own lock to reduce locking contention
    __lock = threading.Lock()
    
    # private class instance may not necessarily need name-mangling
    __instance = None
    
    @classmethod
    def instance(cls):
        
        if not cls.__instance:
            
            with cls.__lock:
                if not cls.__instance:
                    cls.__instance = cls()
        
        return cls.__instance


# A per-thread container implementation of Singleton pattern
# To be used as mixin or base class
class SingletonPerThread(object):
    # use special name mangling for private class-level lock
    # we don't want a global lock for all the classes that use Singleton
    # each class should have its own lock to reduce locking contention
    __locks = {}
    # private class instances may not necessarily need name-mangling
    __instances = {}
    @classmethod
    def instance(cls):
        _thread_id = threading.get_ident()
        if _thread_id not in cls.__locks:
            cls.__locks[_thread_id] = threading.Lock()
        if not cls.__instances.get(_thread_id):
            with cls.__locks[_thread_id]:
                if not cls.__instances.get(_thread_id):
                    cls.__instances[_thread_id] = cls()
        return cls.__instances[_thread_id]
