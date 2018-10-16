from requests import Response as RequestsResponse
from flask import Response as FlaskResponse

class Utils:

    @staticmethod
    def response_handler(response: RequestsResponse) -> FlaskResponse:
        try:
            return FlaskResponse(response.text, response.status_code, headers=response.headers.items())
        except Exception as e:
            return FlaskResponse({'text': e}, 500)

    @staticmethod
    def make_registering_decorator_factory(_foreign_decorator_factory):
        
        def _new_decorator_factory(*_args, **_kw):
            
            _old_generated_decorator = _foreign_decorator_factory(*_args, **_kw)
            
            def _new_generated_decorator(_func):
                
                _modified_func = _old_generated_decorator(_func)
                _modified_func.decorator = _new_decorator_factory # keep track of decorator
                
                return _modified_func
        
            return _new_generated_decorator
        
        _new_decorator_factory.__name__ = _foreign_decorator_factory.__name__
        _new_decorator_factory.__doc__ = _foreign_decorator_factory.__doc__
    
        return _new_decorator_factory