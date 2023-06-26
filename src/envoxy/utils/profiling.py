import cProfile
import pstats
import contextlib

def profiled_decorator(func):
    """
    Decorator for function profiling
    Usage:
    @profiled_decorator
    def my_function(arg1, arg2, keyword_arg=3):
        do_something()
    """

    def _wrapper(*args, **kwargs):
        
        _profiler = cProfile.Profile()
        
        _result = _profiler.runcall(func, *args, **kwargs)
        
        _profiler.create_stats()
        
        _stats = pstats.Stats(_profiler)
        _stats.strip_dirs()\
            .sort_stats('cumulative')\
            .print_stats(10) # Print top 10 time consuming functions
        
        return _result
    
    return _wrapper

@contextlib.contextmanager
def profiled_context():
    """
    Context manager for function profiling
    Usage:
    with profiled_context():
        do_something()
    """

    profiler = cProfile.Profile()
    profiler.enable()
    
    yield
    
    profiler.disable()
    profiler.create_stats()
    
    stats = pstats.Stats(profiler)
    stats.strip_dirs()\
        .sort_stats('cumulative')\
        .print_stats(10)  # Print top 10 time-consuming functions

def profile_func(func, *args, **kwargs):
    """
    Function profiling
    Usage:
    result = profile_func(my_function, arg1, arg2, keyword_arg=3)
    """
    with profiled_context():
        return func(*args, **kwargs)