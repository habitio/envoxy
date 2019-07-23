import json
import uuid

import zmq

from ..constants import Performative, SERVER_NAME, ZEROMQ_POLLIN_TIMEOUT, ZEROMQ_REQUEST_RETRIES, ZEROMQ_CONTEXT
from ..utils.config import Config
from ..utils.datetime import Now
from ..utils.logs import Log
from ..utils.singleton import Singleton


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
            #_socket.setsockopt(zmq.LINGER, 0)

            self._instances[_server_key] = {
                'server_key': _server_key,
                'conf': _conf,
                'auto_discovery': _conf.get('auto_discovery', {}),
                'socket': _socket,
                'url': f"tcp://{_conf.get('host')}",
                'retries_left': ZEROMQ_REQUEST_RETRIES
            }

            self.connect(self._instances[_server_key])

    
    def port_range(self, instance):

        _port_range = []

        if instance['auto_discovery']: 
            _port_range = self.find_ports(instance['server_key'], instance['auto_discovery'].get('file'))

        if not _port_range: 
            _port_range = self.get_port_range(instance['conf'])

        return _port_range

    def connect(self, instance):

        for _port in self.port_range(instance):

            try:

                Log.info(f"Connecting {instance['url']}:{_port}")

                instance['socket'].connect(f"{instance['url']}:{_port}")

                if not instance['socket'].closed():
                    Log.trace('>>> Successfully connected to ZEROMQ machine: {}'.format(f"{instance['url']}:{_port}"))
                else:
                    instance['socket'].disconnect(f"{instance['url']}:{_port}")

            except:

                pass

        self._poller.register(instance['socket'], zmq.POLLIN)

    def disconnect(self, instance):

        for _port in self.port_range(instance):

            try:

                Log.info(f"Disconnecting {instance['url']}:{_port}")

                instance['socket'].close(f"{instance['url']}:{_port}")

                if instance['socket'].closed():
                    Log.trace('>>> Successfully disconnected to ZEROMQ machine: {}'.format(f"{instance['url']}:{_port}"))

            except:

                pass

        self._poller.unregister(instance['socket'])

    def restore_socket_connection(self, instance, force_new_socket=False):

        # Socket is confused. Close and remove it.
        self.disconnect(instance)
        
        instance['retries_left'] -= 1

        if instance['retries_left'] == 0:
            Log.error(f"ZMQ::send_and_recv : Server seems to be offline, abandoning: {instance['url']}")
            return False
        
        Log.error(f"ZMQ::send_and_recv : Reconnecting and resending: {instance['url']}")

        # Create new connection

        if force_new_socket:
            
            del instance['socket']

            _socket = self._context.socket(zmq.REQ)
            #_socket.setsockopt(zmq.LINGER, 0)

            instance['socket'] = _socket

        self.connect(instance)

        return True

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
                        
                        if _socks.get(_instance['socket']) == zmq.POLLIN:
                            
                            _instance['socket'].recv() # discard delimiter
                            _response = _instance['socket'].recv() # actual message
                            
                            try:
                                _response = json.loads(_response)
                                _instance['retries_left'] = ZEROMQ_REQUEST_RETRIES
                                return _response
                            except Exception as e:
                                _response = None
                                Log.error(f"ZMQ::send_and_recv : Malformed reply from server: {_instance['url']}")

                        else:

                            if not self.restore_socket_connection(_instance):
                                break
                        
                except IOError:
                    
                    Log.error(f"ZMQ::send_and_recv : Could not connect to ZeroMQ machine: {_instance['url']}")

                    if not self.restore_socket_connection(_instance, force_new_socket=True):
                        break

    
        except Exception as e:
            
            Log.error(f"ZMQ::send_and_recv : It is not possible to send message using the ZMQ server \"{_instance['url']}\". Error: {e}")

            if not self.restore_socket_connection(_instance, force_new_socket=True):
                return None

            return self.send_and_recv(server_key, message)

        return None

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
