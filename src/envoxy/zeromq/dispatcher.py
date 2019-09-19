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

class NoSocketException(Exception):
    pass


class ZMQException(Exception):
    pass

class ZMQ(Singleton):

    CACHE = {}

    _instances = {}
    _context = zmq.Context(ZEROMQ_CONTEXT)
    _poller = zmq.Poller()

    def __init__(self):

        self._server_confs = Config.get('zmq_servers')

        if not self._server_confs:
            raise Exception('Error to find ZMQ Servers config')

        for _server_key in self._server_confs.keys():

            _conf = self._server_confs[_server_key]
            _socket = self._context.socket(zmq.REQ)

            self._instances[_server_key] = {
                'server_key': _server_key,
                'conf': _conf,
                'auto_discovery': _conf.get('auto_discovery', {}),
                'socket': _socket,
                'url': f"tcp://{_conf.get('host')}",
                'retries_left': ZEROMQ_REQUEST_RETRIES
            }

            self.connect(self._instances[_server_key])

    def connect(self, instance):

        _connected = []

        for _port in self.port_range(instance):

            try:

                _url =  f"{instance['url']}:{_port}"
                Log.trace(f"Connecting {_url} {instance['socket']} {instance['socket'].closed}")
                instance['socket'].connect(_url)

                if not instance['socket'].closed:
                    _connected.append(_url)

            except Exception as e:
                Log.error(f'>>Exception during CONNECT {e}')

        if len(_connected) > 0:
            Log.trace(f">>> Successfully connected to ZEROMQ machine: {', '.join(_connected)}")
            Log.trace(f">>Registering new socket {instance['socket']}")
            self._poller.register(instance['socket'], zmq.POLLIN)

            return True
        
    def disconnect(self, instance):

        try:
            
            Log.trace(f"Disconnecting {instance['socket']}")
            instance['socket'].close()

            if instance['socket'].closed:
                Log.trace('>>> Successfully disconnected to ZEROMQ machine: {}'.format(f"{instance['socket']}"))
                self._poller.unregister(instance['socket'])

                return True

        except Exception as e:
            Log.error(f'>>Exception during DISCONNECT {e}')
            return False

    def restore_socket_connection(self, server_key, force_new_socket=False):

        _restore_successful = True

        try:

            if self._instances[server_key]['retries_left'] > 0:

                # Socket is confused. Close and remove it.
                _result = self.disconnect(self._instances[server_key])

                self._instances[server_key]['retries_left'] -= 1

                Log.warning(f"ZMQ::restore_socket_connection : Reconnecting and resending: {self._instances[server_key]['url']} retry #{self._instances[server_key]['retries_left']}")

                if force_new_socket:  # Create new connection

                    del self._instances[server_key]['socket']

                    _socket = self._context.socket(zmq.REQ)

                    self._instances[server_key]['socket'] = _socket

                self.connect(self._instances[server_key])

                if dict(self._poller.poll(ZEROMQ_RETRY_TIMEOUT)):
                    _restore_successful = True

        except Exception as e:
            Log.error(f'>>Exception during RESTORE {e}')

        if self._instances[server_key]['retries_left'] == 0 and not _restore_successful:
            Log.alert(f"ZMQ::send_and_recv : Server seems to be offline, abandoning: {self._instances[server_key]['url']}")
            self._instances[server_key]['retries_left'] = ZEROMQ_REQUEST_RETRIES


        return _restore_successful == True

    def send_and_recv(self, server_key, message):
        _response = None
        _instance = self._instances[server_key]

        try:

            while _instance['retries_left']:
            
                _instance['socket'].send_string('', zmq.SNDMORE)
                _instance['socket'].send_string(json.dumps(message))
                    
                try:
                    
                    while True:
                        
                        _socks = dict(self._poller.poll(ZEROMQ_POLLIN_TIMEOUT))

                        if not _socks:
                            raise NoSocketException(f'No events received in {ZEROMQ_POLLIN_TIMEOUT/1000} secs on {_instance["url"]}')

                        if _socks.get(_instance['socket']) == zmq.POLLIN:
                            
                            _instance['socket'].recv() # discard delimiter
                            _response = _instance['socket'].recv_json() # actual message
                            _response = self._remove_header(_response, 'X-Cid')

                            _instance['retries_left'] = ZEROMQ_REQUEST_RETRIES

                            return _response

                        else:

                            if not self.restore_socket_connection(server_key):
                                break
                        
                except IOError:
                    
                    Log.error(f"ZMQ::send_and_recv : Could not connect to ZeroMQ machine: {_instance['url']}")

                    if not self.restore_socket_connection(server_key, force_new_socket=True):
                        break
    
        except NoSocketException as e:
            Log.warning(f"ZMQ::send_and_recv : It is not possible to send message using the ZMQ server \"{_instance['url']}\". Error: {e}")
            if self.restore_socket_connection(server_key, force_new_socket=True):
                return self.send_and_recv(server_key, message)

        if _instance['retries_left'] == 0: _instance['retries_left'] = ZEROMQ_REQUEST_RETRIES

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

    @staticmethod
    def validate_response(response):

        if response is None:
            raise ValidationException("Service Unavailable", code=0, status=503)

        if response.get('status') not in [200, 201] and ('elements' not in response.get('payload') or '_id' not in response.get('payload')):
            msg = response.get('payload', {}).get('text', f"Resource error, code: {response['status']}, {response['resource']}")
            code = response.get('payload', {}).get('code', 0)
            raise ValidationException(msg, code=code, status=str(response.get('status')))

        return response
