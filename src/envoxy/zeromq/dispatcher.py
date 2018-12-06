import zmq

from ..utils.config import Config
from ..utils.logs import Log
from ..utils.singleton import Singleton

from ..utils.datetime import Now

from ..constants import Performative, SERVER_NAME, ZEROMQ_POLLIN_TIMEOUT

import datetime
import uuid
import json

class ZMQ(Singleton):

    _instances = {}
    _context = zmq.Context()

    def __init__(self):

        self._server_confs = Config.get('zmq_servers')

        if not self._server_confs:
            raise Exception('Error to find ZMQ Servers config')

        for _server_key in self._server_confs.keys():

            _conf = self._server_confs[_server_key]
            _socket = self._context.socket(zmq.REQ)
            _socket.setsockopt(zmq.LINGER, 0)

            self._instances[_server_key] = {
                'conf': _conf,
                'socket': _socket,
                'url': 'tcp://{}'.format(_conf.get('host'))
            }

            if ',' in _conf.get('port'):
                _port_parts = _conf.get('port').split(',')
            else:
                _port_parts = [_conf.get('port')]

            for _port_part in _port_part:

                if ':' in _port_part:
                    _port_range = _port_part.split(':')[:2]

                    _port_range = range(int(_port_range[0]), int(_port_range[1]))
                else:
                    _port_range = [_port_part]

                for _port in _port_range:

                    self._instances[_server_key]['socket'].connect('{}:{}'.format(self._instances[_server_key]['url'], _port))

                    Log.trace('>>> Successfully connected to ZEROMQ machine: {}'.format('{}:{}'.format(self._instances[_server_key]['url'], _port)))

    def send_and_recv(self, _server_key, _message):

        _response = None
        _instance = self._instances[_server_key]

        try:
            _instance['socket'].send_string('', zmq.SNDMORE)
            _instance['socket'].send_string(json.dumps(_message))

            # use poll for timeouts:
            poller = zmq.Poller()
            poller.register(_instance['socket'], zmq.POLLIN)

            socks = dict(poller.poll(ZEROMQ_POLLIN_TIMEOUT))

            if _instance['socket'] in socks:
                try:
                    _instance['socket'].recv()  # discard delimiter
                    _response = json.loads(_instance['socket'].recv())  # actual message
                except IOError:
                    Log.error('Could not connect to machine')
            else:
                Log.error('Machine did not respond')
    
        except Exception as e:
            Log.error('ZMQ::publish : It is not possible to send message using the ZMQ server "{}". Error: {}'.format(_instance['url'], e))
        #finally:
            #_instance['socket'].unbind(_instance['url'])

        return _response
        

class Dispatcher():

    @staticmethod
    def generate_headers(_client_id=None):
        
            _headers = {
                'Accept': 'application/json',
                'Accept-Charset': 'utf-8',
                'Date': Now.api_format(),
                'User-Agent': SERVER_NAME
            }
            
            if _client_id:
                _headers['X-Cid'] = _client_id
            else:
                _headers['X-Cid'] = str(uuid.uuid4())
                    
            return _headers

    @staticmethod
    def get(server_key, url, params=None, payload=None, headers=None):
            
        _message = {
            'resource': url,
            'headers': Dispatcher.generate_headers(),
            'params': params,
            'payload': payload,
            'performative': Performative.GET
        }

        if headers and isinstance(headers, dict):
            _message['headers'].update(headers)
        
        return ZMQ.instance().send_and_recv(server_key, _message)

    @staticmethod
    def post(server_key, url, params=None, payload=None, headers=None):
            
        _message = {
            'resource': url,
            'headers': Dispatcher.generate_headers(),
            'params': params,
            'payload': payload,
            'performative': Performative.POST
        }

        if headers and isinstance(headers, dict):
            _message['headers'].update(headers)
        
        return ZMQ.instance().send_and_recv(server_key, _message)

    @staticmethod
    def put(server_key, url, params=None, payload=None, headers=None):
            
        _message = {
            'resource': url,
            'headers': Dispatcher.generate_headers(),
            'params': params,
            'payload': payload,
            'performative': Performative.PUT
        }

        if headers and isinstance(headers, dict):
            _message['headers'].update(headers)
        
        return ZMQ.instance().send_and_recv(server_key, _message)

    @staticmethod
    def patch(server_key, url, params=None, payload=None, headers=None):
            
        _message = {
            'resource': url,
            'headers': Dispatcher.generate_headers(),
            'params': params,
            'payload': payload,
            'performative': Performative.PATCH
        }
        
        if headers and isinstance(headers, dict):
            _message['headers'].update(headers)
        
        return ZMQ.instance().send_and_recv(server_key, _message)

    @staticmethod
    def delete(server_key, url, params=None, payload=None, headers=None):
            
        _message = {
            'resource': url,
            'headers': Dispatcher.generate_headers(),
            'params': params,
            'payload': payload,
            'performative': Performative.DELETE
        }

        if headers and isinstance(headers, dict):
            _message['headers'].update(headers)
        
        return ZMQ.instance().send_and_recv(server_key, _message)

    @staticmethod
    def head(server_key, url, params=None, payload=None, headers=None):
            
        _message = {
            'resource': url,
            'headers': Dispatcher.generate_headers(),
            'params': params,
            'payload': payload,
            'performative': Performative.HEAD
        }

        if headers and isinstance(headers, dict):
            _message['headers'].update(headers)
        
        return ZMQ.instance().send_and_recv(server_key, _message)
