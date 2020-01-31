import json
import time
import uuid

import zmq

from ..constants import Performative, SERVER_NAME, ZEROMQ_POLLIN_TIMEOUT, ZEROMQ_POLLER_RETRIES, ZEROMQ_CONTEXT, ZEROMQ_RETRY_TIMEOUT, ZEROMQ_MAX_WORKERS
from ..utils.config import Config
from ..utils.datetime import Now
from ..utils.logs import Log
from ..utils.singleton import Singleton

from ..exceptions import ValidationException
import traceback
import time

from concurrent.futures import ThreadPoolExecutor

class NoSocketException(Exception):
    pass


class ZMQException(Exception):
    pass

class ZMQ(Singleton):

    _instances = {}

    _workers = {}

    _available_workers = []

    _async_pool = ThreadPoolExecutor(max_workers=ZEROMQ_MAX_WORKERS, thread_name_prefix='zmqc-worker')

    def __init__(self):

        self._server_confs = Config.get('zmq_servers')

        if not self._server_confs:
            raise Exception('Error to find ZMQ Servers config')

        for _server_key in self._server_confs.keys():

            _conf = self._server_confs[_server_key]

            self._instances[_server_key] = {
                'server_key': _server_key,
                'conf': _conf,
                'url': f"tcp://{_conf.get('host')}:{_conf.get('port')}"
            }

        for i in range(ZEROMQ_MAX_WORKERS):
            self.add_worker(f'zmqc-poller-{i}')

    def add_worker(self, worker_id):
        
        self._workers[worker_id] = {
            'context': zmq.Context(ZEROMQ_CONTEXT),
            'poller': zmq.Poller()
        }

        self.free_worker(worker_id)

    def free_worker(self, worker_id, socket=None):
        
        if socket:
            
            try:
                self._workers[worker_id]['poller'].unregister(socket)
            except KeyError as e:
                pass
            finally:
                socket.close()
        
        self._available_workers.append(worker_id)

    def remove_header(self, _response, header):

        if 'headers' in _response and header in _response['headers']:
            _response['headers'].pop(header, None)

    def remove_keys(self, _response, keys):

        for key in keys:
            if key in _response:
                _response.pop(key, None)
    
    def send_and_recv_future(self, server_key, message):
        return self._async_pool.submit(self.send_and_recv, server_key, message)

    def send_and_recv(self, server_key, message):
        
        _response = None
        _instance = self._instances[server_key]

        try:

            while self._available_workers:

                _worker_id = self._available_workers.pop()

                _worker = self._workers[_worker_id]

                _socket = _worker['context'].socket(zmq.REQ)
                _socket.linger = 0

                _socket.connect(f"{_instance['url']}")

                _worker['poller'].register(_socket, zmq.POLLIN)
            
                _socket.send_multipart([b'', json.dumps(message).encode('utf-8')])
                    
                try:

                    _poller_attempt = 0
                    
                    while True:
                        
                        _socks = dict(_worker['poller'].poll(ZEROMQ_POLLIN_TIMEOUT))

                        if not _socks:

                            _poller_attempt += 1

                            if _poller_attempt <= ZEROMQ_POLLER_RETRIES:
                                continue
                            else:
                                raise NoSocketException(f'No events received in {(ZEROMQ_POLLIN_TIMEOUT/1000)*ZEROMQ_POLLER_RETRIES} secs on {_instance["url"]}')

                        if _socks.get(_socket) == zmq.POLLIN:
                            
                            _recv = _socket.recv_multipart() 
                            _recv.pop(0) # discard delimiter
                            _response = json.loads(_recv.pop(0).decode('utf-8')) # actual message
                            
                            self.remove_header(_response, 'X-Cid')
                            
                            self.remove_keys(_response, ['protocol', 'performative'])

                            self.free_worker(_worker_id, socket=_socket)

                            return _response
                        
                except IOError:
                    
                    Log.error(f"ZMQ::send_and_recv : Could not connect to ZeroMQ machine: {_instance['url']}")

                    self.free_worker(_worker_id, socket=_socket)

                    time.sleep(ZEROMQ_RETRY_TIMEOUT)
    
        except NoSocketException as e:
           
            Log.warning(f"ZMQ::send_and_recv : It is not possible to send message using the ZMQ server \"{_instance['url']}\". Error: {e}")

            self.free_worker(_worker_id, socket=_socket)

            time.sleep(ZEROMQ_RETRY_TIMEOUT)
            
            return self.send_and_recv(server_key, message)

        except Exception as e:
           
            Log.warning(f"ZMQ::send_and_recv : Unexpected error. It is not possible to send message using the ZMQ server \"{_instance['url']}\". Error: {e}")

            self.free_worker(_worker_id, socket=_socket)

            time.sleep(ZEROMQ_RETRY_TIMEOUT)
            
            return self.send_and_recv(server_key, message)

        return _response


class Dispatcher():

    @staticmethod
    def instance():
        return ZMQ.instance()

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

        if headers:
            _message['headers'].update(dict(headers))

        if not future:
            return ZMQ.instance().send_and_recv(server_key, _message)
        else:
            return ZMQ.instance().send_and_recv_future(server_key, _message)

    @staticmethod
    def post(server_key, url, params=None, payload=None, headers=None, future=False):
            
        _message = {
            'resource': url,
            'headers': Dispatcher.generate_headers(),
            'params': params,
            'payload': payload,
            'performative': Performative.POST
        }

        if headers:
            _message['headers'].update(dict(headers))
        
        if not future:
            return ZMQ.instance().send_and_recv(server_key, _message)
        else:
            return ZMQ.instance().send_and_recv_future(server_key, _message)

    @staticmethod
    def put(server_key, url, params=None, payload=None, headers=None, future=False):
            
        _message = {
            'resource': url,
            'headers': Dispatcher.generate_headers(),
            'params': params,
            'payload': payload,
            'performative': Performative.PUT
        }

        if headers:
            _message['headers'].update(dict(headers))
        
        if not future:
            return ZMQ.instance().send_and_recv(server_key, _message)
        else:
            return ZMQ.instance().send_and_recv_future(server_key, _message)

    @staticmethod
    def patch(server_key, url, params=None, payload=None, headers=None, future=False):
            
        _message = {
            'resource': url,
            'headers': Dispatcher.generate_headers(),
            'params': params,
            'payload': payload,
            'performative': Performative.PATCH
        }
        
        if headers:
            _message['headers'].update(dict(headers))
        
        if not future:
            return ZMQ.instance().send_and_recv(server_key, _message)
        else:
            return ZMQ.instance().send_and_recv_future(server_key, _message)

    @staticmethod
    def delete(server_key, url, params=None, payload=None, headers=None, future=False):
            
        _message = {
            'resource': url,
            'headers': Dispatcher.generate_headers(),
            'params': params,
            'payload': payload,
            'performative': Performative.DELETE
        }

        if headers:
            _message['headers'].update(dict(headers))
        
        if not future:
            return ZMQ.instance().send_and_recv(server_key, _message)
        else:
            return ZMQ.instance().send_and_recv_future(server_key, _message)

    @staticmethod
    def head(server_key, url, params=None, payload=None, headers=None, future=False):
            
        _message = {
            'resource': url,
            'headers': Dispatcher.generate_headers(),
            'params': params,
            'payload': payload,
            'performative': Performative.HEAD
        }

        if headers:
            _message['headers'].update(dict(headers))
        
        if not future:
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
