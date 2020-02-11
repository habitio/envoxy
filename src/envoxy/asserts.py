from requests import codes as status_codes

from .exceptions import ValidationException
import json
import datetime
from .utils.datetime import Now
from uuid import UUID
import re
from .constants import HASH_REGEX, URI_REGEX, EMAIL_REGEX, PHONE_REGEX, TOKEN_REGEX, URL_REGEX
from inspect import getframeinfo, stack

DEFAULT_STATUS_CODE = status_codes.precondition_failed
INVALID_TYPE_ERROR_CODE = 1202


def assertz(_expression, _error_message, _error_code, _status_code):
    """
    :param _expression: a boolean expression to be validated
    :param _error_message: exception message to be passed as "text" param in payload response
    :param _error_code: internal error code
    :param _status_code: HTTP status code to be replied to the invoking HTTP client
    """
    if not _expression:
        raise ValidationException(_error_message, code=_error_code, status=_status_code)

def assertz_reply(_expression, _error_msg, _error_code, _status_code):
    """
    same as assertz but instead of raising exception will return a dictionary
    :param _expression:
    :param _error_msg:
    :param _status_code:
    :param _error_code:
    :return:
    """
    caller = getframeinfo(stack()[1][0])
    _file = '.'.join(caller.filename.split('/')[-3:])
    _lineno = caller.lineno

    if not _expression:
        return {
            "status": _status_code,
            "payload": {
                "text": _error_msg,
                "code": _error_code,
                "assertion_failed": f"{caller.code_context} failed on file {_file}, line {_lineno}"
            }
        }

def assertz_call(_expression, _error_msg, _error_code, _status_code, reply=False):
    if not reply:
        return assertz(_expression, _error_msg, _error_code, _status_code)
    else:
        return assertz_reply(_expression, _error_msg, _error_code, _status_code)


def assertz_mandatory(_obj, _element=None, _error_code=1200, _status_code=DEFAULT_STATUS_CODE, reply=False):
    """
    Validates if an element is part of another object and value should't be an empty string
    when not given and _element only validates _ob
    """
    if isinstance(_element, str) and not _element:
        return assertz_call(_element, "Key must not be emtpy", 1201, _status_code, reply=reply)
    elif _obj and _element is not None:
        return assertz_call(_element in _obj and _element is not None and _obj[_element] is not None, f"Mandatory: {_element}", _error_code,
                _status_code, reply=reply)
    else:
        return assertz_call(_obj, f"Mandatory: {_obj}", _error_code, _status_code, reply=reply)


def assertz_string(_element, key=None, _error_code=INVALID_TYPE_ERROR_CODE, _status_code=DEFAULT_STATUS_CODE, reply=False):
    if _element is None: return None

    try:
        value = _element if key is None else _element[key]
    except KeyError:
        return assertz_call(False, f"Invalid value type: {_element}", _error_code, _status_code, reply=reply)

    try:
        return assertz_call(isinstance(value, str), f"Invalid value type: {value}", _error_code, _status_code, reply=reply)
    except (AttributeError, TypeError):
        return assertz_call(False, f"Invalid value type: {value}", _error_code, _status_code, reply=reply)

def assertz_integer(_element, key=None, _error_code=INVALID_TYPE_ERROR_CODE, _status_code=DEFAULT_STATUS_CODE, reply=False):
    if _element is None: return None

    if isinstance(_element, int) and key is None:
        return assertz_call(_element, f"Invalid value type: {_element}", _error_code, _status_code, reply=reply)
    else:
        return assertz_call(key in _element and isinstance(_element[key], int), f"Invalid value type: {_element[key]}", _error_code,
                _status_code, reply=reply)


def assertz_float(_element, key=None, _error_code=INVALID_TYPE_ERROR_CODE, _status_code=DEFAULT_STATUS_CODE, reply=False):
    if _element is None: return None

    if isinstance(_element, float) and key is None:
        return assertz_call(_element, f"Invalid value type: {_element}", _error_code, _status_code, reply=reply)
    else:
        return assertz_call(key in _element and isinstance(_element[key], float), f"Invalid value type: {_element[key]}",
                _error_code, _status_code, reply=reply)


def assertz_timestamp(_element, key=None, _error_code=INVALID_TYPE_ERROR_CODE, _status_code=DEFAULT_STATUS_CODE, reply=False):
    if _element is None or isinstance(_element, datetime.date) or isinstance(_element, datetime.date): return None

    if key is None:
        return assertz_call(Now.to_datetime(_element), f"Invalid value type: {_element}", _error_code, _status_code, reply=reply)
    else:
        return assertz_call(key in _element and Now.to_datetime(_element[key]), f"Invalid value type: {_element[key]}", _error_code,
                _status_code, reply=reply)


def assertz_boolean(_element, key=None, _error_code=INVALID_TYPE_ERROR_CODE, _status_code=DEFAULT_STATUS_CODE, reply=False):
    if _element is None: return None

    if isinstance(_element, bool) and key is None:
        return assertz_call(_element in [True, False], f"Invalid value type: {_element}", _error_code, _status_code, reply=reply)
    else:
        return assertz_call(key in _element and isinstance(_element[key], bool), f"Invalid value type: {_element[key]}",
                _error_code, _status_code, reply=reply)


def assertz_array(_element, key=None, _error_code=INVALID_TYPE_ERROR_CODE, _status_code=DEFAULT_STATUS_CODE, reply=False):
    if _element is None: return None

    try:
        value = _element if key is None else _element[key]
    except KeyError:
        return assertz_call(False, f"Invalid value type: {key}", _error_code, _status_code, reply=reply)

    try:
        return assertz_call(isinstance(value, list) and value, f"Invalid value type: {value}", _error_code, _status_code, reply=reply)
    except TypeError:
        return assertz_call(False, f"Invalid value type: {value}", _error_code, _status_code, reply=reply)


def assertz_dict(_element, key=None, _error_code=INVALID_TYPE_ERROR_CODE, _status_code=DEFAULT_STATUS_CODE, reply=False):
    if _element is None: return None

    try:
        value = _element if key is None else _element[key]
    except KeyError:
        return assertz_call(False, f"Invalid value type: {key}", _error_code, _status_code, reply=reply)

    try:
        return assertz_call((isinstance(value, dict) and value), f"Invalid value type: {value}", _error_code, _status_code, reply=reply)

    except TypeError:

        return assertz_call(False, f"Invalid value type: {value}", _error_code, _status_code, reply=reply)


def assertz_json(_element, key=None, _error_code=INVALID_TYPE_ERROR_CODE, _status_code=DEFAULT_STATUS_CODE, reply=False):
    if _element is None: return None

    try:
        value = _element if key is None else _element[key]
    except KeyError:
        return assertz_call(False, f"Invalid value type: {key}", _error_code, _status_code, reply=reply)

    try:
        return assertz_call(json.loads(value), f"Invalid value type: {value}", _error_code, _status_code, reply=reply)

    except (json.JSONDecodeError, TypeError):

        return assertz_call(False, f"Invalid value type: {value}", _error_code, _status_code, reply=reply)


def assertz_complex(_element, key=None, _error_code=INVALID_TYPE_ERROR_CODE, _status_code=DEFAULT_STATUS_CODE, reply=False):
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

    return assertz_call(None in [is_json, is_dict, is_array], msg, _error_code, _status_code, reply=reply)


def assertz_uuid(_element, key=None, _error_code=INVALID_TYPE_ERROR_CODE, _status_code=DEFAULT_STATUS_CODE, reply=False):
    if _element is None: return None

    try:
        value = _element if key is None else _element[key]
    except KeyError:
        return assertz_call(False, f"Invalid value type: {key}", _error_code, _status_code, reply=reply)

    try:
        return assertz_call(UUID(value), f"Invalid value type: {value}", _error_code, _status_code, reply=reply)

    except (ValueError, AttributeError, TypeError):

        return assertz_call(False, f"Invalid value type: {value}", _error_code, _status_code, reply=reply)


def assertz_utf8(_element, key=None, _error_code=INVALID_TYPE_ERROR_CODE, _status_code=DEFAULT_STATUS_CODE, reply=False):
    if _element is None: return None

    _error_msg = "Invalid utf-8 encoding"

    try:
        value = _element if key is None else _element[key]
    except KeyError:
        return assertz_call(False, _error_msg, _error_code, _status_code, reply=reply)

    try:
        return assertz_call(value.encode(encoding='utf-8'), _error_msg, _error_code, _status_code, reply=reply)
    except (UnicodeEncodeError, AttributeError):

        return assertz_call(False, _error_msg, _error_code, _status_code, reply=reply)


def assertz_ascii(_element, key=None, _error_code=INVALID_TYPE_ERROR_CODE, _status_code=DEFAULT_STATUS_CODE, reply=False):
    if _element is None: return None

    _error_msg = "Invalid ascii encoding"

    try:
        value = _element if key is None else _element[key]
    except KeyError:
        return assertz_call(False, _error_msg, _error_code, _status_code, reply=reply)

    try:
        return assertz_call(value.encode(encoding='ascii'), _error_msg, _error_code, _status_code, reply=reply)
    except (UnicodeEncodeError, AttributeError):
        return assertz_call(False, _error_msg, _error_code, _status_code, reply=reply)

def assertz_regex(regex_expr, _error_msg, _element, key=None, _error_code=INVALID_TYPE_ERROR_CODE, _status_code=DEFAULT_STATUS_CODE, reply=False):
    if _element is None: return None

    try:
        value = _element if key is None else _element[key]
        assertz_string(value)

    except (KeyError, ValidationException):
        return assertz_call(False, _error_msg, _error_code, _status_code, reply=reply)

    try:
        return assertz_call(re.match(regex_expr, value).group() == value, _error_msg, _error_code, _status_code)
    except (AttributeError, TypeError):
        return assertz_call(False, _error_msg, _error_code, _status_code, reply=reply)

def assertz_hash(_element, key=None, _error_code=INVALID_TYPE_ERROR_CODE, _status_code=DEFAULT_STATUS_CODE, reply=False):
    return assertz_regex(HASH_REGEX, "Invalid hash", _element, key, _error_code, _status_code, reply=reply)

def assertz_token(_element, key=None, _error_code=INVALID_TYPE_ERROR_CODE, _status_code=DEFAULT_STATUS_CODE, reply=False):
    return assertz_regex(TOKEN_REGEX, "Invalid token", _element, key, _error_code, _status_code, reply=reply)

def assertz_uri(_element, key=None, _error_code=INVALID_TYPE_ERROR_CODE, _status_code=DEFAULT_STATUS_CODE, reply=False):
    return assertz_regex(URI_REGEX, "Invalid uri", _element, key, _error_code, _status_code, reply=reply)

def assertz_url(_element, key=None, _error_code=INVALID_TYPE_ERROR_CODE, _status_code=DEFAULT_STATUS_CODE, reply=False):
    return assertz_regex(URL_REGEX, "Invalid url", _element, key, _error_code, _status_code, reply=reply)

def assertz_email(_element, key=None, _error_code=INVALID_TYPE_ERROR_CODE, _status_code=DEFAULT_STATUS_CODE, reply=False):
    return assertz_regex(EMAIL_REGEX, "Invalid email", _element, key, _error_code, _status_code, reply=reply)

def assertz_location(_element, key=None, _error_code=INVALID_TYPE_ERROR_CODE, _status_code=DEFAULT_STATUS_CODE, reply=False):
    if _element is None: return None

    _error_msg = "Invalid location"

    try:
        value = _element if key is None else _element[key]
    except KeyError:
        return assertz_call(False, _error_msg, _error_code, _status_code, reply=reply)

    try:

        if isinstance(value, dict):

            _expression = 'latitude' in value and 'longitude' in value \
                          and (isinstance(value['latitude'], int) or isinstance(value['latitude'], float)) \
                          and (isinstance(value['longitude'], int) or isinstance(value['longitude'], float))

        elif isinstance(value, list):
            _expression = len(value) == 2 \
                          and (isinstance(value[0], int) or isinstance(value[0], float)) \
                          and (isinstance(value[1], int) or isinstance(value[1], float))

        else:
            raise TypeError

        return assertz_call(_expression, _error_msg, _error_code, _status_code, reply=reply)


    except (AttributeError, TypeError):
        return assertz_call(False, _error_msg, _error_code, _status_code, reply=reply)


def assertz_phone(_element, key=None, _error_code=INVALID_TYPE_ERROR_CODE, _status_code=DEFAULT_STATUS_CODE, reply=False):
    return assertz_regex(PHONE_REGEX, "Invalid phone", _element, key, _error_code, _status_code, reply=reply)

def assertz_intersects(x, y, _error_code=INVALID_TYPE_ERROR_CODE, _status_code=DEFAULT_STATUS_CODE, reply=False):
    _expression = set(x).intersection(y)

    return assertz_call(_expression, f"No intersection between {x} and {y}", _error_code, _status_code, reply=reply)


def assertz_unauthorized(_expression, _error_msg, _error_code=INVALID_TYPE_ERROR_CODE, reply=False):
    return assertz_call(_expression, _error_msg, _error_code, status_codes.unauthorized, reply=reply)


def assertz_valid_values(_expression, _error_msg, _error_code=INVALID_TYPE_ERROR_CODE, _status_code=DEFAULT_STATUS_CODE, reply=False):
    return assertz_call(_expression, _error_msg, _error_code, _status_code, reply=reply)


def assertz_mandatory_reply(_element, key, _error_code, _status_code):
    return assertz_mandatory(_element, key, _error_code, _status_code, reply=True)

def assertz_string_reply(_element, key, _error_code, _status_code):
    return assertz_string(_element, key, _error_code, _status_code, reply=True)

def assertz_integer_reply(_element, key, _error_code, _status_code):
    return assertz_integer(_element, key, _error_code, _status_code, reply=True)

def assertz_float_reply(_element, key, _error_code, _status_code):
    return assertz_float(_element, key, _error_code, _status_code, reply=True)

def assertz_timestamp_reply(_element, key, _error_code, _status_code):
    return assertz_timestamp(_element, key, _error_code, _status_code, reply=True)

def assertz_boolean_reply(_element, key, _error_code, _status_code):
    return assertz_boolean(_element, key, _error_code, _status_code, reply=True)

def assertz_complex_reply(_element, key, _error_code, _status_code):
    return assertz_complex(_element, key, _error_code, _status_code, reply=True)

def assertz_dict_reply(_element, key, _error_code, _status_code):
    return assertz_dict(_element, key, _error_code, _status_code, reply=True)

def assertz_json_reply(_element, key, _error_code, _status_code):
    return assertz_json(_element, key, _error_code, _status_code, reply=True)

def assertz_array_reply(_element, key, _error_code, _status_code):
    return assertz_array(_element, key, _error_code, _status_code, reply=True)

def assertz_uuid_reply(_element, key, _error_code, _status_code):
    return assertz_uuid(_element, key, _error_code, _status_code, reply=True)

def assertz_utf8_reply(_element, key, _error_code, _status_code):
    return assertz_utf8(_element, key, _error_code, _status_code, reply=True)

def assertz_ascii_reply(_element, key, _error_code, _status_code):
    return assertz_ascii(_element, key, _error_code, _status_code, reply=True)

def assertz_hash_reply(_element, key, _error_code, _status_code):
    return assertz_hash(_element, key, _error_code, _status_code, reply=True)

def assertz_token_reply(_element, key, _error_code, _status_code):
    return assertz_token(_element, key, _error_code, _status_code, reply=True)

def assertz_uri_reply(_element, key, _error_code, _status_code):
    return assertz_uri(_element, key, _error_code, _status_code, reply=True)

def assertz_email_reply(_element, key, _error_code, _status_code):
    return assertz_email(_element, key, _error_code, _status_code, reply=True)

def assertz_location_reply(_element, key, _error_code, _status_code):
    return assertz_location(_element, key, _error_code, _status_code, reply=True)

def assertz_phone_reply(_element, key, _error_code, _status_code):
    return assertz_phone(_element, key, _error_code, _status_code, reply=True)

def assertz_intersects_reply(_element, key, _error_code, _status_code):
    return assertz_intersects(_element, key, _error_code, _status_code, reply=True)

def assertz_unauthorized_reply(_element, key, _error_code):
    return assertz_unauthorized(_element, key, _error_code, reply=True)

def assertz_valid_values_reply(_element, key, _error_code, _status_code):
    return assertz_valid_values(_element, key, _error_code, _status_code, reply=True)


