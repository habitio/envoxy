import asyncio
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import zmq

from ..asserts import *
from ..cache import Cache
from ..constants import (SERVER_NAME, ZEROMQ_CONTEXT, ZEROMQ_MAX_WORKERS,
                         ZEROMQ_POLLER_RETRIES, ZEROMQ_POLLIN_TIMEOUT,
                         ZEROMQ_RETRY_TIMEOUT, Performative)
from ..exceptions import ValidationException
from ..utils.config import Config
from ..utils.datetime import Now
from ..utils.logs import Log
from ..utils.singleton import Singleton


class NoSocketException(Exception):
    pass

class ZMQException(Exception):
    pass

class ZMQ(Singleton):

    def __init__(self):

        self._cache = None
        self._instances = {}
        self._workers = {}
        self._available_workers = []
        self._executor = None
        self._lock = threading.Lock()

        try:
            _workers_conf = Config.get('zmq_workers')
            self._thread_poll_executor_max_workers = int(_workers_conf.get('thread_poll_executor_max_workers', ZEROMQ_MAX_WORKERS))
        except Exception:
            self._thread_poll_executor_max_workers = ZEROMQ_MAX_WORKERS

        try:
            _workers_conf = Config.get('zmq_workers')
            self._max_workers = int(_workers_conf.get('context_max_workers', ZEROMQ_MAX_WORKERS))
        except Exception:
            self._max_workers = ZEROMQ_MAX_WORKERS

        Log.info(f'ZMQ: ThreadPoolExecutor max workers: {self._thread_poll_executor_max_workers}')
        Log.info(f'ZMQ: Context max workers: {self._max_workers}')

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
            
        for _i in range(self._max_workers):
            self.add_worker(f'zmqc-poller-{_i}')

        self._executor = ThreadPoolExecutor(max_workers=self._thread_poll_executor_max_workers, thread_name_prefix=f'zmqc-worker')

    def add_worker(self, worker_id):
        
        with self._lock:

            self._workers[worker_id] = {
                'context': zmq.Context(ZEROMQ_CONTEXT),
                'poller': zmq.Poller(),
                'socket': None
            }

        self.free_worker(worker_id)

    def get_or_create_socket(self, server_key, worker_id):

        _worker = self._workers[worker_id]

        _socket = _worker['socket']

        if _socket is None or _socket.closed:

            _poller = _worker['poller']
            
            if _socket is not None:

                try:
                    _poller.unregister(_socket)
                except KeyError:
                    pass
                finally:
                    _socket = None
                
            _socket = _worker['context'].socket(zmq.REQ)
            _socket.connect(self._instances[server_key]['url'])
            _socket.setsockopt(zmq.LINGER, 0)
            _poller.register(_socket, zmq.POLLIN)    

        return _socket

    def free_worker(self, worker_id, close_socket=False):
        
        if close_socket:

            _worker = self._workers[worker_id]
            _socket = _worker['socket']

            if _socket is not None:
                
                try:
                    _worker['poller'].unregister(_socket)
                except KeyError:
                    pass
                finally:
                    _socket.close()
                    _socket = None
        
        with self._lock:    
            self._available_workers.append(worker_id)

    def remove_header(self, response, header):

        if 'headers' in response and header in response['headers']:
            response['headers'].pop(header, None)

    def remove_keys(self, response, keys):

        for _key in keys:
            
            if _key in response:
                response.pop(_key, None)
    
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

            while True:
    
                # Test without any lock
                if not self._available_workers:
                    time.sleep(0.01)
                    continue

                with self._lock:
                    
                    # Check again with lock to make sure that the list is not empty
                    if not self._available_workers:
                        continue

                    _worker_id = self._available_workers.pop()

                _worker = self._workers[_worker_id]

                _socket = self.get_or_create_socket(server_key, _worker_id)
            
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

                            self.free_worker(_worker_id)
                            
                            _recv.pop(0) # discard delimiter
                            _response = json.loads(_recv.pop(0).decode('utf-8')) # actual message
                            
                            self.remove_header(_response, 'X-Cid')
                            
                            self.remove_keys(_response, ['protocol', 'performative'])

                            if self._cache and _is_in_cached_routes:

                                try:

                                    _status_code = int(_response.get('status', 0))

                                    if _status_code >= 200 and _status_code < 300:

                                        _ttl = int(_is_in_cached_routes.get('ttl', 3600))
                                    
                                    else:

                                        _ttl = int(_is_in_cached_routes.get('error_ttl', 60))
                                        
                                        if Log.is_gte_log_level(Log.ERROR):
                                            Log.error(f"ZMQ::cache::set::Error: (state_code: {_status_code}, this cached entry will expire in {_ttl} seconds) {message['resource']} :: {message['performative']} :: {message.get('params')}")

                                    self._cache.set(
                                        message['resource'], 
                                        message['performative'], 
                                        message.get('params'), 
                                        _response, 
                                        _ttl
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

                    self.free_worker(_worker_id, close_socket=True)

                    time.sleep(ZEROMQ_RETRY_TIMEOUT)

                    return self.send_and_recv(server_key, message)
    
        except NoSocketException as e:
           
            Log.warning(f"ZMQ::send_and_recv : It is not possible to send message using the ZMQ server \"{_instance['url']}\". Error: {e}")

            self.free_worker(_worker_id, close_socket=True)

            time.sleep(ZEROMQ_RETRY_TIMEOUT)
            
            return self.send_and_recv(server_key, message)

        except Exception as e:
           
            Log.warning(f"ZMQ::send_and_recv : Unexpected error. It is not possible to send message using the ZMQ server \"{_instance['url']}\". Error: {e}")

            self.free_worker(_worker_id, close_socket=True)

            time.sleep(ZEROMQ_RETRY_TIMEOUT)
            
            return self.send_and_recv(server_key, message)


class Dispatcher():

    @staticmethod
    def initialize():
        try:
            Dispatcher.instance()
        except Exception as e:
            Log.error(f"ZMQ::Dispatcher::initialize::Error: {e}")

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
    def _get_or_create_eventloop():
        
        try:
            
            return asyncio.get_event_loop()

        except RuntimeError as ex:
            
            if "There is no current event loop in thread" in str(ex):
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                return asyncio.get_event_loop()
            
            raise ex
    
    @staticmethod
    def bulk_requests(request_list):

        _loop = Dispatcher._get_or_create_eventloop()

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
