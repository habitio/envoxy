# Envoxy Package Build & Publish Workflow

## Overview

Complete workflow for developing, building, and publishing envoxy packages using Docker.

## Prerequisites

- Docker & Docker Compose V2
- Python 3.12+ (for local development)
- PyPI account and API tokens (for publishing)

## Workflow Steps

### 1. Development Setup

```bash
cd docker/dev

# Load helper functions
source dev.sh

# Start development services (optional, for testing runtime)
docker compose up -d
```

### 2. Build Packages

Build both envoxy and envoxyd wheel packages:

```bash
# Using helper function
envoxy-build

# Or manually
docker compose --profile tools run --rm builder make packages
```

**Output:**

- `dist/envoxy-0.5.0-py3-none-any.whl`
- `dist/envoxy-0.5.0.tar.gz`
- `vendors/dist/envoxyd-0.4.0-py3-none-any.whl`
- `vendors/dist/envoxyd-0.4.0.tar.gz`

### 3. Test Installation (Optional)

Test installation in the builder container:

```bash
# Install to /opt/envoxy venv
envoxy-install-local

# Or open interactive shell
envoxy-shell

# Inside shell:
source /opt/envoxy/bin/activate
python -c "import envoxy; print(envoxy.__version__)"
envoxyd --help
```

### 4. Export Packages to Host

Export built packages to your local machine:

```bash
# Export to ./packages directory
envoxy-export ./packages

# Packages are now available locally
ls -l ./packages/
```

### 5. Test in Local Environment

Install the exported packages in your local Python environment:

```bash
# Create test venv
python3.12 -m venv /tmp/test-envoxy
source /tmp/test-envoxy/bin/activate

# Install from local wheels
pip install ./packages/envoxy-*.whl
pip install ./packages/envoxyd-*.whl

# Test
python -c "import envoxy; print('Success!')"
```

### 6. Publish to Test PyPI

Test the publishing process first:

```bash
# Setup ~/.pypirc with test PyPI credentials
# See Configuration section below

# Publish to test PyPI
envoxy-publish testpypi

# Test installation from test PyPI
pip install --index-url https://test.pypi.org/simple/ envoxy
```

### 7. Publish to Production PyPI

When ready for production release:

```bash
# Publish to production PyPI
envoxy-publish pypi
```

## Configuration

### PyPI Credentials

Create `~/.pypirc`:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-AgENdGVzdC...your-token-here

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-AgENdGVzdC...your-test-token-here
```

Update docker-compose.yml to mount credentials:

```yaml
builder:
  volumes:
    - ../../:/usr/envoxy
    - ~/.pypirc:/root/.pypirc:ro # Add this line
```

## Complete Example Session

```bash
# Terminal session example
cd /home/vorjdux/Projects/muzzley/envoxy/docker/dev

# Load helpers
$ source dev.sh
Envoxy Development Environment
==============================
Helper functions loaded. Type 'envoxy-help' for usage.

# Build packages
$ envoxy-build
Building envoxy and envoxyd packages...
✓ Building envoxy package...
✓ Building envoxyd package...
✓ Packages built in dist/ and vendors/dist/

# Test locally
$ envoxy-install-local
Installing packages to /opt/envoxy...
✓ Installed to /opt/envoxy

# Export for local testing
$ envoxy-export ./my-build
Exporting packages to ./my-build...
✓ Packages exported to ./my-build

# Publish to test PyPI
$ envoxy-publish testpypi
Publishing to testpypi...
Uploading envoxy-0.5.0-py3-none-any.whl
Uploading envoxyd-0.4.0-py3-none-any.whl
✓ Published to testpypi

# Publish to production PyPI
$ envoxy-publish pypi
Publishing to pypi...
Are you sure you want to publish to PRODUCTION PyPI? (yes/no): yes
Uploading envoxy-0.5.0-py3-none-any.whl
Uploading envoxyd-0.4.0-py3-none-any.whl
✓ Published to pypi
```

## Manual Commands (Without Helpers)

### Build

```bash
docker compose --profile tools run --rm builder bash -c "
    cd /usr/envoxy &&
    make packages
"
```

### Publish

```bash
docker compose --profile tools run --rm builder bash -c "
    cd /usr/envoxy &&
    pip install twine &&
    twine upload --repository testpypi dist/* &&
    cd vendors &&
    twine upload --repository testpypi dist/*
"
```

## Original Workflow Comparison

### Old Workflow (Ubuntu 18 container)

```bash
$ docker build --no-cache -t envoxy-ubuntu:18.04 -f envoxy-ubuntu-18.Dockerfile .
$ docker run -it -v /home/vorjdux/Projects/muzzley/envoxy:/usr/envoxy envoxy-ubuntu:18.04
$ cd /usr/envoxy
$ make packages
$ source /opt/envoxy/bin/activate
$ pip install -r requirements.dev
$ twine upload --repository testpypi dist/*
$ cd vendors
$ twine upload dist/*
```

### New Workflow (Docker Compose + helpers)

```bash
$ cd docker/dev
$ source dev.sh
$ envoxy-build
$ envoxy-publish testpypi
```

## Benefits of New Workflow

1. **Simpler**: One-line commands vs multi-step process
2. **Faster**: Cached Docker layers, parallel builds
3. **Modern**: Ubuntu 24.04 + Python 3.12
4. **Consistent**: Same environment for all developers
5. **Isolated**: No host contamination
6. **Documented**: Clear helper functions and README

## Troubleshooting

### Clean build artifacts

```bash
envoxy-clean
envoxy-build
```

### Check builder environment

```bash
envoxy-shell

# Inside container:
ls -la /opt/envoxy/bin/
which envoxyd
python --version
```

### Manual package inspection

```bash
docker compose --profile tools run --rm builder bash -c "
    ls -lh dist/
    ls -lh vendors/dist/
"
```

## See Also

- `README.md` - Docker dev environment overview
- `dev.sh` - Helper script source code
- `../../docs/BUILD.md` - Build system documentation
- `../../QUICK-REFERENCE.md` - Quick reference guide
