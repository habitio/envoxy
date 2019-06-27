import requests
from ..utils.logs import Log

def authenticate(credentials):

    auth_url = credentials.get("server")
    data = {
        "client_id": credentials.get("client_id"),
        "client_secret": credentials.get("client_secret"),
        "response_type": credentials.get("response_type"),
        "scope": credentials.get("scope"),
        "state": "active"
    }

    if not "" in data.values() and auth_url:
        try:
            resp = requests.get(auth_url, params=data)
            Log.info("Response >> {}".format(resp.status_code))
        except requests.RequestException as e:
            Log.emergency("Error while performing authorization {}".format(e))
            exit(-10)

        if resp.status_code == requests.codes.ok:
            return resp.json()

    Log.emergency("Authorization data incomplete")
    exit(-10)




