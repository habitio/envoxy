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
        protocol = 'amqps' if server.get('cert_path', True) else 'amqp'

        broker = f"{protocol}://{server['user']}:{server['passwd']}@{server['host']}:{server['port']}/{server['vhost']}"

        app = Celery('envoxy', broker=broker)

        # celerybeat config

        if Config.get("mongodb_servers") and "celery" in Config.get("mongodb_servers"):

            _mongodb_celery = Config.get("mongodb_servers").get("celery", {})

            _mongodb_url = f"mongodb://{_mongodb_celery['user']}:{_mongodb_celery['passwd']}@{_mongodb_celery['host']}:{_mongodb_celery['port']}"

            config = {
                "mongodb_scheduler_db": _mongodb_celery.get("db"),
                "mongodb_scheduler_url": _mongodb_url
            }

            app.conf.update(**config)

        # task result backend config

        if Config.get("redis_servers") and "celery" in Config.get("redis_servers"):

            _redis_celery = Config.get("redis_servers").get("celery", {})

            config = {
                "result_backend": f"redis://{_redis_celery['bind']}/{_redis_celery['db']}"
            }

            app.conf.update(**config)

        app.autodiscover_tasks()

        Client.app = app
