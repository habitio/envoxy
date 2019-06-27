import requests
from .utils.logs import Log

def authenticate(credentials):

    auth_url = credentials.get('server')
    data = {
        'client_id': credentials.get('client_id'),
        'client_secret': credentials.get('client_secret'),
        'response_type': credentials.get('response_type'),
        'scope': credentials.get('scope'),
        'state': 'active'
    }

    if not '' in data and auth_url:
        resp = requests.post(auth_url, data=data)

        if resp.status_code == requests.codes.ok:
            return resp.json()
        else:
            Log.error("Authorization Error: {}".format(resp.json()))

    Log.emergency("Authorization data incomplete")




