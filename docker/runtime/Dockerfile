## Multi-stage Dockerfile: build wheels then create a small runtime image

### Builder stage
FROM ubuntu:24.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential python3.12 python3.12-venv python3.12-dev python3-pip \
    libpq-dev swig make git ca-certificates && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/envoxy
COPY . /usr/envoxy

# Build wheels into /wheels
RUN python3.12 -m venv /opt/venv && /opt/venv/bin/pip install --upgrade pip setuptools wheel && \
    /opt/venv/bin/pip wheel . -w /wheels

### Runtime stage
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/envoxy

# Copy wheels from builder and install without cache
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*

# Copy the project (optional, if you need source in the runtime)
COPY . /usr/envoxy

# Create a non-root user for runtime
RUN useradd -m -s /bin/bash envoxy && chown -R envoxy:envoxy /usr/envoxy
USER envoxy

EXPOSE 8080
CMD ["envoxyd", "run"]
