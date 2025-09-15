Envoxy Platform Framework
=========================

Envoxy is a service platform framework + uWSGI‑based daemon that unifies
messaging, persistence, background processing and an opinionated ORM layer.
One install gives you structured modules, connectors, conventions and a
packaged migration workflow.

Core capabilities
-----------------
- ZeroMQ / UPnP integration ("Zapata")
- MQTT / AMQP (RabbitMQ) messaging
- Celery task dispatch
- CouchDB & PostgreSQL connectors (direct + SQLAlchemy helpers)
- Redis cache / key‑value utilities
- Packaged Alembic migrations & CLI (`envoxy-alembic`)
- Opinionated ORM conventions (automatic naming, audit columns, index safety)

Recent additions
----------------
- `EnvoxyBase` declarative base (prefix + pluralization + audit fields)
- Idempotent mapper listeners (populate id/created/updated/href)
- Bundled Alembic config (`alembic.ini` + `env.py`) with model auto‑discovery
- Session helpers: `session_scope`, `transactional`

Why
---
Reduce boilerplate per service, enforce naming consistency across a fleet and
make migrations / messaging predictable and safe.

ORM conventions
---------------
`EnvoxyBase` is the unified model base.

Automatic rules:
- Table prefix: `aux_`
- Pluralized class names (with curated exceptions)
- Audit columns injected: `id`, `created`, `updated`, `href`
- Index names rewritten with framework prefix
- Audit values populated by idempotent listeners

Why `aux_`?
The core Envoxy platform is designed around a ZeroMQ data-layer for primary domain
entities. The SQLAlchemy layer is intentionally a secondary/auxiliary persistence
mechanism for sidecar tables: caches, denormalized projections, integration state,
small feature flags, ephemeral join helpers—NOT the canonical domain records.

The `aux_` prefix:
* Visibly segregates auxiliary tables from core platform data-layer storage.
* Prevents future naming collisions if a core table later lands in RDBMS form.
* Makes auditing / cleanup simpler (drop or archive all `aux_` tables safely).
* Signals that schemas can evolve faster with fewer cross‑service guarantees.

Guidelines:
* Keep business‑critical source-of-truth entities in the primary data-layer.
* Use ORM `aux_` tables for performance, enrichment, or transient coordination.
* Avoid back‑writing from `aux_` tables into the core pipeline except via explicit
    integration processes.

Minimal model:
```
from envoxy.db.orm import EnvoxyBase
from sqlalchemy import Column, String

class Product(EnvoxyBase):
    name = Column(String(255), nullable=False)

metadata = EnvoxyBase.metadata  # for Alembic autogenerate
```

Benefits: consistent naming, fewer conflicts, less boilerplate.
More: `docs/HOWTO-migrations.md`, `docs/POSTGRES.md`.

Migrations (packaged Alembic)
-----------------------------
Run migrations without copying config.

CLI:
```
envoxy-alembic revision -m "create product table" --autogenerate
envoxy-alembic upgrade head
```
Module form:
```
python -m envoxy.tools.alembic.alembic current
```
Features: packaged config, model discovery, sqlite path normalization, baseline versions.
CI helper: `python -m envoxy.tools.check_migrations <versions_dir>`.
Docs: `docs/HOWTO-migrations.md`.

Daemon & packaging
------------------
`envoxyd` boots service modules via embedded customized uWSGI.

Install (Make):
```
make install
```
Docker:
```
docker build --no-cache -t envoxy-ubuntu:20.04 -f envoxy-ubuntu.Dockerfile .
docker build -t envoxy .
```
Run:
```
envoxyd --http :8080 --set conf=/path/to/confs/envoxy.json
```
Build packages:
```
make packages
```
Manual (example):
```
python3.11 setup.py sdist bdist_wheel
cd vendors && python3.11 setup.py sdist bdist_wheel
twine upload dist/*
```
Details: `docs/ENVOXYD.md`.

Project scaffold
----------------
```
envoxy-cli --create-project --name my-container
```

Docker (mount volumes):
```
docker run -it -d -p 8080:8080 \
  -v /path/to/project:/home/envoxy \
  -v /path/to/plugins:/usr/envoxy/plugins envoxy
```

PostgreSQL (direct connector)
-----------------------------
Read-only queries:
```
from envoxy import pgsqlc
rows = pgsqlc.query("db_name", "select * from sample_table where id = 1;")
```
Writes: use the ORM (SQLAlchemy) via `PgDispatcher.sa_manager()` and models. Direct
`insert()` on the raw client is no longer supported by design.

CouchDB
-------
Find:
```
from envoxy import couchdbc
docs = couchdbc.find(
    db="server_key.db_name",
    fields=["id", "field2"],
    params={"id": "1234", "field1__gt": "2345"}
)
```
Get:
```
doc = couchdbc.get("005r9odyj...", db="server_key.db_name")
```

Redis
-----
```
from envoxy import redisc
redisc.set("server_key", "my_key", {"a": 1, "b": 2})
val = redisc.get("server_key", "my_key")
client = redisc.client('server_key'); client.hgetall('my_hash')
```

MQTT
----
Publish:
```
from envoxy import mqttc
mqttc.publish('server_key', '/v3/topic/channel', {"data": "test"}, no_envelope=True)
```
Subscribe:
```
from envoxy import mqttc
mqttc.subscribe('server_key', '/v3/topic/channels/#', callback)
```
on_event class:
```
from envoxy import on
from envoxy.decorators import log_event

@on(endpoint='/v3/topic/channels/#', protocols=['mqtt'], server='server_key')
class MqttViewCtrl(View):
    @log_event
    def on_event(self, data, **kw):
        do_stuff(data)
```
Low‑level client example: `docs/MQTT.md`.

More documentation
------------------
- Daemon build & packaging: `docs/ENVOXYD.md`
- PostgreSQL (direct + ORM): `docs/POSTGRES.md`
- CouchDB usage & selectors: `docs/COUCHDB.md`
- MQTT detailed usage: `docs/MQTT.md`
- Migrations & Alembic packaging: `docs/HOWTO-migrations.md`
- Shared DB guidance: `docs/HOWTO-shared-db.md`
- CI tooling helpers: `docs/HOWTO-ci-tools.md`
