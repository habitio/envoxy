from celery import Celery

from ..utils.config import Config


class Client:

    app = None

    def initialize(server_key=None):

        _conf = Config.get('amqp_servers')

        if not _conf:
            raise Exception('Error to find AMQP Servers config')

        if server_key is None:
            server_key = list(_conf.keys())[0]

        server = _conf.get(server_key)

        broker = f"amqp://{server['user']}:{server['passwd']}@{server['host']}:{server['port']}/{server['vhost']}"

        app = Celery('envoxy', broker=broker)

        app.autodiscover_tasks()

        Client.app = app
