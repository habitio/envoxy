## Multi-stage Dockerfile: build wheels then create a small runtime image

### Builder stage
FROM ubuntu:24.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential python3.12 python3.12-venv python3.12-dev python3-pip \
    libpq-dev swig make git ca-certificates \
    # Install docker CLI so cibuildwheel can invoke Docker from inside the builder
    docker.io \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/envoxy
COPY . /usr/envoxy

# Build and install packages in venv (this compiles uwsgi via InstallCommand)
# Using /opt/envoxy to match the project's standard workflow
RUN python3.12 -m venv /opt/envoxy \
    && /opt/envoxy/bin/pip install --upgrade pip setuptools wheel \
    && bash tools/build.sh envoxyd \
    && /opt/envoxy/bin/pip install . \
    && cd vendors && /opt/envoxy/bin/python setup.py install && cd ..

### Runtime stage
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# Install Python 3.12 runtime dependencies but avoid pulling the system
# libpython package: we prefer the libpython copied into the venv to avoid
# ABI mismatches with compiled extensions.
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/envoxy

# Copy the entire venv from builder (includes compiled uwsgi)
COPY --from=builder /opt/envoxy /opt/envoxy

# Add venv to PATH
ENV PATH="/opt/envoxy/bin:$PATH"
ENV LD_LIBRARY_PATH="/opt/envoxy/lib:${LD_LIBRARY_PATH}"

# Copy the project (optional, if you need source in the runtime)
COPY . /usr/envoxy

# Create a non-root user for runtime
RUN useradd -m -s /bin/bash envoxy && chown -R envoxy:envoxy /usr/envoxy
USER envoxy

EXPOSE 8080
CMD ["envoxyd", "run"]
