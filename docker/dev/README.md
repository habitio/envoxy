# Envoxy Development Environment

Complete Docker-based development environment for building, testing, and publishing envoxy packages.

## Quick Start

```bash
# Start development services
cd docker/dev
docker compose up -d

# Load helper functions
source dev.sh
```

## Services

- **envoxy** - Runtime environment with uwsgi (http://localhost:8080)
- **postgres** - PostgreSQL database (localhost:5432)
- **redis** - Redis cache (localhost:6379)
- **builder** - Package building environment (on-demand)

Optional tools (use `--profile tools`):

- **pgadmin** - PostgreSQL GUI (http://localhost:5050)
- **redis-commander** - Redis GUI (http://localhost:8081)

## Development Workflow

### 1. Build Packages

Build envoxy and envoxyd wheel packages:

```bash
envoxy-build
# or
docker compose run --rm --profile tools builder make packages
```

This creates:

- `dist/envoxy-*.whl` - Envoxy framework package
- `vendors/dist/envoxyd-*.whl` - Envoxyd daemon package

### 2. Test Locally

Install to local /opt/envoxy environment:

```bash
envoxy-install-local
# or
docker compose run --rm --profile tools builder make install
```

### 3. Export Packages

Export built packages to your host machine:

```bash
envoxy-export ./my-packages
```

### 4. Publish to PyPI

Publish to test PyPI (for testing):

```bash
envoxy-publish testpypi
```

Publish to production PyPI:

```bash
envoxy-publish pypi
```

**Note**: Requires PyPI credentials configured in `~/.pypirc`

## Helper Commands

Load the helper functions:

```bash
source dev.sh
```

Available commands:

- `envoxy-build` - Build packages
- `envoxy-install-local` - Install to /opt/envoxy
- `envoxy-publish [repo]` - Publish to PyPI
- `envoxy-export [dir]` - Export packages
- `envoxy-clean` - Clean build artifacts
- `envoxy-test` - Run tests
- `envoxy-shell` - Interactive shell
- `envoxy-help` - Show help

## Manual Docker Commands

### Build Packages

```bash
docker compose run --rm --profile tools builder bash -c "
    make packages
"
```

### Install Locally

```bash
docker compose run --rm --profile tools builder bash -c "
    make install
"
```

### Publish to PyPI

```bash
docker compose run --rm --profile tools builder bash -c "
    pip install twine &&
    twine upload --repository testpypi dist/* &&
    cd vendors && twine upload --repository testpypi dist/*
"
```

### Interactive Development

```bash
# Open shell in builder
docker compose run --rm --profile tools builder /bin/bash

# Inside container:
source /opt/envoxy/bin/activate
make packages
```

## Configuration

### PyPI Credentials

Create `~/.pypirc` in your home directory:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-your-token-here

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-your-test-token-here
```

Mount it in docker-compose.yml:

```yaml
builder:
  volumes:
    - ~/.pypirc:/root/.pypirc:ro
```

### Application Code

Mount your application code for development:

```yaml
envoxy:
  volumes:
    - /path/to/your/app:/usr/envoxy/app
```

Update `envoxy.json` to include your modules:

```json
{
  "modules": ["/usr/envoxy/app/views.py"]
}
```

## Troubleshooting

### uwsgi module not found

If you see `ModuleNotFoundError: No module named 'uwsgi'`:

- Use `envoxyd` binary, not `python -m envoxyd.run`
- uwsgi module only exists inside uwsgi process

### Package not building

```bash
# Clean and rebuild
envoxy-clean
envoxy-build
```

### Check logs

```bash
docker compose logs envoxy
docker compose logs postgres
docker compose logs redis
```

## Architecture

```
┌─────────────────────────────────────────┐
│          Docker Environment             │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────┐  ┌──────────┐            │
│  │  Builder │  │  Envoxy  │            │
│  │  Stage   │  │ Runtime  │            │
│  └────┬─────┘  └────┬─────┘            │
│       │             │                   │
│   Build &       Run uwsgi               │
│   Package       + Flask                 │
│       │             │                   │
│       └─────┬───────┘                   │
│             │                           │
│      /opt/envoxy/                       │
│      (virtualenv)                       │
│             │                           │
│    ┌────────┴────────┐                 │
│    │  envoxy.whl     │                 │
│    │  envoxyd.whl    │                 │
│    └─────────────────┘                 │
│                                         │
│  ┌──────────┐  ┌──────────┐            │
│  │ Postgres │  │  Redis   │            │
│  └──────────┘  └──────────┘            │
└─────────────────────────────────────────┘
```

## See Also

- [BUILD.md](../../docs/BUILD.md) - Build system documentation
- [QUICK-REFERENCE.md](../../QUICK-REFERENCE.md) - Quick reference guide
- [PROJECT-STATUS.md](../../PROJECT-STATUS.md) - Project status
