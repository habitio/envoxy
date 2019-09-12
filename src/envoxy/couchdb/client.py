import requests
from ..utils.logs import Log
from urllib.parse import quote

class Client:

    valid_operators = ['eq', 'gt', 'gte', 'lt', 'lte', 'in']
    _instances = {}
    __conn = None

    def __init__(self, server_conf):

        for _server_key in server_conf.keys():

            _conf = server_conf[_server_key]
            self._instances[_server_key] = {
                'server': _server_key,
                'conf': _conf
            }

            self.connect(self._instances[_server_key])


    def connect(self, instance):

        conf = instance['conf']

        session = requests.Session()
        session.headers = {
            "Content-Type": "application/json",
            "Encoding": "UTF-8"
        }

        instance['conn'] = session

        Log.trace('>>> Successfully connected to COUCHDB: {}, {}'.format(instance['server'],conf['bind']))

    def _get_conn(self, server_key):
        """
        :param server_key: database identifier
        :return: raw requests session instance
        """
        _instance = self._instances[server_key]
        return _instance['conn']

    def _get_selector(self, params):
        _selector = {}

        if params:

            for key, value in params.items():

                try:
                    operator = key.split('__')[1:].pop()
                    if operator in self.valid_operators:
                        _selector[key] = {
                            '${}'.format(operator): value
                        }
                        continue
                except IndexError:
                    pass

                _selector[key] = value

        return {
            'selector': _selector
        }

    def base_request(self, db, method, data=None, find=False, uri=None):

        db_data = db.split('.')

        server_key = db_data[0]
        database = db_data[1]

        host = self._instances[server_key]['conf']['bind']
        url = '{}/{}'.format(host, database)

        if find: url = f'{url}/_find'
        if uri: url = f'{url}/{uri}'

        session = self._get_conn(server_key)

        try:

            Log.debug('couchdb::{} {}'.format(url, data))
            resp = session.request(method, url, json=data)
            Log.debug(f"request took {resp.elapsed.total_seconds()} seconds")

            return resp

        except requests.RequestException:
            pass

        return None

    def find(self, db: str, fields: list, params: dict):
        data = self._get_selector(params)
        resp = self.base_request(db, 'POST', data=data, find=True)

        if resp.status_code in [ requests.codes.ok ] and 'docs' in resp.json():
            return resp.json()['docs']

        return []

    def get(self, id: str, db: str):

        uri = quote(id, safe='')
        resp = self.base_request(db, 'GET', find=False, uri=uri)

        if resp.status_code in [ requests.codes.ok ]:
            return resp.json()

        return {}

    def post(self, db: str, payload: dict):

        resp = self.base_request(db, 'POST', data=payload)

        if resp.status_code in [ requests.codes.created ] and 'docs' in resp.json():
            return resp.json()['docs']

        return resp.json()
