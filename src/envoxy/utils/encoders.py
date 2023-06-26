import orjson
import decimal
import datetime

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