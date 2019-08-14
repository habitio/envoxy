import json

from ..utils.logs import Log
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

class Client:

    _instances = {}

    _username = None
    _password = None
    _host = None
    _port = None
    _schema = None

    def __init__(self, _server_confs, credentials=None):

        if not _server_confs:
            raise Exception('Error to find MQTT Servers config')

        for _server_key in _server_confs.keys():

            if _server_key in self._instances:

                Log.info(self._instances[_server_key]['mqtt_client'].connected_flag)

                if self._instances[_server_key]['mqtt_client'].connected_flag:
                    Log.debug(f'{_server_key} already connected')
                else:
                    Log.debug('reconnecting on init')
                    self._instances[_server_key]['mqtt_client'].reconnect()

            _conf = _server_confs[_server_key]

            self._instances[_server_key] = {
                'server_key': _server_key,
                'conf': _conf,
                'credentials': credentials
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

    def connect(self, instance):

        bind = instance['conf'].get('bind', None)
        if not bind: raise Exception('bind must be provided')

        if not instance['credentials']:  # credentials are provided within bind uri

            parts = bind.split(":")
            self.schema = parts[0]
            self.username = parts[1].replace("//", "")
            self.port = int(parts[3])

            parts = parts[2].split("@")
            self.password = parts[0]
            self.host = parts[1]

        else:
            parts = bind.split(":")
            self.schema = parts[0]
            self.host = parts[1].replace("//", "")
            self.port = int(parts[2])
            self.username = instance['credentials']['client_id']
            self.password = instance['credentials']['access_token']


        instance['mqtt_client'] = paho.Client()
        instance['mqtt_client'].on_connect = self.on_connect
        instance['mqtt_client'].username_pw_set(username=self.username, password=self.password)

        if not instance['mqtt_client']._ssl and self.schema == "mqtts":
            instance['mqtt_client'].tls_set(ca_certs=instance['conf']['cert_path'])

        instance['mqtt_client'].connect(self.host, self.port)
        instance['mqtt_client'].loop_start()

    def publish(self, server_key, topic, message, no_envelope=False, headers=None):

        mqtt_client = self._instances[server_key]['mqtt_client']

        _message = '{} [{}] {}'.format(
            Log.style.apply('> PUBLISH', Log.style.BOLD),
            Log.style.apply('MQTT', Log.style.GREEN_FG),
            Log.style.apply('{}'.format(topic), Log.style.BLUE_FG)
        )
        Log.trace(_message)

        if no_envelope:
            payload = json.dumps(message)

        else:
            payload = json.dumps(message.update({
                "headers": headers,
                "resource": topic
            }))

        _message = '{} | Message{}'
        Log.verbose(_message, payload)

        (rc, mid) = mqtt_client.publish(topic, payload)

        if rc == 0:
            Log.verbose(
                "Mqtt - Published successfully, result code({}) and mid({}) to topic: {} with payload:{}".format(
                    rc, mid, topic, message))

        else:
            raise ValidationException("Mqtt - Failed to publish , result code({})".format(rc))


    def subscribe(self, server_key, topic, callback=None):
        mqtt_client = self._instances[server_key]['mqtt_client']

        (rc, mid) = mqtt_client.subscribe(topic, qos=0)

        Log.verbose("Mqtt - Subscription result code({}) and mid({}) to topic: {}, callback {}".format(rc, mid, topic, callback))

        if callback:
            mqtt_client.message_callback_add(topic, callback)

