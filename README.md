Envoxy Platform Framework
=========================

The Envoxy is a different kind of API REST framework and application daemon, we are trying to use all the best tools and technics together getting all their power and performance to be able to have all the platform running in one unique framework allowing communications and task distribution with:
- Zapata using (ZeroMQ / UPnP);
- RabbitMQ using (MQTT / AMQP);
- Celery;
- CouchDB;
- PostgreSQL;

# Build envoxyd (Envoxy Daemon) and envoxy python package:
What is `envoxyd`? It is the process daemon using embeded uWSGI customized to be able to boot our modules using the `envoxy` structure and API's. 
```
$ make install
```

or using docker

```
$ docker build -t envoxy .
```

### Steps during the build processs

- Install dependencies
- Delete previous virtualenv dir if exists (/opt/envoxy)
- Create clean virtualenv (/opt/envoxy) with python3.6 version and activate
- Give current user permissions to virtualenv dir
- Install envoxy:  `python setup install`
- Prepare envoxyd files:
    * Delete src dir (vendors/src)
    * Create envoxyd src dir and make a clean copy o uWSGI
    * Copy envoxyd files to customize uWSGI
- Install envoxyd: `python setup install`

# Prepare packages to pypi repository

```
$ make packages
```

### Steps during the packaging processs

- Install Process
- Create a Source distribution for both packages: `python3 setup.py sdist bdist_wheel`

# Publish to pypi repository

On project root for *envoxy* and ./vendors dir for *envoxyd*

- Make sure `build` dir was created
- `build` dir must contain a `.whl` and `.tar.gz` of the current version


```
envoxy-0.0.2-py3-none-any.whl
envoxy-0.0.2.tar.gz
```

- Upload current package using twine command and enter your credentials for the account you registered on the real PyPI.

```
$ twine upload dist/*
```


# Run envoxyd
```
$ envoxyd --http :8080 --set conf=/path/to/confs/envoxy.json
```

# How to use envoxy
Create a new project
```
$ envoxy-cli --create-project --name my-container
```

# How to build envoxy with Docker
```
$ docker build --no-cache -t envoxy-ubuntu:18.04 -f envoxy-ubuntu.Dockerfile .
$ docker build -t envoxy .
```

# Use an existent project path as volume
```
$ docker run -it -d -p 8080:8080 -v /path/to/project:/home/envoxy -v /path/to/plugins:/usr/envoxy/plugins envoxy
```


# PostgreSQL connector samples

### Select Query

```
from envoxy import pgsqlc

result = pgsqlc.query(
    "db_name",
    "select * from sample_table where id = 1;"
)

```


### Insert statement and Transaction block

```
from envoxy import pgsqlc

with pgsqlc.transaction('db_name') as db_conn:

    r = db_conn.query(
        sql="select * from sample_table limit 2"
    )

    db_conn.insert('sample_table2', {
        "field1": "test",
        "field2": "test",
        "id": 1
    })

```

_all inserts statements must be placed inside a transaction block_


# CouchDB connector samples


## Find

*valid selectors:* eq, gt, gte, lt, lte
*fields*: if defined will only return this fields, otherwise will return all fields

```
from envoxy import couchdbc

perms = couchdbc.find(
    db="server_key.db_name",
    fields=["id", "field2"]
    params={
        "id": "1234"
        "field1__gt": "2345"
    }
)
```


## Get

Get the document by id

```
from envoxy import couchdbc

perms = couchdbc.get(
    "005r9odyj91dw0y1ho32lvzh5r2avzngvrouyj",
    db="server_key.db_name",
)
```
