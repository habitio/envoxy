# Envoxy Platform Framework

[![Tests](https://github.com/habitio/envoxy/workflows/Tests/badge.svg)](https://github.com/habitio/envoxy/actions/workflows/test.yml)
[![Security](https://github.com/habitio/envoxy/workflows/Security/badge.svg)](https://github.com/habitio/envoxy/actions/workflows/security.yml)
[![Quality](https://github.com/habitio/envoxy/workflows/Quality/badge.svg)](https://github.com/habitio/envoxy/actions/workflows/quality.yml)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

Envoxy is a service platform framework + uWSGI‑based daemon that unifies
messaging, persistence, background processing and an opinionated ORM layer.
One install gives you structured modules, connectors, conventions and a
packaged migration workflow.

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Core Capabilities](#core-capabilities)
- [Installation](#-installation)
- [Usage Examples](#-usage-examples)
- [ORM Conventions](#orm-conventions)
- [Migrations](#migrations-packaged-alembic)
- [Docker Support](#-docker-support)
- [Development](#-development)
- [Publishing Releases](#-publishing-releases)
- [Documentation](#-documentation)
- [Contributing](#-contributing)

## 🚀 Quick Start

```bash
# Install the framework and uWSGI server
pip install envoxy envoxyd

# Create a new project structure
mkdir my-service && cd my-service

# Create your application (run.py)
# See usage examples below

# Start the uWSGI server
envoxyd --http :8080 --set conf=/path/to/envoxy.json
```

## 📦 Installation

### Framework Only (Pure Python)

```bash
pip install envoxy
```

This installs the Envoxy framework with all Python dependencies for building services.

### With uWSGI Server (Manylinux Binary)

```bash
pip install envoxyd
```

This installs:

- The `envoxy` framework (as a dependency)
- A pre-built `envoxyd` binary (uWSGI with dynamic Python 3.12 linking)
- All shared libraries bundled for portability

**Note:** `envoxyd` is Linux-only. For development on macOS/Windows, use the framework with your own WSGI server.

### Development Installation

```bash
# Clone the repository
git clone https://github.com/habitio/envoxy.git
cd envoxy

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e .[dev]

# Install pre-commit hooks
pre-commit install
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed development setup.

## 💡 Usage Examples

### PostgreSQL with ORM

```python
from envoxy.db.orm import EnvoxyBase
from sqlalchemy import Column, String

class Product(EnvoxyBase):
    name = Column(String(255), nullable=False)

# Table name: aux_products
# Columns: id, name, created, updated, href
```

### Redis Cache

```python
from envoxy import redisc

# Set value
redisc.set("server_key", "my_key", {"a": 1, "b": 2})

# Get value
val = redisc.get("server_key", "my_key")

# Direct client access
client = redisc.client('server_key')
client.hgetall('my_hash')
```

### MQTT Messaging

```python
from envoxy import mqttc

# Publish
mqttc.publish('server_key', '/v3/topic/channel',
              {"data": "test"}, no_envelope=True)

# Subscribe
def callback(data):
    print(f"Received: {data}")

mqttc.subscribe('server_key', '/v3/topic/channels/#', callback)
```

### CouchDB

```python
from envoxy import couchdbc

# Find documents
docs = couchdbc.find(
    db="server_key.db_name",
    fields=["id", "field2"],
    params={"id": "1234", "field1__gt": "2345"}
)

# Get document
doc = couchdbc.get("005r9odyj...", db="server_key.db_name")
```

## 🐳 Docker Support (Development Only)

### Local Development Environment

For local development and testing, a Docker Compose setup is available:

```bash
cd docker/dev
docker-compose up -d
```

This starts:

- PostgreSQL database
- Redis cache
- pgAdmin (PostgreSQL GUI)
- RedisInsight (Redis GUI)

**Note:** For production deployments, use the `envoxyd` wheel from PyPI instead of Docker images.

See [docker/dev/README.md](docker/dev/README.md) for development environment documentation.

## 🔧 Development

### Run Tests

```bash
# All tests
make test

# Unit tests only
make test-unit

# With coverage
make test-cov
```

### Code Quality

```bash
# Lint and format
make lint
make format

# Type checking
make type-check

# Run all CI checks locally
make ci-local
```

### Build Documentation

```bash
# Build system documentation
cat docs/BUILD.md

# CI/CD pipeline documentation
cat docs/CI-CD.md

# Testing guide
cat tests/README.md
```

## 📦 Publishing Releases

### Publishing to TestPyPI (Testing)

TestPyPI is used to test package distribution before publishing to production PyPI.

#### 1. Update Version Numbers

Update the version in both package files:

```bash
# Edit pyproject.toml for envoxy
vim pyproject.toml  # Update version = "0.6.10"

# Edit vendors/pyproject.toml for envoxyd
vim vendors/pyproject.toml  # Update version = "0.5.10"
```

#### 2. Commit and Push Version Changes

```bash
git add pyproject.toml vendors/pyproject.toml
git commit -m "chore: Bump version to 0.6.10 / 0.5.10"
git push origin main
```

#### 3. Automatic TestPyPI Publishing

**When you push to `main` branch**, both workflows automatically trigger:

- **envoxy-publish.yml**: Builds pure Python wheel → publishes to TestPyPI
- **envoxyd-manylinux.yml**: Builds manylinux wheel → publishes to TestPyPI

No manual workflow trigger needed! Every push to `main` automatically publishes to TestPyPI for testing.

#### 4. Test Installation from TestPyPI

```bash
# Create a fresh virtual environment
python3.12 -m venv test-env
source test-env/bin/activate

# Install from TestPyPI (note: --extra-index-url needed for dependencies)
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ envoxy
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ envoxyd

# Verify installation
python -c "import envoxy; print(envoxy.__version__)"
envoxyd --version

# Test basic functionality
python -c "from envoxy.db.orm import EnvoxyBase; print('Import successful')"
```

### Publishing to PyPI (Production)

Production releases require manual workflow dispatch to prevent accidental publishes.

#### 1. Ensure Version is Updated

Make sure `pyproject.toml` and `vendors/pyproject.toml` have the correct version numbers and are pushed to `main`.

#### 2. Create and Push Git Tag

```bash
# Create annotated tag (recommended for documentation)
git tag -a v0.6.10 -m "Release version 0.6.10

- Feature: Description of major features
- Fix: Description of bug fixes
- Chore: Infrastructure updates
"

# Push the tag to GitHub
git push origin v0.6.10
```

**Note:** Pushing a tag will trigger the workflows to **build** the packages, but **NOT** publish to production PyPI.

#### 3. Manual Production Publishing

After pushing the tag and verifying the builds succeeded:

**For envoxy (pure Python wheel):**

1. Go to [GitHub Actions](https://github.com/habitio/envoxy/actions)
2. Select `Build and publish envoxy (pure Python)` workflow
3. Click "Run workflow"
4. Select the tag (e.g., `v0.6.10`) from the branch dropdown
5. Click "Run workflow"

This will publish to production PyPI at `https://pypi.org/project/envoxy/`

**For envoxyd (manylinux binary):**

1. Go to [GitHub Actions](https://github.com/habitio/envoxy/actions)
2. Select `Build and publish envoxyd (manylinux)` workflow
3. Click "Run workflow"
4. Select the tag (e.g., `v0.6.10`) from the branch dropdown
5. Click "Run workflow"

This will publish to production PyPI at `https://pypi.org/project/envoxyd/`

#### 4. Verify Production Release

```bash
# Install from production PyPI
pip install --upgrade envoxy envoxyd

# Verify versions
pip show envoxy envoxyd
```

#### 5. Monitor Release

- Check PyPI pages: [envoxy](https://pypi.org/project/envoxy/), [envoxyd](https://pypi.org/project/envoxyd/)
- Verify GitHub Actions succeeded: [Actions tab](https://github.com/habitio/envoxy/actions)
- Check workflow logs for any errors

### Versioning Guidelines

Follow [Semantic Versioning](https://semver.org/):

- **Major version** (1.0.0): Breaking changes
- **Minor version** (0.6.0): New features, backward compatible
- **Patch version** (0.6.1): Bug fixes, backward compatible

Both `envoxy` and `envoxyd` should be versioned together to maintain compatibility:

```bash
# Example: Major release
envoxy: 1.0.0
envoxyd: 1.0.0

# Example: Feature release
envoxy: 0.7.0
envoxyd: 0.6.0  # Only if envoxyd has no changes
```

### Troubleshooting

**Build fails on GitHub Actions:**

- Check workflow logs in Actions tab
- Verify all tests pass: `make test`
- Ensure dependencies are up to date

**TestPyPI/PyPI upload fails:**

- Verify `TEST_PYPI_API_TOKEN` and `PYPI_API_TOKEN` secrets are set in repository settings
- Check if version already exists (PyPI doesn't allow re-uploading same version)
- Ensure package name is available

**envoxyd binary doesn't run:**

- Check RPATH is correct: `patchelf --print-rpath $(which envoxyd)`
- Verify shared libraries are bundled: `auditwheel show wheelhouse/*.whl`
- Test in clean manylinux container: `docker run -it quay.io/pypa/manylinux_2_28_x86_64 bash`

## 📚 Documentation

## Core capabilities

- ZeroMQ / UPnP integration ("Zapata")
- MQTT / AMQP (RabbitMQ) messaging
- Celery task dispatch
- CouchDB & PostgreSQL connectors (direct + SQLAlchemy helpers)
- Redis cache / key‑value utilities
- Packaged Alembic migrations & CLI (`envoxy-alembic`)
- Opinionated ORM conventions (automatic naming, audit columns, index safety)

## Recent additions

- `EnvoxyBase` declarative base (prefix + pluralization + audit fields)
- Idempotent mapper listeners (populate id/created/updated/href)
- Bundled Alembic config (`alembic.ini` + `env.py`) with model auto‑discovery
- Session helpers: `session_scope`, `transactional`

## Why

Reduce boilerplate per service, enforce naming consistency across a fleet and
make migrations / messaging predictable and safe.

## ORM conventions

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

- Visibly segregates auxiliary tables from core platform data-layer storage.
- Prevents future naming collisions if a core table later lands in RDBMS form.
- Makes auditing / cleanup simpler (drop or archive all `aux_` tables safely).
- Signals that schemas can evolve faster with fewer cross‑service guarantees.

Guidelines:

- Keep business‑critical source-of-truth entities in the primary data-layer.
- Use ORM `aux_` tables for performance, enrichment, or transient coordination.
- Avoid back‑writing from `aux_` tables into the core pipeline except via explicit
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

## Migrations (packaged Alembic)

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

## Daemon & packaging

`envoxyd` boots service modules via embedded customized uWSGI.

Install (Make):

```
make install
```

Docker:

```bash
# Development: Quick start with docker-compose (recommended)
cd docker/dev && docker-compose up -d

# Or build builder images manually
docker build --build-arg UID=$(id -u) --build-arg GID=$(id -g) \
  -t envoxy-ubuntu:24.04 -f docker/builder/ubuntu-24.04.Dockerfile .

# Production runtime image
docker build -t envoxy:runtime -f docker/runtime/Dockerfile .
```

See `docker/README.md` for detailed Docker documentation.

Run:

```
envoxyd --http :8080 --set conf=/path/to/confs/envoxy.json
```

Build packages:

```
make packages
```

Manual (example):

```bash
# Using tools/build.sh (recommended)
./tools/build.sh packages

# Or manually with Python 3.12
python3.12 setup.py sdist bdist_wheel
cd vendors && python3.12 setup.py sdist bdist_wheel
twine upload dist/*
```

Details: `docs/ENVOXYD.md`.

## Project scaffold

```
envoxy-cli --create-project --name my-container
```

Docker (mount volumes):

```
docker run -it -d -p 8080:8080 \
  -v /path/to/project:/home/envoxy \
  -v /path/to/plugins:/usr/envoxy/plugins envoxy
```

## PostgreSQL (direct connector)

Read-only queries:

```
from envoxy import pgsqlc
rows = pgsqlc.query("db_name", "select * from sample_table where id = 1;")
```

Writes: use the ORM (SQLAlchemy) via `PgDispatcher.sa_manager()` and models. Direct
`insert()` on the raw client is no longer supported by design.

## CouchDB

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

## Redis

```
from envoxy import redisc
redisc.set("server_key", "my_key", {"a": 1, "b": 2})
val = redisc.get("server_key", "my_key")
client = redisc.client('server_key'); client.hgetall('my_hash')
```

## MQTT

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

### Core Documentation

- **[BUILD.md](docs/BUILD.md)** - Build system and tools documentation
- **[CI-CD.md](docs/CI-CD.md)** - Continuous Integration/Deployment guide
- **[ENVOXYD.md](docs/ENVOXYD.md)** - Daemon build & packaging
- **[POSTGRES.md](docs/POSTGRES.md)** - PostgreSQL (direct + ORM)
- **[COUCHDB.md](docs/COUCHDB.md)** - CouchDB usage & selectors
- **[MQTT.md](docs/MQTT.md)** - MQTT detailed usage

### How-To Guides

- **[HOWTO-migrations.md](docs/HOWTO-migrations.md)** - Migrations & Alembic packaging
- **[HOWTO-shared-db.md](docs/HOWTO-shared-db.md)** - Shared DB guidance
- **[HOWTO-ci-tools.md](docs/HOWTO-ci-tools.md)** - CI tooling helpers

### Additional Resources

- **[tests/README.md](tests/README.md)** - Comprehensive testing guide
- **[docker/README.md](docker/README.md)** - Docker build and deployment
- **[docker/MIGRATION.md](docker/MIGRATION.md)** - Docker migration guide

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:

- Development setup instructions
- Code style guidelines
- Testing requirements
- Pull request process
- Release workflow

## 📝 License

See [LICENSE](LICENSE) for details.

## 🔗 Links

- **Repository**: [github.com/habitio/envoxy](https://github.com/habitio/envoxy)
- **Issues**: [github.com/habitio/envoxy/issues](https://github.com/habitio/envoxy/issues)
- **Changelog**: [CHANGELOG](CHANGELOG)

---

**Made with ❤️ by the Envoxy team**
