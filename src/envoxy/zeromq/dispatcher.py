import json
import uuid

import zmq

from ..constants import Performative, SERVER_NAME, ZEROMQ_POLLIN_TIMEOUT
from ..utils.config import Config
from ..utils.datetime import Now
from ..utils.logs import Log
from ..utils.singleton import Singleton


class ZMQ(Singleton):

    CACHE = {}

    _instances = {}
    _context = zmq.Context()
    _poller = zmq.Poller()

    def __init__(self):

        self._server_confs = Config.get('zmq_servers')

        if not self._server_confs:
            raise Exception('Error to find ZMQ Servers config')

        for _server_key in self._server_confs.keys():

            _conf = self._server_confs[_server_key]
            _socket = self._context.socket(zmq.REQ)
            _socket.setsockopt(zmq.LINGER, 0)

            self._instances[_server_key] = {
                'server_key': _server_key,
                'conf': _conf,
                'auto_discovery': _conf.get('auto_discovery', {}),
                'socket': _socket,
                'url': 'tcp://{}'.format(_conf.get('host'))
            }

            self.connect(self._instances[_server_key])

    def connect(self, instance):

        _port_range = []

        if instance['auto_discovery']: _port_range = self.find_ports(instance['server_key'],
                                                                     instance['auto_discovery'].get('file'))

        if not _port_range: _port_range = self.get_port_range(instance['conf'])

        for _port in _port_range:

            try:

                Log.info(f"Connecting {instance['url']}:{_port}")

                instance['socket'].connect('{}:{}'.format(instance['url'], _port))

                if instance['socket'].closed():
                    instance['socket'].disconnect('{}:{}'.format(instance['url'], _port))
                else:
                    Log.trace('>>> Successfully connected to ZEROMQ machine: {}'.format(
                        '{}:{}'.format(instance['url'], _port)))

            except:

                pass

        # use poll for timeouts:
        self._poller.register(instance['socket'], zmq.POLLIN)

    def send_and_recv(self, server_key, message):

        _response = None
        _instance = self._instances[server_key]

        try:
            _instance['socket'].send_string('', zmq.SNDMORE)
            _instance['socket'].send_string(json.dumps(message))

            socks = dict(self._poller.poll(ZEROMQ_POLLIN_TIMEOUT))

            if _instance['socket'] in socks:
                try:
                    _instance['socket'].recv() # discard delimiter
                    _response = json.loads(_instance['socket'].recv()) # actual message
                except IOError:
                    Log.error('ZMQ::recv : Could not connect to ZeroMQ machine: {}'.format(_instance['url']))
            else:
                Log.error('ZMQ::poller : Machine did not respond: {}'.format(_instance['url']))
                self._poller.register(_instance['socket'], zmq.POLLIN)
                self.connect(_instance)
    
        except Exception as e:
            Log.error('ZMQ::send : It is not possible to send message using the ZMQ server "{}". Error: {}'.format(
                                                                                                _instance['url'], e))

        return _response

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
