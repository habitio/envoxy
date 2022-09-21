import json
import threading
import uuid

import paho.mqtt.client as paho

from ..constants import SERVER_NAME
from ..exceptions import ValidationException
from ..utils.config import Config
from ..utils.datetime import Now
from ..utils.logs import Log
from ..utils.singleton import Singleton


RC_LIST = {
    0: "Connection successful",
    1: "Connection refused - incorrect protocol version",
    2: "Connection refused - invalid client identifier",
    3: "Connection refused - server unavailable",
    4: "Connection refused - bad username or password",
    5: "Connection refused - not authorised"
}


class MqttConnector(Singleton):

    def __init__(self):

        self._instances = {}

        self._server_confs = Config.get('mqtt_servers')

        if not self._server_confs:
            raise Exception('Error to find MQTT Servers config')

        _credentials = Config.get_credentials()

        for _server_key in self._server_confs.keys():

            _conf = self._server_confs[_server_key]

            self._instances[_server_key] = {
                'server_key': _server_key,
                'conf': _conf,
                'credentials': _credentials,
                'username': None,
                'password': None,
                'host': None,
                'port': None,
                'schema': None,
                'lock': threading.Lock(),
                'mqtt_client': None,
                'subscriptions': []
            }

            _instance = self._instances[_server_key]

            _bind = _instance['conf'].get('bind', None)
        
            if not _bind: 
                raise Exception('bind must be provided')

            if not _instance['credentials']:  # credentials are provided within bind uri

                _parts = _bind.split(":")
                
                _instance['schema'] = _parts[0]
                _instance['username'] = _parts[1].replace("//", "")
                _instance['port'] = int(_parts[3])

                _parts = _parts[2].split("@")
                
                _instance['password'] = _parts[0]
                _instance['host'] = _parts[1]

            else:

                _parts = _bind.split(":")
                
                _instance['schema'] = _parts[0]
                _instance['host'] = _parts[1].replace("//", "")
                _instance['port'] = int(_parts[2])
                
                _instance['username'] = _instance['credentials']['client_id']
                _instance['password'] = _instance['credentials']['access_token']

    def is_connected(self, server_key):
        _instance = self._instances.get(server_key)
        return _instance and _instance['mqtt_client'] is not None and _instance['mqtt_client'].connected_flag

    def disconnect(self, server_key):

        if self._instances[server_key]['mqtt_client'] is None:
            return True 
            
        with self._instances[server_key]['lock']:
            
            try:
                self._instances[server_key]['mqtt_client'].disconnect()
            except Exception as e:
                Log.warning('Error on disconnecting from MQTT server: {}'.format(e))
            
            try:
                self._instances[server_key]['mqtt_client'].loop_stop()
            except Exception as e:
                Log.warning('Error on stopping MQTT client loop: {}'.format(e))
            finally:
                self._instances[server_key]['mqtt_client'] = None
            
        return True

    def reconnect(self, server_key):
        
        try:
            
            _instance = self._instances.get(server_key)
            
            if _instance and _instance['mqtt_client'] is not None:
                
                _instance['mqtt_client'].reconnect()
                
                return True

            else:

                return self.connect(server_key)
        
        except Exception as e:
            
            Log.error('Error on reconnecting to MQTT server: {}'.format(e))

        return False

    def _on_connect(self, client, userdata, flags, rc):
        
        try:

            if rc == 0:
                
                client.connected_flag = True
                
                Log.verbose(f"Mqtt - Connected, result code {rc}, userdata {userdata}, flags {flags}")

                _instance = self._instances[userdata['server_key']]

                # Recovering subscriptions
                for _subscription in _instance['subscriptions']:
                    
                    self.create_subscription(
                        _instance, 
                        _subscription['topic'], 
                        callback=_subscription['callback'], 
                        qos=_subscription['qos']
                    )
            
            else:
                
                client.connected_flag = False
                
                raise Exception(
                    RC_LIST.get(rc, f"Unknown error: result code {rc}, userdata {userdata}, flags {flags}")
                )
        
        except Exception as e:
            
            Log.error(e)

    def connect(self, server_key):

        try:
            
            self.disconnect(server_key)

            _instance = self._instances[server_key]

            _instance['mqtt_client'] = paho.Client()
            _instance['mqtt_client'].on_connect = self._on_connect
            _instance['mqtt_client'].username_pw_set(username=_instance['username'], password=_instance['password'])

            if not _instance['mqtt_client']._ssl and _instance['schema'] == "mqtts":
                _instance['mqtt_client'].tls_set(ca_certs=_instance['conf']['cert_path'])

            _instance['mqtt_client'].user_data_set({'server_key': server_key})

            _instance['mqtt_client'].connect(_instance['host'], _instance['port'])
            _instance['mqtt_client'].loop_start()

            Log.notice('New MQTT conn: {}, schema = {}, host = {}, port = {}, username = {}'.format(
                _instance['mqtt_client'],
                _instance['schema'],
                _instance['host'],
                _instance['port'],
                _instance['username'],
                
            ))

            return True

        except Exception as e:
                
            Log.error(f"Error on connecting to MQTT server: {e}")
            
            return False

    def publish(self, server_key, topic, message, no_envelope=False, headers=None):

        _instance = self._instances[server_key]
        
        if not self.is_connected(server_key):
            
            if _instance['mqtt_client'] is None:
                if not self.connect(server_key):
                    return False
            else:
                if self.reconnect(server_key):
                    return False

        try:
            _mqtt_client = _instance['mqtt_client']

            _message = '{} [{}] {}'.format(
                Log.style.apply('> PUBLISH', Log.style.BOLD),
                Log.style.apply('MQTT', Log.style.GREEN_FG),
                Log.style.apply('{}'.format(topic), Log.style.BLUE_FG)
            )
            
            Log.trace(_message)

            if no_envelope:
                _payload = json.dumps(message)

            else:
                _payload = json.dumps(message.update({
                    "headers": headers,
                    "resource": topic
                }))

            _message = '{} | Message{}'

            Log.verbose(_message, _payload)

            with _instance['lock']:
                (_rc, _mid) = _mqtt_client.publish(topic, _payload)

            if _rc == 0:
                
                Log.verbose(
                    "Mqtt - Published successfully, result code({}) and mid({}) to topic: {} with payload:{}".format(
                        _rc, 
                        _mid, 
                        topic, 
                        message
                    )
                )

                return True

            else:

                raise ValidationException("Mqtt - Failed to publish, result code({}) and mid({}) to topic: {} with payload:{}".format(
                        _rc, 
                        _mid, 
                        topic, 
                        message
                    )
                )

        except ValidationException as e:
            
            raise e

        except Exception as e:
            
            Log.error(e)
            
            return False

    def subscribe(self, server_key, topic, callback=None):

        _instance = self._instances[server_key]

        _instance['subscriptions'].append({
            'topic': topic,
            'callback': callback,
            'qos': 0
        })

        self.create_subscription(server_key, topic, callback=callback)

    def create_subscription(self, instance, topic, callback=None, qos=0):
        
        _server_key = instance['server_key']

        if not self.is_connected(_server_key):
            
            if instance['mqtt_client'] is None:
                if not self.connect(_server_key):
                    return False
            else:
                if not self.reconnect(_server_key):
                    return False

        with instance['lock']:

            try:
        
                _mqtt_client = instance['mqtt_client']

                (_rc, _mid) = _mqtt_client.subscribe(topic, qos=qos)

                Log.verbose("Mqtt - Subscription result code({}) and mid({}) to topic: {}, callback {}".format(_rc, _mid, topic, callback))

                if callback:
                    _mqtt_client.message_callback_add(topic, callback)

            except Exception as e:
                
                Log.error('Error on subscribing to MQTT topic: {}'.format(e))

                return False

        return True


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

        return MqttConnector.instance().publish(server_key, topic, message, no_envelope=no_envelope, headers=MqttDispatcher.generate_headers())

    @staticmethod
    def subscribe(server_key, topic, callback=None):

        return MqttConnector.instance().subscribe(server_key, topic, callback=callback)

