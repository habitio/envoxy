import asyncio
import queue
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import zmq

from ..asserts import assertz_integer, assertz_mandatory, assertz_string, assertz_uri
from ..cache import Cache
from ..constants import SERVER_NAME, ZEROMQ_CONTEXT, ZEROMQ_MAX_WORKERS, ZEROMQ_POLLER_RETRIES, ZEROMQ_POLLIN_TIMEOUT, ZEROMQ_RETRY_TIMEOUT, Performative
from ..exceptions import ValidationException
from ..utils.config import Config
from ..utils.datetime import Now
from ..utils.logs import Log
from ..utils.singleton import Singleton
from ..utils.encoders import envoxy_json_loads, envoxy_json_dumps


class NoSocketException(Exception):
    pass


class ZMQException(Exception):
    pass


class ZMQ(Singleton):

    _cache = None
    _instances = {}
    _contexts = {}
    _workers = {}
    _available_workers = {}
    _executor = None
    _lock = threading.Lock()

    def __init__(self):

        try:
            _workers_conf = Config.get('zmq_workers')
            self._thread_poll_executor_max_workers = int(_workers_conf.get(
                'thread_poll_executor_max_workers', ZEROMQ_MAX_WORKERS))
        except Exception:
            self._thread_poll_executor_max_workers = ZEROMQ_MAX_WORKERS

        try:
            _workers_conf = Config.get('zmq_workers')
            self._max_workers = int(_workers_conf.get(
                'context_max_workers', ZEROMQ_MAX_WORKERS))
        except Exception:
            self._max_workers = ZEROMQ_MAX_WORKERS

        Log.info(
            f'ZMQ: ThreadPoolExecutor max workers: {self._thread_poll_executor_max_workers}')
        Log.info(f'ZMQ: Context max workers: {self._max_workers}')

        self._server_confs = Config.get('zmq_servers')

        if not self._server_confs:
            raise Exception('Error to find ZMQ Servers config')

        for _server_key in self._server_confs.keys():

            _conf = self._server_confs[_server_key]

            self._contexts[_server_key] = zmq.Context(ZEROMQ_CONTEXT)

            self._instances[_server_key] = {
                'server_key': _server_key,
                'conf': _conf,
                'url': f"tcp://{_conf.get('host')}:{_conf.get('port')}"
            }

            self._available_workers[_server_key] = queue.Queue()

            for _i in range(self._max_workers):
                self.add_worker(_server_key, f'zmqc-poller-{_server_key}-{_i}')

        # Cached Routes
        if Config.get('cache'):
            _cache_instance = Cache()
            self._cache = _cache_instance.get_backend()

        self._executor = ThreadPoolExecutor(
            max_workers=self._thread_poll_executor_max_workers, thread_name_prefix='zmqc-worker')

    def get_available_worker(self, server_key):
        return self._available_workers[server_key].get()

    def add_worker(self, server_key, worker_id):

        with self._lock:

            self._workers[worker_id] = {
                'poller': zmq.Poller(),
                'socket': None
            }

        self.free_worker(server_key, worker_id)

    def get_or_create_socket(self, server_key, worker_id):

        with self._lock:

            _worker = self._workers[worker_id]

            _socket = _worker['socket']

            if _socket is None or _socket.closed:

                _poller = _worker['poller']

                if _socket is not None:

                    try:
                        _poller.unregister(_socket)
                    except Exception:
                        pass

                    try:
                        _socket.close(linger=0)
                    except Exception:
                        pass

                _socket = self._contexts[server_key].socket(zmq.REQ)
                _socket.connect(self._instances[server_key]['url'])
                _socket.setsockopt(zmq.LINGER, 0)
                _poller.register(_socket, zmq.POLLIN)

                _worker['socket'] = _socket

        return _socket
    
    def close_and_unregister_socket(self, worker_id):
        
        with self._lock:
        
            _worker = self._workers[worker_id]
            _socket = _worker['socket']

            if _socket is not None:

                try:
                    _worker['poller'].unregister(_socket)
                except Exception:
                    pass
                
                try:
                    _socket.close(linger=0)
                except Exception:
                    pass
                
                _worker['socket'] = None

    def free_worker(self, server_key, worker_id, close_socket=False):

        if close_socket:
            self.close_and_unregister_socket(worker_id)

        self._available_workers[server_key].put(worker_id)

    def remove_header(self, response, header):

        if 'headers' in response and header in response['headers']:
            response['headers'].pop(header, None)

    def remove_keys(self, response, keys):

        for _key in keys:
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

            _cached_routes = _instance['conf'].get('cached_routes') 

            if _cached_routes:
                
                _message_headers = message.get('headers', {})

                if 'X-No-Cache' not in _message_headers.keys() or _message_headers.get('X-No-Cache') is False:

                    _performative = message['performative']
                    _resource = message['resource']
                    _params = message.get('params')

                    _cached_key = f"{_performative}:{'/'.join(_resource.split('/')[:4])}"

                    _is_in_cached_routes = _cached_routes.get(_cached_key)

                    if _is_in_cached_routes:

                        _cached_response = self._cache.get(
                            _resource,
                            _performative,
                            _params
                        )

                        if _cached_response:

                            if Log.is_gte_log_level(Log.DEBUG):

                                Log.debug(
                                    f">>> ZMQ::cache::get::cached: {_resource} :: {_performative} :: {_params}")

                                _duration = time.time() - _start

                                Log.debug(
                                    f">>> ZMQ::send_and_recv::time:: {_instance['url']} :: {_duration} :: {message} ")

                            return _cached_response

        try:

            while True:

                _worker_id = self.get_available_worker(server_key)

                with self._lock:
                    _worker = self._workers[_worker_id]

                _socket = self.get_or_create_socket(server_key, _worker_id)

                _socket.send_multipart(
                    [b'', envoxy_json_dumps(message)])

                try:

                    _poller_attempt = 0

                    while True:

                        _socks = dict(_worker['poller'].poll(
                            ZEROMQ_POLLIN_TIMEOUT))

                        if not _socks:

                            _poller_attempt += 1

                            if _poller_attempt <= ZEROMQ_POLLER_RETRIES:
                                continue
                            else:
                                raise NoSocketException(
                                    f'No events received in {(ZEROMQ_POLLIN_TIMEOUT/1000)*ZEROMQ_POLLER_RETRIES} secs on {_instance["url"]}')

                        if _socks.get(_socket) == zmq.POLLIN:

                            _recv = _socket.recv_multipart()

                            self.free_worker(server_key, _worker_id)

                            _recv.pop(0)  # discard delimiter
                            _response = envoxy_json_loads(_recv.pop(0))  # actual message

                            self.remove_header(_response, 'X-Cid')

                            self.remove_keys(_response, ['protocol', 'performative'])

                            if self._cache and _is_in_cached_routes:

                                _performative = message['performative']
                                _resource = message['resource']
                                _params = message.get('params')

                                try:

                                    _status_code = int(
                                        _response.get('status', 0))

                                    if _status_code >= 200 and _status_code < 300:

                                        _ttl = int(
                                            _is_in_cached_routes.get('ttl', 3600))

                                    else:

                                        _ttl = int(
                                            _is_in_cached_routes.get('error_ttl', 60))

                                        if Log.is_gte_log_level(Log.ERROR):
                                            Log.error(f"ZMQ::cache::set::Error: "
                                                      f"(state_code: {_status_code}, this cached entry will expire in {_ttl} seconds) "
                                                      f"{_resource} :: {_performative} :: {_params}"
                                                      )

                                    self._cache.set(
                                        _resource,
                                        _performative,
                                        _params,
                                        _response,
                                        _ttl
                                    )

                                    if Log.is_gte_log_level(Log.DEBUG):
                                        Log.debug(
                                            f">>> ZMQ::cache::set: {_resource} :: {_performative} :: {_params}")

                                except Exception as e:

                                    Log.error(f"ZMQ::cache::set::Error: {e}")

                            if Log.is_gte_log_level(Log.DEBUG):

                                _duration = time.time() - _start

                                Log.debug(
                                    f">>> ZMQ::send_and_recv::time:: {_instance['url']} :: {_duration} :: {message} ")

                            return _response

                except IOError:

                    Log.error(
                        f"ZMQ::send_and_recv : Could not connect to ZeroMQ machine: {_instance['url']}")

                    self.free_worker(server_key, _worker_id, close_socket=True)

                    time.sleep(ZEROMQ_RETRY_TIMEOUT)

                    return self.send_and_recv(server_key, message)

        except NoSocketException as e:

            Log.warning(
                f"ZMQ::send_and_recv : It is not possible to send message using the ZMQ server \"{_instance['url']}\". Error: {e}")

            self.free_worker(server_key, _worker_id, close_socket=True)

            time.sleep(ZEROMQ_RETRY_TIMEOUT)

            return self.send_and_recv(server_key, message)

        except Exception as e:

            Log.warning(
                f"ZMQ::send_and_recv : Unexpected error. It is not possible to send message using the ZMQ server \"{_instance['url']}\". Error: {e}")

            self.free_worker(server_key, _worker_id, close_socket=True)

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
        except RuntimeError as _ex:

            if "There is no current event loop in thread" in str(_ex):

                _loop = asyncio.new_event_loop()
                asyncio.set_event_loop(_loop)

                return asyncio.get_event_loop()

            raise _ex
        except Exception as _ex:
            Log.error(f"Unexpected error in creating event loop: {_ex}")
            raise

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
        
        _status = response.get('status', 0)
        _payload = response.get('payload', {})

        if _status not in [200, 201] \
                and ('elements' not in _payload or '_id' not in _payload):
            
            _msg = _payload.get('text', f"Resource error, code: {_status}, {response['resource']}")
            _code = _payload.get('code', 0)
            
            raise ValidationException(_msg, code=_code, status=str(_status))

        return response
