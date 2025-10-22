# Docker: builder and runtime images for envoxy

This project provides two kinds of Docker images to support development and production workflows:

- **Builder images** (interactive) — `docker/builder/ubuntu-24.04.Dockerfile` and `docker/builder/ubuntu-20.04.Dockerfile`. These are developer images you run locally to compile `envoxyd`, run `make packages`, and upload/distribute wheels.

- **Runtime image** (multi-stage) — `docker/runtime/Dockerfile`. This file builds wheels in a builder stage and then installs them into a small `python:3.12-slim` runtime image. Use this for production containers.

## Quick developer flow (recommended)

1. Build the builder image (24.04 example):

```bash
docker build --build-arg UID=$(id -u) --build-arg GID=$(id -g) \
  -t envoxy-ubuntu:24.04 -f docker/builder/ubuntu-24.04.Dockerfile .
```

2. Run it interactively with your source mounted so build artifacts appear on the host:

```bash
docker run --rm -it \
  -v $(pwd):/usr/envoxy \
  -v /path/to/other/volume:/home/habit/service \
  -e TWINE_USERNAME -e TWINE_PASSWORD \
  envoxy-ubuntu:24.04
```

3. Inside the container:

```bash
cd /usr/envoxy
# bump version if needed, then
make packages
source /opt/envoxy/bin/activate
pip install -r requirements.dev
twine upload --repository testpypi dist/*
cd vendors
twine upload dist/*
```

Notes:

- Use `--build-arg UID=$(id -u)` to ensure the container user matches your host UID and avoid permission issues when bind-mounting the project.
- Prefer environment variables for Twine credentials or mount `~/.pypirc`.

## Production image build (multi-stage)

You can create a small runtime image with `docker/runtime/Dockerfile`. It builds wheels in a builder stage and installs them into `python:3.12-slim`.

Build the runtime image:

```bash
docker build -t envoxy-runtime:latest -f docker/runtime/Dockerfile .
```

This output is a lean image with only runtime deps (libpq) and your installed package. Use orchestration tooling (docker-compose, Kubernetes) to run it and map ports securely.

## Security & reproducibility tips

- Pin versions in `requirements.txt` for reproducible builds.
- Use CI to build wheels and publish artifacts rather than interactive twine pushes from developer machines when possible.
- Keep credentials out of Dockerfiles; use secrets management in CI or mount a secure `.pypirc` at runtime.
