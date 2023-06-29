import cProfile
import pstats
import contextlib

def profiled_decorator(func, top=10, type='cumulative'):
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
        _stats.sort_stats(type).print_stats(top)
        
        return _result
    
    return _wrapper

@contextlib.contextmanager
def profiled_context(top=10, type='cumulative'):
    """
    Context manager for function profiling
    Usage:
    with profiled_context():
        do_something()
    """

    _profiler = cProfile.Profile()
    _profiler.enable()
    
    yield
    
    _profiler.disable()
    _profiler.create_stats()
    
    _stats = pstats.Stats(_profiler)
    _stats.sort_stats(type).print_stats(top)
    
def profile_func(func, *args, **kwargs):
    """
    Function profiling
    Usage:
    result = profile_func(my_function, arg1, arg2, keyword_arg=3, pf_top=5, pf_type='tottime')
    """
    _top = kwargs.pop('pf_top', 10)
    _type = kwargs.pop('pf_type', 'cumulative')

    with profiled_context(top=_top, type=_type):
        return func(*args, **kwargs)