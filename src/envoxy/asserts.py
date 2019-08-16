from requests import codes as status_codes
from .exceptions import ValidationException
from collections.abc import Iterable

def assertz(_expression, _error_message, _error_code, _status_code):

    """
    :param _expression: a boolean expression to be validated
    :param _error_message: exception message to be passed as "text" param in payload response
    :param _error_code: internal error code
    :param _status_code: HTTP status code to be replied to the invoking HTTP client
    """
    # import pdb; pdb.set_trace()
    if not _expression:
        raise ValidationException(_error_message, code=_error_code, status=_status_code)


def assertz_mandatory(_obj, _element=None, _error_code=1200, _status_code=status_codes.precondition_failed):
    """
    Validates if an element is part of another object and value should't be an empty string
    when not given and _element only validates _ob
    """

    if isinstance(_element, str) and not _element:
        assertz(_element, "Key must not be emtpy", 1201, _status_code)
    elif _obj and _element is not None:
        assertz(_element in _obj and _element is not None and _obj[_element], f"Mandatory: {_element}", _error_code, _status_code)
    else:
        assertz(_obj, f"Mandatory: {_obj}", _error_code, _status_code)


def assertz_string(_element, _error_code=1202, _status_code=status_codes.precondition_failed):
    if _element is None: return None

    if isinstance(_element, str):
        assertz(_element, f"Invalid value type: {_element}", _error_code, _status_code)
    else:
        assertz(isinstance(_element, str), f"Invalid value type: {_element}", _error_code, _status_code)


def assertz_integer(_element, _error_code=1202,  _status_code=status_codes.precondition_failed):
    if _element is None: return None

    if isinstance(_element, int):
        assertz(_element, f"Invalid value type: {_element}", _error_code, _status_code)
    else:
        assertz(isinstance(_element, int), f"Invalid value type: {_element}", _error_code, _status_code)



def assertz_float(_element, _error_code=1202,  _status_code=status_codes.precondition_failed):
    if _element is None: return None

    if isinstance(_element, float):
        assertz(_element, f"Invalid value type: {_element}", _error_code, _status_code)
    else:
        assertz(isinstance(_element, float), f"Invalid value type: {_element}", _error_code, _status_code)

def assertz_timestamp(x, y, z):
    pass


def assertz_boolean(_element, _error_code=1202,  _status_code=status_codes.precondition_failed):
    if _element is None: return None

    if isinstance(_element, bool):
        assertz(_element in [True, False], f"Invalid value type: {_element}", _error_code, _status_code)
    else:
        assertz(isinstance(_element, bool), f"Invalid value type: {_element}", _error_code, _status_code)


def assertz_complex(x, y, z):
    pass


def assertz_object(x, y, z):
    pass


def assertz_array(x, y, z):
    pass
