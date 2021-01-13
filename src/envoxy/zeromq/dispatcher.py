import asyncio
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import zmq

from ..asserts import *
from ..constants import Performative, SERVER_NAME, ZEROMQ_POLLIN_TIMEOUT, ZEROMQ_POLLER_RETRIES, ZEROMQ_CONTEXT, \
    ZEROMQ_RETRY_TIMEOUT, ZEROMQ_MAX_WORKERS
from ..exceptions import ValidationException
from ..utils.config import Config
from ..utils.datetime import Now
from ..utils.logs import Log
from ..utils.singleton import Singleton

from ..cache import Cache


class NoSocketException(Exception):
    pass


class ZMQException(Exception):
    pass

class ZMQ(Singleton):

    _cache = None

    _instances = {}

    _workers = {}

    _available_workers = []

    _executor = None

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

        # Cached Routes
        if Config.get('cache'):
            _cache_instance = Cache()
            self._cache = _cache_instance.get_backend()
            
        for i in range(ZEROMQ_MAX_WORKERS):
            self.add_worker(f'zmqc-poller-{i}')

        self._executor = ThreadPoolExecutor(max_workers=ZEROMQ_MAX_WORKERS, thread_name_prefix='zmqc-worker')

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

    def remove_header(self, response, header):

        if 'headers' in response and header in response['headers']:
            response['headers'].pop(header, None)

    def remove_keys(self, response, keys):

        for key in keys:
            if key in response:
                response.pop(key, None)
    
    def send_and_recv_future(self, server_key, message):
        return self._executor.submit(self.send_and_recv, server_key, message)

    def send_and_recv(self, server_key, message):

        if Log.is_gte_log_level(Log.DEBUG):
            _start = time.time()
        
        _response = None
        _instance = self._instances[server_key]

        _is_in_cached_routes = None

        if self._cache:

            if _instance['conf'].get('cached_routes') and (
                    'X-No-Cache' not in message.get('headers', {}).keys() or message.get('headers', {}).get('X-No-Cache') == False):

                _cached_routes = _instance['conf']['cached_routes']

                _cached_key = f"{message['performative']}:{'/'.join(message['resource'].split('/')[:4])}"

                _is_in_cached_routes = _cached_routes.get(_cached_key)

                if _is_in_cached_routes:
                    
                    _cached_response = self._cache.get(
                        message['resource'], 
                        message['performative'], 
                        message.get('params')
                    )

                    if _cached_response:
                        
                        if Log.is_gte_log_level(Log.DEBUG):
                            
                            Log.debug(f">>> ZMQ::cache::get::cached: {message['resource']} :: {message['performative']} :: {message.get('params')}")

                            _duration = time.time() - _start
                                
                            Log.debug(f">>> ZMQ::send_and_recv::time:: {_instance['url']} :: {_duration} :: {message} ")
                        
                        return _cached_response

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

                            if self._cache and _is_in_cached_routes:

                                try:

                                    self._cache.set(
                                        message['resource'], 
                                        message['performative'], 
                                        message.get('params'), 
                                        _response, 
                                        int(_is_in_cached_routes.get('ttl', 3600))
                                    )

                                    if Log.is_gte_log_level(Log.DEBUG):
                                        Log.debug(f">>> ZMQ::cache::set: {message['resource']} :: {message['performative']} :: {message.get('params')}")

                                except Exception as e:
                                    
                                    Log.error(f"ZMQ::cache::set::Error: {e}")
                            
                            if Log.is_gte_log_level(Log.DEBUG):

                                _duration = time.time() - _start
                                
                                Log.debug(f">>> ZMQ::send_and_recv::time:: {_instance['url']} :: {_duration} :: {message} ")

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
    def bulk_requests(request_list):

        _loop = asyncio.get_event_loop()

        _requests = []
        
        for _request in request_list:

            assertz_mandatory(_request, 'server_key')
            assertz_string(_request, 'server_key')
            
            assertz_mandatory(_request, 'performative')
            assertz_integer(_request, 'performative')
            
            assertz_mandatory(_request, 'url')
            assertz_uri(_request, 'url')

            _message = {
                'performative': _request['performative'],
                'resource': _request['url'],
                'headers': Dispatcher.generate_headers(),
                'params': _request.get('params'),
                'payload': _request.get('payload')
            }

            if 'headers' in _request and _request.get('headers'):
                _message['headers'].update(dict(_request['headers']))

            _requests.append((_request['server_key'], _message))
        
        if _requests:

            _executor = ZMQ.instance()._executor
            _func = ZMQ.instance().send_and_recv
                
            _futures = [
                _loop.run_in_executor(_executor, _func, _server_key, _message) 
                for _server_key, _message in _requests
            ]

            return _loop.run_until_complete(asyncio.gather(*_futures)) if _futures else []
        
        return []
        
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
