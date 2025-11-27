# Envoxy Platform Framework - AI Coding Agent Instructions

## Project Overview

Envoxy is a service platform framework combining uWSGI-based daemon, messaging, persistence, and an opinionated ORM. It provides a unified Python 3.12 framework for building microservices with PostgreSQL, Redis, CouchDB, MQTT, ZeroMQ, and Celery integrations.

**Key Architecture**: Singleton-based dispatchers (`mqttc`, `redisc`, `pgsqlc`, `couchdbc`, `zmqc`, `celeryc`) exposed via `from envoxy import *` for client access across the codebase.

## Critical Workflows

### Development Setup

```bash
python3.12 -m venv venv && source venv/bin/activate
pip install -e .[dev]
pre-commit install
cd docker/dev && docker compose up -d  # PostgreSQL, Redis, pgAdmin, RedisInsight
```

### Running Tests

```bash
make test          # All tests
make test-unit     # Fast unit tests only (marker: @pytest.mark.unit)
make test-cov      # Coverage report → htmlcov/index.html
pytest -k test_name -m "not slow"  # Specific tests, skip slow ones
```

### Code Quality (Pre-commit enforced)

```bash
make lint          # ruff check (must pass)
make format        # ruff format (auto-fix)
make type-check    # mypy --ignore-missing-imports
pylint src/envoxy/ --fail-under=8.0  # Quality threshold
```

### Migrations (Alembic via CLI)

```bash
envoxy-alembic revision -m "description" --autogenerate
envoxy-alembic upgrade head
envoxy-alembic current
```

**Important**: Set `SERVICE_MODELS=your.module.models` env var for service-specific migrations. Models must import all `EnvoxyBase` subclasses to populate metadata.

## ORM Conventions (Strict Rules)

### Table Naming

- **Auto-prefixed with `aux_`**: All `EnvoxyBase` models get `aux_{plural_class_name}` tables
  - Example: `class Product(EnvoxyBase)` → table `aux_products`
  - Override: Set `__exception_tablename__ = "custom_name"` to skip prefix
- **Metaclass**: `EnvoxyMeta` handles pluralization via `inflect` library

### Mandatory Columns (from `EnvoxyMixin`)

Every model inherits: `id` (String 36), `created` (DateTime), `updated` (DateTime), `href` (String 1024)

### Constraint Naming (Automatic)

Constraints auto-generate names to avoid conflicts:

- Indexes: `idx_{table}_{cols}` (e.g., `idx_products_name_category`)
- Unique: `uq_{table}_{cols}`
- ForeignKeys: `fk_{table}_{local_col}_to_{ref_table}`
- Checks: `ck_{table}_{hash}`
- **Max 63 chars** (Postgres limit), hashed if longer

### ForeignKey Prefixing

String-based FK targets are auto-prefixed:

```python
# Write this:
ForeignKey("users.id")
# Becomes: aux_users.id (automatically)
```

## Validation Pattern (Critical)

Use `assertz_*` helpers from `envoxy.asserts` for request validation (throws `ValidationException`):

```python
from envoxy.asserts import assertz_mandatory, assertz_string, assertz_integer

assertz_mandatory(request, "user_id")         # Key exists and not None (empty strings ARE allowed)
assertz_string(request, "user_id")            # Type validation
assertz_integer(request, "count")             # Integer check
```

**Reply variants** (`assertz_mandatory_reply`, etc.) return dict instead of raising exceptions for non-critical paths.

## Singleton Dispatchers (Import Pattern)

```python
from envoxy import mqttc, redisc, pgsqlc, couchdbc, zmqc, celeryc

# MQTT
mqttc.publish('server_key', '/topic', {"data": "value"})
mqttc.subscribe('server_key', '/topic/#', callback_fn)

# Redis
redisc.set("server_key", "my_key", {"a": 1})
val = redisc.get("server_key", "my_key")

# PostgreSQL (via SQLAlchemy session)
session = pgsqlc.session("server_key")

# CouchDB
docs = couchdbc.find(db="server_key.db_name", params={"field": "value"})

# ZeroMQ
zmqc.send("server_key", payload)
```

**Configuration**: `envoxy.json` defines server keys with connection params (see `docker/dev/envoxy.json` example).

## Decorators

```python
from envoxy.decorators import auth_required, cache, on

@auth_required()                    # Injects authenticated headers
def protected_view(view, request, **kwargs): ...

@cache(ttl=3600)                    # Redis-backed caching
def expensive_operation(view, request): ...

@on(route="/api/v1/products")      # Metadata annotation
class ProductView: ...
```

## Response Handling

```python
from envoxy import Response

# Auto JSON serialization
return Response({"status": "ok", "data": items})
return Response({"payload": data, "status": 200})

# Lists auto-wrapped with size
return Response([item1, item2])  # → {"elements": [...], "size": 2}
```

## Common Pitfalls

1. **Don't manually prefix table names** - `EnvoxyMeta` handles it
2. **Don't use `BASE_TABLE_PREFIX` directly** - Import `AUX_TABLE_PREFIX` from `envoxy.db.orm.constants`
3. **Thread safety** - Use `Singleton` or `SingletonPerThread` from `envoxy.utils.singleton`
4. **Constraint names** - Let `EnvoxyMixin` auto-generate to avoid length/conflict issues
5. **uWSGI config** - Production uses `uwsgi.opt.get("conf_content")`, dev fallback to `Config.set_file_path()`

## Testing Markers

```python
@pytest.mark.unit           # Fast, isolated (default)
@pytest.mark.integration    # Requires services (postgres, redis)
@pytest.mark.slow           # Long-running
@pytest.mark.postgresql     # Needs PostgreSQL
```

## Package Structure

- `src/envoxy/` - Main framework code
  - `db/orm/` - SQLAlchemy extensions (base, mixin, meta, schema)
  - `mqtt/`, `redis/`, `zeromq/` - Messaging dispatchers
  - `auth/` - Authentication backends
  - `tools/alembic/` - Packaged migration CLI
  - `utils/` - Singleton, config, datetime, logs, encoders
- `tests/unit/` - Fast tests (no external deps)
- `examples/template_service/` - Reference implementation

## Publishing (CI/CD via GitHub Actions)

1. **Create `v*` tag** (e.g., `v0.6.9`) and mark as **pre-release** → auto-triggers build to TestPyPI
2. **Test the TestPyPI package** to verify it works correctly
3. **Manually trigger workflows** (`envoxy-publish.yml`, `envoxyd-manylinux.yml`) to publish to PyPI
4. **Mark release as latest** after successful PyPI publication

Workflows: `envoxy-publish.yml` (pure Python), `envoxyd-manylinux.yml` (uWSGI binary)

## Documentation

- `QUICK-REFERENCE.md` - Command cheatsheet
- `CONTRIBUTING.md` - Development guide
- `docs/BUILD.md` - Build system internals
- `docs/HOWTO-migrations.md` - Alembic workflows
- `tests/README.md` - Testing conventions
