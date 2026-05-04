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


def _convert_large_integers(obj):
    """Recursively convert integers outside orjson's 64-bit range to strings."""
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

    # datetime before date — datetime is a subclass of date.
    # Called by orjson because we use OPT_PASSTHROUGH_DATETIME, which disables
    # orjson's native datetime serialisation and routes all datetime/date objects
    # here so we can emit the platform UTC format.
    if isinstance(obj, datetime.datetime):
        return _fmt_datetime(obj)

    if isinstance(obj, datetime.date):
        return obj.isoformat()

    # Handle dict views (dict_keys, dict_values, dict_items) that orjson can't serialize natively.
    if isinstance(obj, MappingView):
        return list(obj)

    raise TypeError


# OPT_PASSTHROUGH_DATETIME disables orjson's native datetime serialisation,
# routing datetime/date objects through envoxy_json_encode_default instead.
# This lets us emit the platform UTC format without a pre-processing tree walk.
_ORJSON_OPTS = orjson.OPT_PASSTHROUGH_DATETIME


def envoxy_json_dumps(obj):
    """
    Serialize object to JSON bytes using orjson.

    datetime/date objects are handled by envoxy_json_encode_default via
    OPT_PASSTHROUGH_DATETIME — no pre-processing tree walk needed.

    Large integers (outside orjson's 64-bit range) are handled on the slow
    path: first attempt raises TypeError, then we pre-process and retry.
    """
    try:
        return orjson.dumps(obj, default=envoxy_json_encode_default, option=_ORJSON_OPTS)
    except TypeError as e:
        if "Integer exceeds 64-bit range" in str(e):
            return orjson.dumps(_convert_large_integers(obj), default=envoxy_json_encode_default, option=_ORJSON_OPTS)
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
