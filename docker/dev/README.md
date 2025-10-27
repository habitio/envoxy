# Envoxy Local Development Environment

Docker-based local development environment for testing envoxy applications.

## Quick Start

```bash
cd docker/dev

# Start all services
docker compose up -d

# View logs
docker compose logs -f envoxy

# Stop services
docker compose down
```

## Services

### Core Services

- **envoxy** - Runtime environment with uwsgi (http://localhost:8080)
- **postgres** - PostgreSQL database (localhost:5432)
- **redis** - Redis cache (localhost:6379)

### Optional Tools (use `--profile tools`)

- **pgadmin** - PostgreSQL GUI (http://localhost:5050)
  - Email: `admin@envoxy.local`
  - Password: `admin`
- **redis-commander** - Redis GUI (http://localhost:8081)

Start with tools:

```bash
docker compose --profile tools up -d
```

## Configuration

### Application Configuration

Edit `envoxy.json` to configure your application:

```json
{
  "modules": ["/path/to/your/views.py"],
  "psql_servers": {
    "default": {
      "host": "postgres",
      "port": "5432",
      "db": "envoxy",
      "user": "envoxy",
      "passwd": "dev_password"
    }
  },
  "redis_servers": {
    "default": {
      "bind": "redis:6379",
      "db": "0"
    }
  }
}
```

### Mount Your Application

To develop your own application, mount your code in `docker-compose.yml`:

```yaml
envoxy:
  volumes:
    - ../../src:/usr/envoxy/src
    - /path/to/your/app:/usr/envoxy/app
```

### Database Access

PostgreSQL credentials:

- Host: `localhost` (or `postgres` from within containers)
- Port: `5432`
- Database: `envoxy`
- User: `envoxy`
- Password: `dev_password`

### Redis Access

Redis connection:

- Host: `localhost` (or `redis` from within containers)
- Port: `6379`

## Building & Publishing Packages

Package building and publishing is handled by GitHub Actions. See `.github/workflows/` for:

- `envoxy-publish.yml` - Publishes envoxy package to PyPI
- `envoxyd-manylinux.yml` - Builds and publishes envoxyd manylinux wheels

To trigger a release, create and push a git tag:

```bash
git tag v0.5.10
git push origin v0.5.10
```

## Troubleshooting

### Service won't start

Check logs:

```bash
docker compose logs envoxy
```

### Database connection issues

Ensure postgres is healthy:

```bash
docker compose ps postgres
```

Reset database:

```bash
docker compose down -v
docker compose up -d
```

### Port conflicts

If ports 5432, 6379, or 8080 are already in use, modify them in `docker-compose.yml`:

```yaml
postgres:
  ports:
    - "15432:5432" # Use different host port
```

## Development Workflow

1. Start services: `docker compose up -d`
2. Make code changes in your local editor
3. Changes are reflected immediately (volumes are mounted)
4. View logs: `docker compose logs -f envoxy`
5. Stop services: `docker compose down`

## Cleaning Up

Remove all containers and volumes:

```bash
docker compose down -v
```

Remove images:

```bash
docker compose down --rmi all
```
