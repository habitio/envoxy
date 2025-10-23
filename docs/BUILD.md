# Build System Documentation

## Overview

Envoxy uses a standardized build system based on Python 3.12+ with a unified build script and Makefile targets.

## Requirements

### System Requirements

- **Python 3.12+** with development headers
- **PostgreSQL** development libraries (`libpq-dev`)
- **systemd** development libraries (`libsystemd-dev`)
- **Build tools** (gcc, make, pkg-config)
- **Git** (for submodule management)

### Ubuntu/Debian Installation

#### Ubuntu 24.04+ (Recommended)

Python 3.12 is the default:

```bash
# Install all requirements
sudo apt-get update
sudo apt-get install -y \
    python3.12 python3.12-dev python3.12-venv \
    libpq-dev libsystemd-dev \
    build-essential pkg-config git
```

#### Ubuntu 22.04 or 20.04

Python 3.12 requires the deadsnakes PPA:

```bash
# Add deadsnakes PPA for Python 3.12
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get update

# Install all requirements
sudo apt-get install -y \
    python3.12 python3.12-dev python3.12-venv \
    libpq-dev libsystemd-dev \
    build-essential pkg-config git
```

## Build Script

The main build script is located at `tools/build.sh` and provides all build operations.

### Available Commands

```bash
./tools/build.sh help        # Show help
./tools/build.sh info        # Show system information
./tools/build.sh clean       # Clean build artifacts
./tools/build.sh envoxyd     # Prepare envoxyd (uWSGI-based)
./tools/build.sh install     # Full system installation
./tools/build.sh develop     # Development mode (editable install)
./tools/build.sh packages    # Build distribution packages
```

### Environment Variables

Configure the build process with these environment variables:

- `PYTHON_VERSION` - Python version to use (default: 3.12)
- `VENV_PATH` - Virtual environment path (default: /opt/envoxy)

**Examples:**

```bash
# Use different Python version
PYTHON_VERSION=3.12 ./tools/build.sh install

# Use custom virtual environment path
VENV_PATH=/home/user/envoxy ./tools/build.sh develop
```

## Makefile Targets

For convenience, Makefile targets wrap the build script:

### Core Targets

```bash
make help           # Show help
make info           # System information
make clean          # Clean build artifacts
make install        # Full installation (requires sudo)
make develop        # Development mode
make packages       # Build distribution packages
```

### Docker Targets

```bash
make docker-dev              # Start development environment (docker-compose)
make docker-dev-down         # Stop development environment
make docker-build-runtime    # Build production runtime image
make docker-build-builder    # Build builder image
```

### Interactive Targets

```bash
make prompt         # Python interactive prompt
make shell          # Python shell
```

## Build Workflows

### 1. Development Setup (Recommended)

For local development with editable installation:

```bash
# Clone and setup
git clone https://github.com/habitio/envoxy.git
cd envoxy
git submodule update --init --recursive

# Install in development mode
make develop

# Activate environment
source /opt/envoxy/bin/activate

# Run tests
pytest tests/
```

### 2. Full System Installation

For system-wide installation (requires sudo):

```bash
# Full installation to /opt/envoxy
sudo make install

# Or specify custom path
sudo VENV_PATH=/usr/local/envoxy make install
```

### 3. Building Distribution Packages

For creating wheels to upload to PyPI:

```bash
# Build packages (requires full install first)
make packages

# Upload to PyPI
twine upload dist/*
cd vendors && twine upload dist/*

# Or upload to test PyPI
twine upload --repository testpypi dist/*
cd vendors && twine upload --repository testpypi dist/*
```

### 4. Docker-based Development

Use Docker for isolated development:

````bash
# Quick start with docker-compose
make docker-dev

# View logs
cd docker/dev && docker-compose logs -f

# Stop
make docker-dev-down

## Notes on systemd Python bindings

Envoxy integrates with systemd for journald and watchdog support. There are multiple ways
to provide the Python bindings:

- Prefer `cysystemd` (binary wheels) in pip-based environments: it usually ships prebuilt
  wheels for common Python versions and avoids building from source. Example:

```bash
python -m pip install cysystemd
````

- Alternatively, use OS-packages in system images to avoid pip building native extensions:

```bash
sudo apt-get install -y python3-systemd libsystemd-dev
```

- If you must build bindings from source (rare), ensure `libsystemd-dev` is installed and
  that your build environment upgrades pip/setuptools/wheel before running pip.

This project prefers `cysystemd` where possible. The code also falls back to the
systemd module if `cysystemd` is not present.

# Or build and run interactively

make docker-build-builder
docker run -it -v $(pwd):/usr/envoxy envoxy-ubuntu:24.04

```

## Build Outputs

### Directory Structure After Build

```

envoxy/
├── build/ # Temporary build artifacts
├── dist/ # Envoxy distribution packages
├── vendors/
│ ├── dist/ # Envoxyd distribution packages
│ └── src/ # Built envoxyd sources
└── envoxy.egg-info/ # Package metadata

````

### Distribution Packages

After running `make packages`:

- **envoxy/dist/**

  - `envoxy-{version}.tar.gz` - Source distribution
  - `envoxy-{version}-py3-none-any.whl` - Wheel distribution

- **vendors/dist/**
  - `envoxyd-{version}.tar.gz` - Source distribution
  - `envoxyd-{version}-py3-none-any.whl` - Wheel distribution

## Python Version Management

### Why Python 3.12?

- **Modern features**: Pattern matching, improved error messages, performance improvements
- **Security**: Latest security patches and updates
- **Long-term support**: Python 3.12 is supported until October 2028
- **Type hints**: Enhanced type system for better code quality
- **Default in Ubuntu 24.04**: No additional setup required

### Version Compatibility

⚠️ **Python 3.12+ is required** by `pyproject.toml` (`requires-python = ">=3.12"`).

While the build script accepts `PYTHON_VERSION` environment variable, using versions below 3.12 is not supported and will fail during package installation.

## Building envoxyd (uWSGI-based)

Envoxyd is built from customized uWSGI sources.

### Build Process

```bash
# Prepare envoxyd sources (from uWSGI submodule)
./tools/build.sh envoxyd

# This will:
# 1. Copy vendors/uwsgi/* to vendors/src/envoxyd/
# 2. Apply envoxyd customizations from vendors/envoxyd/templates/
# 3. Inject run.py into the embedded environment
````

### Manual Build (Advanced)

```bash
cd vendors/src/envoxyd
python3.12 uwsgiconfig.py --build flask
```

## Troubleshooting

### Common Issues

#### 1. Python Not Found

```
Error: Python 3.12 not found!
```

**Solution:**

```bash
sudo apt-get install python3.12 python3.12-dev python3.12-venv
```

#### 2. Permission Denied

```
Error: Permission denied creating /opt/envoxy
```

**Solution:** Use sudo or change VENV_PATH:

```bash
sudo make install
# OR
VENV_PATH=~/envoxy make develop
```

#### 3. Missing Dependencies

```
Error: libpq-fe.h: No such file or directory
```

**Solution:** Install PostgreSQL development libraries:

```bash
sudo apt-get install libpq-dev
```

#### 4. Git Submodule Issues

```
Error: vendors/uwsgi not found
```

**Solution:** Initialize submodules:

```bash
git submodule update --init --recursive
```

#### 5. Build Cache Issues

If you encounter strange build errors:

```bash
# Clean everything
make clean
rm -rf build/ dist/ *.egg-info vendors/dist/ vendors/src/

# Rebuild
make install
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build and Test

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
        with:
          submodules: recursive

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install system dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y libpq-dev libsystemd-dev

      - name: Install in development mode
        run: |
          ./tools/build.sh develop

      - name: Run tests
        run: |
          source /opt/envoxy/bin/activate
          pytest tests/

      - name: Build packages
        run: |
          ./tools/build.sh packages

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: packages
          path: |
            dist/
            vendors/dist/
```

### GitLab CI Example

```yaml
build:
  image: ubuntu:24.04
  script:
    - apt-get update
    - apt-get install -y python3.12 python3.12-dev python3.12-venv libpq-dev libsystemd-dev build-essential git
    - git submodule update --init --recursive
    - ./tools/build.sh packages
  artifacts:
    paths:
      - dist/
      - vendors/dist/
```

## Performance Tips

### Faster Builds

1. **Use ccache** for faster C compilation:

   ```bash
   sudo apt-get install ccache
   export CC="ccache gcc"
   ```

2. **Parallel builds** (if supported):

   ```bash
   export MAKEFLAGS="-j$(nproc)"
   ```

3. **Skip tests** during development:
   ```bash
   make develop  # Instead of make install
   ```

### Build Time Expectations

- **Development install**: ~2-3 minutes
- **Full install**: ~5-7 minutes
- **Package build**: ~8-10 minutes

Times depend on system specs and network speed.

## Advanced Topics

### Custom Build Configurations

Create a build configuration file:

```bash
# .envoxy-build.conf
export PYTHON_VERSION=3.12
export VENV_PATH=/opt/envoxy
export CFLAGS="-O3 -march=native"
```

Use it:

```bash
source .envoxy-build.conf
./tools/build.sh install
```

### Cross-compilation (Advanced)

For building on different architectures:

```bash
# Example: Build for ARM64 on x86_64 using Docker
docker buildx build --platform linux/arm64 \
    -f docker/runtime/Dockerfile \
    -t envoxy:runtime-arm64 .
```

## Support

- **Documentation**: See `docs/` directory
- **Issues**: https://github.com/habitio/envoxy/issues
- **Docker Help**: See `docker/README.md`
- **CI/CD Guide**: See `docs/CI-CD.md`

## See Also

- `CONTRIBUTING.md` - Contribution guidelines
- `PROJECT-STATUS.md` - Current project status
- `docs/requirements-management.md` - Dependency management
- `docker/README.md` - Docker documentation
- `docker/MIGRATION.md` - Docker migration guide
- `tests/README.md` - Testing guide
