import json
import uuid

import zmq

from ..constants import Performative, SERVER_NAME, ZEROMQ_POLLIN_TIMEOUT, ZEROMQ_REQUEST_RETRIES, ZEROMQ_CONTEXT, ZEROMQ_RETRY_TIMEOUT
from ..utils.config import Config
from ..utils.datetime import Now
from ..utils.logs import Log
from ..utils.singleton import Singleton

from ..exceptions import ValidationException
import traceback
import time

from queue import Queue

from concurrent.futures import ThreadPoolExecutor

class NoSocketException(Exception):
    pass


class ZMQException(Exception):
    pass

class ZMQ(Singleton):

    CACHE = {}

    _instances = {}

    _pollers = {
        ''
    }

    _async_pool = ThreadPoolExecutor(max_workers=50)

    def __init__(self):

        self._server_confs = Config.get('zmq_servers')

        if not self._server_confs:
            raise Exception('Error to find ZMQ Servers config')

        for _server_key in self._server_confs.keys():

            _conf = self._server_confs[_server_key]

            self._instances[_server_key] = {
                'server_key': _server_key,
                'conf': _conf,
                'auto_discovery': _conf.get('auto_discovery', {}),
                'url': f"tcp://{_conf.get('host')}:{_conf.get('port')",
                'retries_left': ZEROMQ_REQUEST_RETRIES
            }

    def worker(self, server_key, message):
        
        while True:
            task = self._queue.get()
            response = self._send_and_recv(server_key, message)
            self._queue.put(response)
            self._queue.task_done()

    def send_and_recv_future(self, message):
        return self.send_and_recv_future('muzzley-platform', message)
    
    def send_and_recv_future(self, server_key, message):
        return self._async_pool.submit(self._send_and_recv, (server_key, message))
    
    def send_and_recv(self, message):
        return self.send_and_recv('muzzley-platform', message)

    def send_and_recv(self, server_key, message):
        
        _response = None
        _instance = self._instances[server_key]

        try:

            while _instance['retries_left']:

                _context = zmq.Context(ZEROMQ_CONTEXT)
                _zmq_poller = zmq.Poller()

                _socket = _context.socket(zmq.REQ)
                _socket.linger = 0

                _socket.connect(f"{instance['url']}")

                self._poller.register(_socket, zmq.POLLIN)
            
                _instance['socket'].send_multiparts([b'', json.dumps(message).encode('utf-8'))
                    
                try:
                    
                    while True:
                        
                        _socks = dict(self._poller.poll(ZEROMQ_POLLIN_TIMEOUT))

                        if not _socks:
                            raise NoSocketException(f'No events received in {ZEROMQ_POLLIN_TIMEOUT/1000} secs on {_instance["url"]}')

                        if _socks.get(_socket) == zmq.POLLIN:

                            _socket = _socks[_socket]
                            
                            _recv = _socket.recv_multiparts() 
                            _recv.pop(0) # discard delimiter
                            _response = _recv.pop(0) # actual message
                            
                            _response = self._remove_header(_response, 'X-Cid')
                            
                            self._remove_keys(_response, ['protocol', 'performative', 'resource'])

                            _instance['retries_left'] = ZEROMQ_REQUEST_RETRIES

                            _socket.close()
                            _context.term()

                            return _response
                        
                except IOError:
                    
                    Log.error(f"ZMQ::send_and_recv : Could not connect to ZeroMQ machine: {_instance['url']}")

                    break
    
        except NoSocketException as e:
           
            Log.warning(f"ZMQ::send_and_recv : It is not possible to send message using the ZMQ server \"{_instance['url']}\". Error: {e}")
            
            return self.send_and_recv(server_key, message)

        if _instance['retries_left'] == 0: 
            _instance['retries_left'] = ZEROMQ_REQUEST_RETRIES

        return _response

    ########## helpers ##########

    def port_range(self, instance):

        _port_range = []

        if instance['auto_discovery']:
            _port_range = self.find_ports(instance['server_key'], instance['auto_discovery'].get('file'))

        if not _port_range:
            _port_range = self.get_port_range(instance['conf'])

        return _port_range

    def find_ports(self, server_key, file_path):

        _port_range = []

        try:

            with open(file_path) as ports_file:
                lines = ports_file.readlines()
                services = list(filter(lambda x: x.find(server_key) != -1, lines))

                Log.notice(f"{len(services)} entries found for {server_key}")

                for service in services:
                    try:
                        port = service.split()[1].split(':')[1]  # PID/SERVICE_NAME IP_ADDR:UDP_PORT
                        _port_range.append(int(port.strip()))
                    except ValueError:
                        continue
        except OSError:
            Log.warning('Error finding ports')

        return _port_range

    def get_port_range(self, _conf):
        _port_range = []

        if ',' in _conf.get('port'):
            _port_parts = _conf.get('port').split(',')
        else:
            _port_parts = [_conf.get('port')]

        for _port_part in _port_parts:

            if ':' in _port_part:
                _port_range = _port_part.split(':')[:2]

                _port_range = range(int(_port_range[0]), int(_port_range[1]))
            else:
                _port_range = [_port_part]

        return _port_range

    def _remove_header(self, _response, header):

        if 'headers' in _response and header in _response['headers']:
            response = _response['headers'].pop(header)

        return _response

    def _remove_keys(self, _response, keys):

        for key in keys:
            if 'key' in _response:
                _response.pop(key, None)

class Dispatcher():

    @staticmethod
    def generate_headers(client_id=None):
        
            _headers = {
                'Accept': 'application/json',
                'Accept-Charset': 'utf-8',
                'Date': Now.api_format(),
                'User-Agent': SERVER_NAME
            }
            
            if client_id:
                _headers['X-Cid'] = client_id
            else:
                _headers['X-Cid'] = str(uuid.uuid4())
                    
            return _headers

    @staticmethod
    def get(server_key, url, params=None, payload=None, headers=None, future=False):

        _message = {
            'resource': url,
            'headers': Dispatcher.generate_headers(),
            'params': params,
            'payload': payload,
            'performative': Performative.GET
        }

        if headers and isinstance(headers, dict):
            _message['headers'].update(headers)

        if future:
            return ZMQ.instance().send_and_recv(server_key, _message)
        else:
            return ZMQ.instance().send_and_recv_future(server_key, _message)

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
        
        if future:
            return ZMQ.instance().send_and_recv(server_key, _message)
        else:
            return ZMQ.instance().send_and_recv_future(server_key, _message)

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
        
        if future:
            return ZMQ.instance().send_and_recv(server_key, _message)
        else:
            return ZMQ.instance().send_and_recv_future(server_key, _message)

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
        
        if future:
            return ZMQ.instance().send_and_recv(server_key, _message)
        else:
            return ZMQ.instance().send_and_recv_future(server_key, _message)

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
        
        if future:
            return ZMQ.instance().send_and_recv(server_key, _message)
        else:
            return ZMQ.instance().send_and_recv_future(server_key, _message)

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
        
        if future:
            return ZMQ.instance().send_and_recv(server_key, _message)
        else:
            return ZMQ.instance().send_and_recv_future(server_key, _message)

    @staticmethod
    def validate_response(response):

        if response is None:
            raise ValidationException("Service Unavailable", code=0, status=503)

        if response.get('status') not in [200, 201] and ('elements' not in response.get('payload') or '_id' not in response.get('payload')):
            msg = response.get('payload', {}).get('text', f"Resource error, code: {response['status']}, {response['resource']}")
            code = response.get('payload', {}).get('code', 0)
            raise ValidationException(msg, code=code, status=str(response.get('status')))

        return response
