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