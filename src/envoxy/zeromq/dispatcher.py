import zmq

from ..utils.config import Config
from ..utils.logs import Log
from ..utils.singleton import Singleton


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

            self._instances[_server_key] = {
                'conf': _conf,
                'socket': _socket,
                'url': 'tcp://{}:{}'.format(_conf.get('host'), _conf.get('port'))
            }

    def send_and_recv(self, _server_key, _message):

        _response = None
        _instance = self._instances[_server_key]

        try:
            _instance['socket'].bind(_instance['url'])
            _instance['socket'].send_json(_message)
            _response = _instance['socket'].recv_json()
        except Exception as e:
            Log.error('ZMQ::publish : It is not possible to send message using the ZMQ server "{}". Error: {}'.format(_instance['url'], e))
        finally:
            _instance['socket'].unbind(_instance['url'])

        return _response
        

class Dispatcher():

    @staticmethod
    def get(server_key, url, params=None):
            
        _message = {
            'resource': url,
            'params': params,
            'performative': 0
        }
        
        return ZMQ.instance().send_and_recv(server_key, _message)
