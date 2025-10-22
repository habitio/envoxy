# Docker Migration Guide

## Changes Made (October 2025)

Docker files have been reorganized into a structured `docker/` directory for better organization and clarity.

### Old Structure → New Structure

| Old Path                      | New Path                                                | Purpose                          |
| ----------------------------- | ------------------------------------------------------- | -------------------------------- |
| `envoxy-ubuntu-20.Dockerfile` | `docker/builder/ubuntu-20.04.Dockerfile`                | Ubuntu 20.04 builder image       |
| `envoxy-ubuntu-24.Dockerfile` | `docker/builder/ubuntu-24.04.Dockerfile`                | Ubuntu 24.04 builder image       |
| `envoxy-runtime.Dockerfile`   | `docker/runtime/Dockerfile`                             | Production runtime image         |
| `Dockerfile`                  | `docker/runtime/Dockerfile.external-builder.deprecated` | Archived (used external builder) |
| `README.docker.md`            | `docker/README.md`                                      | Docker documentation             |

### New Additions

- **`docker/dev/docker-compose.yml`** - Complete local development environment with PostgreSQL, Redis, and optional GUI tools
- **`docker/dev/README.md`** - Comprehensive guide for docker-compose usage

## Updating Your Commands

### Builder Images

**Before:**

```bash
docker build -t envoxy-ubuntu:24.04 -f envoxy-ubuntu-24.Dockerfile .
docker build -t envoxy-ubuntu:20.04 -f envoxy-ubuntu-20.Dockerfile .
```

**After:**

```bash
docker build -t envoxy-ubuntu:24.04 -f docker/builder/ubuntu-24.04.Dockerfile .
docker build -t envoxy-ubuntu:20.04 -f docker/builder/ubuntu-20.04.Dockerfile .
```

### Runtime Image

**Before:**

```bash
docker build -t envoxy:runtime -f envoxy-runtime.Dockerfile .
```

**After:**

```bash
docker build -t envoxy:runtime -f docker/runtime/Dockerfile .
```

## Updating CI/CD Pipelines

If you have CI/CD scripts or GitHub Actions workflows, update the Dockerfile paths:

**GitHub Actions Example:**

```yaml
# Before
- name: Build runtime image
  run: docker build -t envoxy:runtime -f envoxy-runtime.Dockerfile .

# After
- name: Build runtime image
  run: docker build -t envoxy:runtime -f docker/runtime/Dockerfile .
```

**Shell Scripts Example:**

```bash
# Before
BUILD_FILE="envoxy-ubuntu-24.Dockerfile"

# After
BUILD_FILE="docker/builder/ubuntu-24.04.Dockerfile"
```

## Using Docker Compose (New!)

The easiest way to run Envoxy locally is now with docker-compose:

```bash
# Start all services (Envoxy + PostgreSQL + Redis)
cd docker/dev
docker-compose up -d

# View logs
docker-compose logs -f envoxy

# Stop services
docker-compose down

# Start with GUI tools (pgAdmin + Redis Commander)
docker-compose --profile tools up -d
```

See `docker/dev/README.md` for complete documentation.

## Makefile Updates

If your Makefile references Docker files, update the paths:

```makefile
# Before
docker-build:
	docker build -t envoxy:runtime -f envoxy-runtime.Dockerfile .

# After
docker-build:
	docker build -t envoxy:runtime -f docker/runtime/Dockerfile .
```

## Backwards Compatibility

The old Dockerfile names are **removed** from the root directory. If you need them:

1. Update your commands to use the new paths (recommended)
2. Or create symlinks (temporary workaround):
   ```bash
   ln -s docker/builder/ubuntu-24.04.Dockerfile envoxy-ubuntu-24.Dockerfile
   ln -s docker/builder/ubuntu-20.04.Dockerfile envoxy-ubuntu-20.Dockerfile
   ln -s docker/runtime/Dockerfile envoxy-runtime.Dockerfile
   ```

## Documentation

All Docker-related documentation is now in the `docker/` directory:

- **`docker/README.md`** - General Docker usage, builder and runtime images
- **`docker/dev/README.md`** - Docker Compose for local development
- Main `README.md` - Quick start commands (updated)

## Questions?

If you encounter issues after this migration:

1. Check that you updated all paths in your scripts and CI/CD
2. Verify `.dockerignore` is in the project root
3. Review `docker/README.md` for complete examples
4. See `PROJECT-AUDIT.md` for the full project structure audit

## Benefits of New Structure

✅ Clear separation: builder vs runtime vs dev environments  
✅ Consistent naming: ubuntu-20.04, ubuntu-24.04 (not ubuntu-20, ubuntu-24)  
✅ Better organization: all Docker files in one place  
✅ Docker Compose support: one command to start full dev environment  
✅ Archived old files: external-builder approach preserved for reference
