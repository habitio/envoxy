# Docker Compose Development Environment

This directory contains Docker Compose configuration for local development with all required services.

## Quick Start

1. **Start all services:**

   ```bash
   cd docker/dev
   docker-compose up -d
   ```

2. **View logs:**

   ```bash
   docker-compose logs -f envoxy
   ```

3. **Stop services:**
   ```bash
   docker-compose down
   ```

## Services

### Core Services (Always Running)

- **envoxy** - Main application (port 8080)
- **postgres** - PostgreSQL 16 database (port 5432)
- **redis** - Redis 7 cache (port 6379)

### Optional Tools (Profile: `tools`)

Start with: `docker-compose --profile tools up -d`

- **redis-commander** - Redis GUI (port 8081)
- **pgadmin** - PostgreSQL GUI (port 5050)
  - Email: `admin@envoxy.local`
  - Password: `admin`

## Configuration

### Environment Variables

Edit `docker-compose.yml` to customize:

- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` - Database credentials
- `REDIS_HOST`, `REDIS_PORT` - Redis connection
- `LOG_LEVEL` - Application log level (DEBUG, INFO, WARNING, ERROR)

### Volumes

Data is persisted in Docker volumes:

- `postgres_data` - PostgreSQL data directory
- `redis_data` - Redis persistence
- `pgadmin_data` - pgAdmin configuration

To reset all data:

```bash
docker-compose down -v
```

## Development Workflow

### Running Tests Inside Container

```bash
# Enter the running container
docker-compose exec envoxy bash

# Run tests
pytest tests/

# Run specific test
pytest tests/test_postgresql.py -v
```

### Rebuilding After Code Changes

```bash
# Rebuild and restart
docker-compose up -d --build
```

### Viewing Database

**Option 1: Using pgAdmin (GUI)**

1. Start with tools profile: `docker-compose --profile tools up -d`
2. Open http://localhost:5050
3. Add server:
   - Name: `Envoxy Local`
   - Host: `postgres`
   - Port: `5432`
   - Username: `envoxy`
   - Password: `dev_password`

**Option 2: Using psql CLI**

```bash
docker-compose exec postgres psql -U envoxy -d envoxy
```

### Viewing Redis

**Option 1: Using Redis Commander (GUI)**

1. Start with tools profile: `docker-compose --profile tools up -d`
2. Open http://localhost:8081

**Option 2: Using redis-cli**

```bash
docker-compose exec redis redis-cli
```

## Common Tasks

### Reset Database

```bash
docker-compose stop postgres
docker-compose rm -f postgres
docker volume rm dev_postgres_data
docker-compose up -d postgres
```

### Reset Redis Cache

```bash
docker-compose exec redis redis-cli FLUSHALL
```

### View Container Resource Usage

```bash
docker-compose stats
```

### Access Application Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f envoxy
docker-compose logs -f postgres
docker-compose logs -f redis
```

## Troubleshooting

### Port Already in Use

If you see "port already allocated" error:

```bash
# Check what's using the port
sudo lsof -i :8080

# Change port in docker-compose.yml or stop conflicting service
```

### Permission Issues

If you encounter permission issues with volumes:

```bash
# Fix ownership
docker-compose exec envoxy chown -R $(id -u):$(id -g) /app
```

### Database Connection Refused

Wait for PostgreSQL to be ready:

```bash
docker-compose logs postgres
# Look for "database system is ready to accept connections"
```

### Clean Start

Remove all containers, volumes, and images:

```bash
docker-compose down -v --rmi local
docker-compose up -d --build
```

## Production Deployment

⚠️ **This docker-compose.yml is for DEVELOPMENT only!**

For production:

- Use separate docker-compose.prod.yml
- Remove exposed ports for postgres/redis
- Use Docker secrets for credentials
- Set up proper networking and security
- Use external managed databases
- Enable SSL/TLS
- Configure proper logging and monitoring

See `../runtime/Dockerfile` for production container image.
