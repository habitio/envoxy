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


def _fmt_datetime(dt):
    """Format a datetime to platform UTC format: YYYY-MM-DDTHH:MM:SS.fff+0000."""
    dt_utc = dt if dt.tzinfo is None else dt.astimezone(datetime.timezone.utc)
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+0000"


def _normalize_obj(obj):
    """
    Single-pass recursive pre-processor for orjson serialization.

    Handles in one traversal:
    - datetime → platform UTC string ('YYYY-MM-DDTHH:MM:SS.fff+0000')
      orjson serializes datetime natively (bypassing default()), producing
      inconsistent formats. Converting to string first ensures correct output.
    - int outside 64-bit range → str
      orjson only supports [−2^63, 2^64−1]; large integers raise TypeError.

    date objects pass through untouched — orjson emits them as 'YYYY-MM-DD'.
    All other scalars (str, float, bool, None, Decimal, etc.) pass through.
    """
    if isinstance(obj, datetime.datetime):
        return _fmt_datetime(obj)
    elif isinstance(obj, int):
        if obj > UINT64_MAX or obj < INT64_MIN:
            return str(obj)
        return obj
    elif isinstance(obj, dict):
        return {key: _normalize_obj(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return type(obj)(_normalize_obj(item) for item in obj)
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

    Pre-processes the object tree with _normalize_obj (single pass) to handle:
    - datetime → platform UTC string (orjson bypasses default() for datetime)
    - int outside 64-bit range → str (orjson raises TypeError for these)
    """
    return orjson.dumps(_normalize_obj(obj), default=envoxy_json_encode_default)


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
