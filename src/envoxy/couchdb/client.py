import requests
import time

from urllib.parse import quote

from ..utils.logs import Log

class Client:

    valid_operators = ['eq', 'gt', 'gte', 'lt', 'lte', 'in']

    def __init__(self, server_conf):

        self._instances = {}

        for _server_key, _conf in server_conf.items():

            self._instances[_server_key] = {
                'server': _server_key,
                'conf': _conf
            }

            self.connect(self._instances[_server_key])

    def connect(self, instance):

        _conf = instance['conf']

        _session = requests.Session()
        
        _session.headers = {
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip, deflate"
        }

        instance['conn'] = _session

        Log.trace('>>> Connected to COUCHDB: {}, {}'.format(instance['server'], _conf['bind']))

    def _get_conn(self, server_key):
        """
        :param server_key: database identifier
        :return: raw requests session instance
        """
        return self._instances.get(server_key, {}).get('conn')

    def _get_selector(self, params):
        
        _selector = {}

        for _key, _value in (params or {}).items():

            try:
                _operator = _key.split('__')[1:].pop()
                
                if _operator in self.valid_operators:
                    _selector[_key] = {
                        '${}'.format(_operator): _value
                    }
                    continue
            except IndexError:
                pass

            _selector[_key] = _value

        return {
            'selector': _selector
        }
    
    def _execute_request(self, session, method, url, data, retries=3, backoff=1):
        
        for _attempt in range(retries):
            
            try:
                
                if Log.is_gte_log_level(Log.DEBUG):
                    Log.debug('CouchDB::execute_request - Request: {} {}'.format(url, data))
                
                _response = session.request(method, url, json=data)
                
                if Log.is_gte_log_level(Log.DEBUG):
                    Log.debug('CouchDB::execute_request - Request took {:.2f} seconds'.format(_response.elapsed.total_seconds()))

                return _response
            
            except requests.RequestException as e:

                Log.error('CouchDB Request failed: {}'.format(e))
                
                if _attempt < retries - 1:
                    Log.warning('CouchDB::execute_request - Retrying in {} seconds... Retries: {}/{}'.format(backoff, _attempt+1, retries))
                    time.sleep(backoff)
                    backoff *= 2  # Exponential backoff
                else:
                    raise

    def base_request(self, db, method, data=None, find=False, uri=None):

        _server_key, _database = db.split('.')
        
        _host = self._instances[_server_key]['conf']['bind']
        _url = '{}/{}'.format(_host, _database)
        
        if uri: 
            _url = f'{_url}/{quote(uri, safe="")}'

        if find: 
            _url = f'{_url}/_find'

        _session = self._get_conn(_server_key)

        if not _session:
            Log.warning('CouchDB::base_request - No session found for server: "{}" to "{}"'.format(_server_key, _url))

        return self._execute_request(_session, method, _url, data) if _session else None

    def find(self, db: str, fields: list, params: dict):
        
        _data = self._get_selector(params)

        _response = self.base_request(db, 'POST', data=_data, find=True)

        try:

            if _response:
            
                if _response.status_code == requests.codes.ok and 'docs' in _response.json():
                    return _response.json()['docs']
                
                Log.warning('CouchDB::find - Different response than expected - status code: {}, content: {}'.format(
                    _response.status_code, 
                    _response.text
                ))
                
                return []
            
            Log.warning('CouchDB::find - Empty response / no session / no connection - DB: {} - Data: {}'.format(db, _data))
        
        except Exception as e:
            Log.error('CouchDB::find - Error parsing response: {}'.format(e))

        return []

    def get(self, id: str, db: str):

        _response = self.base_request(db, 'GET', uri=id)

        try:

            if _response:
                
                if _response.status_code == requests.codes.ok:
                    return _response.json()
                
                Log.warning('CouchDB::get - Different response than expected - status code: {}, content: {}'.format(
                    _response.status_code, 
                    _response.text
                ))
                
                return {}
            
            Log.warning('CouchDB::get - Empty response / no session / no connection- DB: {} - URI/ID: {}'.format(db, id))

        except Exception as e:

            Log.error('CouchDB::get - Error parsing response: {}'.format(e))

        return {}

    def post(self, db: str, payload: dict):

        _response = self.base_request(db, 'POST', data=payload)

        try:

            if _response:
                
                if _response.status_code == requests.codes.created and 'docs' in _response.json():
                    return _response.json()['docs']
                
                Log.warning('CouchDB::post - Different response than expected - status code: {}, content: {}'.format(
                    _response.status_code, 
                    _response.text
                ))

                return _response.json()
            
            Log.warning('CouchDB::post - Empty response / no session / no connection - DB: {} - Payload: {}'.format(db, payload))

        except Exception as e:
                
                Log.error('CouchDB::post - Error parsing response: {}'.format(e))
                
        return {}
