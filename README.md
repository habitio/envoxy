Envoxy Platform Framework
=========================

The Envoxy is a different kind of API REST framework and application daemon, we are trying to use all the best tools and technics together getting all their power and performance to be able to have all the platform running in one unique framework allowing communications and task distribution with:
- Zapata using (ZeroMQ / UPnP);
- RabbitMQ using (MQTT / AMQP);
- Celery;
- CouchDB;
- PostgreSQL;

# Build envoxyd (Envoxy Daemon):
What is `envoxyd`? It is the process daemon using embeded uWSGI customized to be able to boot our modules using the `envoxy` structure and API's. 
```
$ make envoxyd
```