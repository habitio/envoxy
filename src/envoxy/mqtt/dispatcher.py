import uuid

from ..constants import SERVER_NAME
from ..utils.datetime import Now
from .client import Client as MqttClient

from ..utils.singleton import Singleton
from ..utils.config import Config
from ..utils.logs import Log


class MqttConnector(Singleton):

    client = None

    def __init__(self):
        self.start_conn()

    def start_conn(self):
        Log.notice('new mqtt conn {}'.format(self.client))
        conf = Config.get('mqtt_servers')
        credentials = Config.get_credentials()
        self.client = MqttClient(conf, credentials=credentials)


class MqttDispatcher():

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
    def publish(server_key, topic, message, no_envelope=False):

        return MqttConnector.instance().client.publish(server_key, topic, message, no_envelope=no_envelope, headers=MqttDispatcher.generate_headers())

    @staticmethod
    def subscribe(server_key, topic, callback=None):

        return MqttConnector.instance().client.subscribe(server_key, topic, callback=callback)

