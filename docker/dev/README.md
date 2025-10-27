# Envoxy Local Development Environment# Envoxy Development Environment



Docker-based local development environment for testing envoxy applications.Complete Docker-based development environment for building, testing, and publishing envoxy packages.



## Quick Start## Quick Start



```bash```bash

cd docker/dev# Start development services

cd docker/dev

# Start all servicesdocker compose up -d

docker compose up -d

# Load helper functions

# View logssource dev.sh

docker compose logs -f envoxy```



# Stop services## Services

docker compose down

```- **envoxy** - Runtime environment with uwsgi (http://localhost:8080)

- **postgres** - PostgreSQL database (localhost:5432)

## Services- **redis** - Redis cache (localhost:6379)

- **builder** - Package building environment (on-demand)

### Core Services

Optional tools (use `--profile tools`):

- **envoxy** - Runtime environment with uwsgi (http://localhost:8080)

- **postgres** - PostgreSQL database (localhost:5432)- **pgadmin** - PostgreSQL GUI (http://localhost:5050)

- **redis** - Redis cache (localhost:6379)- **redis-commander** - Redis GUI (http://localhost:8081)



### Optional Tools (use `--profile tools`)## Development Workflow



- **pgadmin** - PostgreSQL GUI (http://localhost:5050)### 1. Build Packages

  - Email: `admin@envoxy.local`

  - Password: `admin`Build envoxy and envoxyd wheel packages:

- **redis-commander** - Redis GUI (http://localhost:8081)

```bash

Start with tools:envoxy-build

```bash# or

docker compose --profile tools up -ddocker compose run --rm --profile tools builder make packages

``````



## ConfigurationThis creates:



### Application Configuration- `dist/envoxy-*.whl` - Envoxy framework package

- `vendors/dist/envoxyd-*.whl` - Envoxyd daemon package

Edit `envoxy.json` to configure your application:

### 2. Test Locally

```json

{Install to local /opt/envoxy environment:

  "modules": ["/path/to/your/views.py"],

  "psql_servers": {```bash

    "default": {envoxy-install-local

      "host": "postgres",# or

      "port": "5432",docker compose run --rm --profile tools builder make install

      "db": "envoxy",```

      "user": "envoxy",

      "passwd": "dev_password"### 3. Export Packages

    }

  },Export built packages to your host machine:

  "redis_servers": {

    "default": {```bash

      "bind": "redis:6379",envoxy-export ./my-packages

      "db": "0"```

    }

  }### 4. Publish to PyPI

}

```Publish to test PyPI (for testing):



### Mount Your Application```bash

envoxy-publish testpypi

To develop your own application, mount your code in `docker-compose.yml`:```



```yamlPublish to production PyPI:

envoxy:

  volumes:```bash

    - ../../src:/usr/envoxy/srcenvoxy-publish pypi

    - /path/to/your/app:/usr/envoxy/app```

```

**Note**: Requires PyPI credentials configured in `~/.pypirc`

### Database Access

## Helper Commands

PostgreSQL credentials:

- Host: `localhost` (or `postgres` from within containers)Load the helper functions:

- Port: `5432`

- Database: `envoxy````bash

- User: `envoxy`source dev.sh

- Password: `dev_password````



### Redis AccessAvailable commands:



Redis connection:- `envoxy-build` - Build packages

- Host: `localhost` (or `redis` from within containers)- `envoxy-install-local` - Install to /opt/envoxy

- Port: `6379`- `envoxy-publish [repo]` - Publish to PyPI

- `envoxy-export [dir]` - Export packages

## Building & Publishing Packages- `envoxy-clean` - Clean build artifacts

- `envoxy-test` - Run tests

Package building and publishing is handled by GitHub Actions. See `.github/workflows/` for:- `envoxy-shell` - Interactive shell

- `envoxy-publish.yml` - Publishes envoxy package to PyPI- `envoxy-help` - Show help

- `envoxyd-manylinux.yml` - Builds and publishes envoxyd manylinux wheels

## Manual Docker Commands

To trigger a release, create and push a git tag:

```bash### Build Packages

git tag v0.5.10

git push origin v0.5.10```bash

```docker compose run --rm --profile tools builder bash -c "

    make packages

## Troubleshooting"

```

### Service won't start

### Install Locally

Check logs:

```bash```bash

docker compose logs envoxydocker compose run --rm --profile tools builder bash -c "

```    make install

"

### Database connection issues```



Ensure postgres is healthy:### Publish to PyPI

```bash

docker compose ps postgres```bash

```docker compose run --rm --profile tools builder bash -c "

    pip install twine &&

Reset database:    twine upload --repository testpypi dist/* &&

```bash    cd vendors && twine upload --repository testpypi dist/*

docker compose down -v"

docker compose up -d```

```

### Interactive Development

### Port conflicts

```bash

If ports 5432, 6379, or 8080 are already in use, modify them in `docker-compose.yml`:# Open shell in builder

```yamldocker compose run --rm --profile tools builder /bin/bash

postgres:

  ports:# Inside container:

    - "15432:5432"  # Use different host portsource /opt/envoxy/bin/activate

```make packages

```

## Development Workflow

## Configuration

1. Start services: `docker compose up -d`

2. Make code changes in your local editor### PyPI Credentials

3. Changes are reflected immediately (volumes are mounted)

4. View logs: `docker compose logs -f envoxy`Create `~/.pypirc` in your home directory:

5. Stop services: `docker compose down`

```ini

## Cleaning Up[distutils]

index-servers =

Remove all containers and volumes:    pypi

```bash    testpypi

docker compose down -v

```[pypi]

username = __token__

Remove images:password = pypi-your-token-here

```bash

docker compose down --rmi all[testpypi]

```repository = https://test.pypi.org/legacy/

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
