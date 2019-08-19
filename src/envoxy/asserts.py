from requests import codes as status_codes
from .exceptions import ValidationException
from collections.abc import Iterable
import json
import datetime
from .utils.datetime import Now

def assertz(_expression, _error_message, _error_code, _status_code):

    """
    :param _expression: a boolean expression to be validated
    :param _error_message: exception message to be passed as "text" param in payload response
    :param _error_code: internal error code
    :param _status_code: HTTP status code to be replied to the invoking HTTP client
    """
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


def assertz_string(_element, key=None, _error_code=1202, _status_code=status_codes.precondition_failed):
    if _element is None: return None

    if isinstance(_element, str) and key is None:
        assertz(_element, f"Invalid value type: {_element}", _error_code, _status_code)
    else:
        assertz( key in _element and isinstance(_element[key], str), f"Invalid value type: {_element[key]}", _error_code, _status_code)


def assertz_integer(_element, key=None, _error_code=1202,  _status_code=status_codes.precondition_failed):
    if _element is None: return None

    if isinstance(_element, int) and key is None:
        assertz(_element, f"Invalid value type: {_element}", _error_code, _status_code)
    else:
        assertz(key in _element and isinstance(_element[key], int), f"Invalid value type: {_element[key]}", _error_code, _status_code)


def assertz_float(_element, key=None, _error_code=1202,  _status_code=status_codes.precondition_failed):
    if _element is None: return None

    if isinstance(_element, float) and key is None:
        assertz(_element, f"Invalid value type: {_element}", _error_code, _status_code)
    else:
        assertz(key in _element and isinstance(_element[key], float), f"Invalid value type: {_element[key]}", _error_code, _status_code)

def assertz_timestamp(_element, key=None, _error_code=1202,  _status_code=status_codes.precondition_failed):
    if _element is None or isinstance(_element, datetime.date) or isinstance(_element, datetime.date): return None

    if key is None:
        assertz(Now.to_datetime(_element), f"Invalid value type: {_element}", _error_code, _status_code)
    else :
        assertz(key in _element and Now.to_datetime(_element[key]), f"Invalid value type: {_element[key]}", _error_code, _status_code)


def assertz_boolean(_element, key=None, _error_code=1202,  _status_code=status_codes.precondition_failed):
    if _element is None: return None

    if isinstance(_element, bool) and key is None:
        assertz(_element in [True, False], f"Invalid value type: {_element}", _error_code, _status_code)
    else:
        assertz(key in _element and isinstance(_element[key], bool), f"Invalid value type: {_element[key]}", _error_code, _status_code)


def assertz_array(_element, key=None, _error_code=1202,  _status_code=status_codes.precondition_failed):
    if _element is None: return None

    try:
        value = _element if key is None else _element[key]
    except KeyError:
        assertz(False, f"Invalid value type: {key}", _error_code, _status_code)

    try:
        assertz(isinstance(value, list) and value, f"Invalid value type: {value}", _error_code, _status_code)
    except TypeError:
        assertz(False, f"Invalid value type: {value}", _error_code, _status_code)


def assertz_dict(_element, key=None, _error_code=1202,  _status_code=status_codes.precondition_failed):
    if _element is None: return None

    try:
        value = _element if key is None else _element[key]
    except KeyError:
        assertz(False, f"Invalid value type: {key}", _error_code, _status_code)

    try:
        assertz((isinstance(value, dict) and value), f"Invalid value type: {value}", _error_code, _status_code)

    except TypeError:

        assertz(False, f"Invalid value type: {value}", _error_code, _status_code)


def assertz_json(_element, key=None, _error_code=1202,  _status_code=status_codes.precondition_failed):
    if _element is None: return None

    try:
        value = _element if key is None else _element[key]
    except KeyError:
        assertz(False, f"Invalid value type: {key}", _error_code, _status_code)

    try:
        assertz(json.loads(value), f"Invalid value type: {value}", _error_code, _status_code)

    except (json.JSONDecodeError, TypeError):

        assertz(False, f"Invalid value type: {value}", _error_code, _status_code)


def assertz_complex(_element, key=None, _error_code=1202,  _status_code=status_codes.precondition_failed):
    if _element is None: return None

    msg = ""

    try:
        is_json = assertz_json(_element, key, _error_code, _status_code)
    except ValidationException as e:
        is_json = False
        msg = str(e)

    try:
        is_dict = assertz_dict(_element, key, _error_code, _status_code)
    except ValidationException as e:
        is_dict = False
        msg = str(e)

    try:
        is_array = assertz_array(_element, key, _error_code, _status_code)
    except ValidationException as e:
        is_array = False
        msg = str(e)

    assertz(None in [is_json, is_dict, is_array], msg, _error_code, _status_code)
