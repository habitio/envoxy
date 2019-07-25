import json
import decimal
import datetime

class EnvoxyJsonEncoder(json.JSONEncoder):
    
    def default(self, o):
        
        if isinstance(o, decimal.Decimal):
            return float(o)

        if isinstance(o, (datetime.date, datetime.datetime)):
            return o.isoformat()
        
        return super(EnvoxyJsonEncoder, self).default(o)