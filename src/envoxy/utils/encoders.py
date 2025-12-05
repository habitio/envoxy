import datetime
import decimal
import json

import orjson


# New encoder for orjson to be used from now on

# Integer boundaries for orjson
# orjson supports unsigned 64-bit for positive values and signed 64-bit for negative
UINT64_MAX = 18446744073709551615  # 2^64 - 1 (max positive)
INT64_MIN = -9223372036854775808  # -2^63 (min negative)


def _convert_large_integers(obj):
    """
    Recursively convert integers exceeding 64-bit range to strings.

    orjson supports: positive integers [0, 2^64-1], negative integers [-2^63, 0].
    This function pre-processes data structures to convert any integers outside
    this range to strings before serialization.

    Optimized to minimize overhead for common cases without large integers.
    """
    if isinstance(obj, int):
        if obj > UINT64_MAX or obj < INT64_MIN:
            return str(obj)
        return obj
    elif isinstance(obj, dict):
        return {key: _convert_large_integers(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return type(obj)(_convert_large_integers(item) for item in obj)
    else:
        return obj


def envoxy_json_encode_default(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)

    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()

    raise TypeError


def envoxy_json_dumps(obj):
    """
    Serialize object to JSON bytes using orjson.

    Automatically handles large integers (exceeding 64-bit range) by converting
    them to strings. Uses a try-fast-path approach: attempts direct serialization
    first, only pre-processing on TypeError to minimize overhead for common cases.
    """
    try:
        # Fast path: try direct serialization (works for 99% of cases)
        return orjson.dumps(obj, default=envoxy_json_encode_default)
    except TypeError as e:
        # Check if it's an integer overflow issue
        if "Integer exceeds 64-bit range" in str(e):
            # Slow path: pre-process to convert large integers to strings
            obj = _convert_large_integers(obj)
            return orjson.dumps(obj, default=envoxy_json_encode_default)
        # Re-raise if it's a different TypeError
        raise


def envoxy_json_loads(obj):
    return orjson.loads(obj)


# Old encoder for json to keep compatibility


class EnvoxyJsonEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)

        if isinstance(o, (datetime.date, datetime.datetime)):
            return o.isoformat()

        return super(EnvoxyJsonEncoder, self).default(o)
