## envoxyd (Daemon)

`envoxyd` is the uWSGI‑embedded daemon that boots Envoxy service modules and exposes HTTP and event endpoints (MQTT / ZeroMQ / internal dispatchers) under a unified lifecycle.

### Key Features

- Embedded customized uWSGI build
- Module & plugin discovery following the Envoxy directory layout
- Shared event loop integrations (timers, dispatchers)
- Graceful shutdown and restart hooks
- Structured logging surface (stdout by default; pluggable)

### Quick Start

```
envoxyd --http :8080 --set conf=/path/to/envoxy.json
```

Minimal `envoxy.json` (illustrative):

```
{
	"logging": {"level": "INFO"},
	"postgres": {"main": {"dsn": "postgresql://user:pass@localhost/app"}},
	"couchdb": {"server_key": {"url": "http://localhost:5984"}},
	"mqtt": {"broker": {"bind": "mqtt://localhost:1883"}}
}
```

### Build & Install

```
make install     # build + install envoxy & envoxyd
make packages    # create wheels/dist archives
```

Docker image:

```
docker build -t envoxy .
```

### Notes on portable envoxyd binaries

- Always build envoxyd inside the packaging virtualenv (the project uses `/opt/envoxy` in the Docker builder). This ensures compiled objects and the embedded uWSGI binary link against the same Python runtime used in the venv.
- The builder image installs `patchelf` and copies the interpreter shared object into `/opt/envoxy/lib`. After install we set the envoxyd RUNPATH to `/opt/envoxy/lib` so the binary prefers the colocated libpython at runtime.
- For development or debugging you can test the LD_LIBRARY_PATH override to force the runtime loader to prefer the venv lib:

```bash
export LD_LIBRARY_PATH=/opt/envoxy/lib:$LD_LIBRARY_PATH
envoxyd --http :8080 --set conf=/path/to/envoxy.json
```

This is a temporary debug step. The recommended approach for reproducible builds is to run `tools/build.sh` inside the builder (or CI) and publish manylinux wheels so downstream consumers don't need to build from source.

### Configuration Sources

| Source                       | Purpose                |
| ---------------------------- | ---------------------- |
| JSON file (`--set conf=...`) | Base structural config |
| Environment variables        | Secrets / overrides    |
| CLI flags (`--http`, etc.)   | Transport endpoints    |

Precedence (highest first): CLI flag > ENV > JSON file default.

### Logging

Default: INFO to stdout. Provide `logging.level` (`DEBUG`, `INFO`, `WARNING`, `ERROR`). Future extensions can inject JSON log formatter.

### Module Discovery

The daemon imports your service package modules (views, tasks, models) so that dispatchers and ORM metadata are registered before HTTP starts listening.

### Graceful Shutdown

Receives typical UNIX signals (TERM/INT) -> stops accepting new requests -> drains in‑flight handlers -> closes pools.

### Health & Readiness (Recommended Pattern)

Expose a lightweight HTTP endpoint (e.g. `/health`) inside your views returning a cached status of primary connectors.

### Troubleshooting

| Symptom                               | Hint                                                                          |
| ------------------------------------- | ----------------------------------------------------------------------------- |
| Models not migrated                   | Ensure models imported somewhere on startup (e.g. `from myapp import models`) |
| MQTT subscriptions lost after restart | Confirm dispatcher configuration & that topics are re‑registered on boot      |
| High memory                           | Inspect long‑lived references / large result sets kept in module globals      |

### Next Steps

- Add your database models and run `envoxy-alembic upgrade head`.
- Implement messaging handlers via `@on` decorator.
- Add Celery tasks (if integrated) for asynchronous workloads.
