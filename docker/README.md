# Docker: Local Development Environment

This directory provides Docker configuration for local development and testing of envoxy applications.

## Building & Publishing

**Package building and publishing is handled by GitHub Actions.** See `.github/workflows/` for:

- `envoxy-publish.yml` - Publishes envoxy package to PyPI
- `envoxyd-manylinux.yml` - Builds and publishes envoxyd manylinux wheels

To trigger a release, create and push a git tag:

```bash
git tag v0.6.10
git push origin v0.6.10
```

## Local Development

For local development and testing, use `docker/dev/`:

```bash
cd docker/dev

# Start all services (postgres, redis, envoxy runtime)
docker compose up -d

# View logs
docker compose logs -f envoxy

# Stop services
docker compose down
```

See `docker/dev/README.md` for detailed local development instructions.

## Runtime Image

The `docker/runtime/Dockerfile` provides a development runtime image based on Ubuntu 24.04. It:

- Installs Python 3.12 and dependencies
- Installs envoxy and envoxyd in development mode (editable install)
- Sets up a non-root user for security

Build the runtime image:

```bash
docker build -t envoxy-runtime:latest -f docker/runtime/Dockerfile .
```

This image is used by `docker/dev/docker-compose.yml` for local testing.
