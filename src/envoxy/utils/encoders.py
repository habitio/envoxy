import datetime
import decimal
import json

import orjson


# New encoder for orjson to be used from now on

def envoxy_json_encode_default(obj):

    if isinstance(obj, decimal.Decimal):
        return float(obj)

    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()

    raise TypeError


def envoxy_json_dumps(obj):
    return orjson.dumps(obj, default=envoxy_json_encode_default)


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
