import json
import decimal

class EnvoxyJsonEncoder(json.JSONEncoder):
    
    def default(self, o):
        
        if isinstance(o, decimal.Decimal):
            return float(o)
        
        return super(EnvoxyJsonEncoder, self).default(o)