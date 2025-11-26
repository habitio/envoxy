# Runtime Dockerfile for local development
# For production builds, use GitHub Actions workflows

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# Install Python 3.12 and build/runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    python3-pip \
    # Build dependencies
    build-essential \
    gcc \
    g++ \
    # PostgreSQL client libraries
    libpq5 \
    libpq-dev \
    # ZeroMQ libraries
    libzmq5 \
    libzmq3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/envoxy

# Create venv
RUN python3.12 -m venv /opt/envoxy

# Copy project files
COPY . /usr/envoxy

# Install envoxy and envoxyd in development mode
RUN /opt/envoxy/bin/pip install --upgrade pip setuptools wheel && \
    /opt/envoxy/bin/pip install -e . && \
    cd vendors && /opt/envoxy/bin/pip install -e . && cd ..

# Add venv to PATH
ENV PATH="/opt/envoxy/bin:$PATH"
ENV LD_LIBRARY_PATH="/opt/envoxy/lib:${LD_LIBRARY_PATH}"

# Create non-root user
RUN useradd -m -s /bin/bash envoxy && chown -R envoxy:envoxy /usr/envoxy
USER envoxy

EXPOSE 8080
CMD ["envoxyd", "/etc/uwsgi/uwsgi.ini"]
