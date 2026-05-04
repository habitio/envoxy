import datetime
import decimal
import json
from collections.abc import MappingView

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


def _fmt_datetime(dt):
    """Format a datetime to platform UTC format: YYYY-MM-DDTHH:MM:SS.fff+0000."""
    dt_utc = dt if dt.tzinfo is None else dt.astimezone(datetime.timezone.utc)
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+0000"


def _convert_datetimes(obj):
    """
    Recursively convert datetime objects to the platform UTC string format.

    orjson serializes datetime natively (bypassing the default function),
    producing inconsistent formats (+00:00, 6 decimal places, non-UTC offsets).
    Pre-processing ensures all datetime values are normalized before orjson
    sees them.

    date objects are left as-is — orjson serializes them as 'YYYY-MM-DD'.
    """
    if isinstance(obj, datetime.datetime):
        return _fmt_datetime(obj)
    elif isinstance(obj, dict):
        return {key: _convert_datetimes(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return type(obj)(_convert_datetimes(item) for item in obj)
    else:
        return obj


def envoxy_json_encode_default(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)

    # datetime before date — datetime is a subclass of date
    if isinstance(obj, datetime.datetime):
        dt_utc = obj if obj.tzinfo is None else obj.astimezone(datetime.timezone.utc)
        return dt_utc.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+0000"

    if isinstance(obj, datetime.date):
        return obj.isoformat()

    # Handle dict views (dict_keys, dict_values, dict_items) that orjson can't serialize natively.
    if isinstance(obj, MappingView):
        return list(obj)

    raise TypeError


def envoxy_json_dumps(obj):
    """
    Serialize object to JSON bytes using orjson.

    orjson handles datetime natively (bypassing the default function), so we
    pre-process the object tree to normalize all datetime values to the platform
    UTC format (YYYY-MM-DDTHH:MM:SS.fff+0000) before serialization.

    Also handles large integers (exceeding 64-bit range) by converting them to
    strings on TypeError, using a try-fast-path to minimize overhead.
    """
    obj = _convert_datetimes(obj)
    try:
        return orjson.dumps(obj, default=envoxy_json_encode_default)
    except TypeError as e:
        if "Integer exceeds 64-bit range" in str(e):
            obj = _convert_large_integers(obj)
            return orjson.dumps(obj, default=envoxy_json_encode_default)
        raise


def envoxy_json_loads(obj):
    return orjson.loads(obj)


# Old encoder for json to keep compatibility


class EnvoxyJsonEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)

        # datetime before date — datetime is a subclass of date
        if isinstance(o, datetime.datetime):
            dt_utc = o if o.tzinfo is None else o.astimezone(datetime.timezone.utc)
            return dt_utc.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+0000"

        if isinstance(o, datetime.date):
            return o.isoformat()

        return super(EnvoxyJsonEncoder, self).default(o)
