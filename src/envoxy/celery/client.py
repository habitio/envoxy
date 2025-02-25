from celery import Celery

from ..utils.config import Config

class Client:

    app = None

    def initialize(self, server):

        _conf = Config.get('amqp_servers')

        if not _conf:
            raise Exception('Error to find AMQP Servers config')

        server = _conf.get(server)

        broker = f"amqp://{server['user']}:{server['passwd']}@{server['host']}:{server['port']}/{server['vhost']}"

        app = Celery('envoxy', broker=broker)
        app.autodiscover_tasks()

        self.app = app
