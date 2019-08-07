import json
import uuid

from ..constants import Performative, SERVER_NAME
from ..utils.datetime import Now
from ..utils.logs import Log
from ..utils.singleton import Singleton
from ..exceptions import ValidationException


import paho.mqtt.client as paho

RC_LIST = {
    0: "Connection successful",
    1: "Connection refused - incorrect protocol version",
    2: "Connection refused - invalid client identifier",
    3: "Connection refused - server unavailable",
    4: "Connection refused - bad username or password",
    5: "Connection refused - not authorised"
}

class MQTT(Singleton):

    _instances = {}

    _username = None
    _password = None
    _host = None
    _port = None
    _schema = None

    def __init__(self, config=None):


        self._server_confs = config.get('mqtt_servers')

        if not self._server_confs:
            raise Exception('Error to find MQTT Servers config')

        for _server_key in self._server_confs.keys():

            if _server_key in self._instances:
                if self._instances[_server_key]['mqtt_client'].connected_flag:
                    Log.debug(f'{_server_key} already connected')
                else:
                    self._instances[_server_key]['mqtt_client'].reconnect()

            _conf = self._server_confs[_server_key]

            self._instances[_server_key] = {
                'server_key': _server_key,
                'conf': _conf
            }

            self.connect(self._instances[_server_key])

    def on_connect(self, client, userdata, flags, rc):
        try:
            if rc == 0:
                client.connected_flag = True
                Log.verbose(f"Mqtt - Connected , result code {rc}")
            elif 0 < rc < 6:
                client.connected_flag = False
                raise Exception(RC_LIST[rc])
        except Exception as e:
            Log.error(e)
            client.reconnect()

    def connect(self, instance):

        use_auth_credentials = instance['conf'].get('use_auth_credentials', False)

        if not use_auth_credentials:  # get from config file

            bind = instance['conf'].get('bind', None)

            parts = bind.split(":")
            self.schema = parts[0]
            self.username = parts[1].replace("//", "")
            self.port = int(parts[3])

            parts = parts[2].split("@")
            self.password = parts[0]
            self.host = parts[1]

        else:
            credentials = instance['conf'].get('credentials')

            parts = credentials['mqtt'].split(":")
            self.schema = parts[0]
            self.host = parts[1].replace("//", "")
            self.port = int(parts[2])
            self.username = credentials['client_id']
            self.password = credentials['access_token']


        instance['mqtt_client'] = paho.Client()
        instance['mqtt_client'].on_connect = self.on_connect

        instance['mqtt_client'].username_pw_set(username=self.username, password=self.password)

        if not instance['mqtt_client']._ssl and self.schema == "mqtts":
            instance['mqtt_client'].tls_set(ca_certs=instance['conf']['cert_path'])

        instance['mqtt_client'].connect(self.host, self.port)
        instance['mqtt_client'].loop_start()

    def publish(self, server_key, topic, message, no_envelope=False, headers=None):

        mqtt_client = self._instances[server_key]['mqtt_client']

        if no_envelope:

            payload = json.dumps(message)

        else:

            payload = message.update({
                "headers": headers,
                "resource": topic
            })

        (rc, mid) = mqtt_client.publish(topic=topic, payload=payload)

        if rc == 0:
            Log.verbose(
                "Mqtt - Published successfully, result code({}) and mid({}) to topic: {} with payload:{}".format(
                    rc, mid, topic, message))

        else:

            raise ValidationException(
                "Mqtt - Failed to publish , result code({})".format(rc))

    def subscribe(self, server_key, topic, callback=None):
        mqtt_client = self._instances[server_key]['mqtt_client']
        mqtt_client.subscribe(topic, qos=0)

        if callback:
            mqtt_client.on_message = callback

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
    def publish(server_key, topic, message, no_envelope=False):

        return MQTT.instance().publish(server_key, topic, message, no_envelope=no_envelope, headers=Dispatcher.generate_headers())

    @staticmethod
    def subscribe(server_key, topic, callback=None):

        return MQTT.instance().subscribe(server_key, topic, callback=callback)

