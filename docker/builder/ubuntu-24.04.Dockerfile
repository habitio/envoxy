FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ARG USER=envoxy
ARG UID=1000
ARG GID=1000
ENV HOME=/home/${USER}

# Install system packages required for building wheels and uWSGI (envoxyd)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3.12 python3.12-venv python3.12-dev python3-pip \
    git curl ca-certificates \
    libpq-dev libssl-dev swig pkg-config \
    make gcc pkgconf \
    python3.12-distutils \
    && rm -rf /var/lib/apt/lists/*

# Create user with matching UID so bind-mounted files remain writable
RUN groupadd -g ${GID} ${USER} || true \
    && useradd -m -u ${UID} -g ${GID} -s /bin/bash ${USER}

# Create venv for packaging and testing
RUN python3.12 -m venv /opt/envoxy && \
    /opt/envoxy/bin/pip install --upgrade pip setuptools wheel twine

# Create working dir and ensure permissions
WORKDIR /usr/envoxy
RUN chown -R ${USER}:${USER} /usr/envoxy /opt/envoxy || true

# Switch to unprivileged user by default in interactive runs
USER ${USER}
ENV PATH="/opt/envoxy/bin:${PATH}"

# Default entrypoint: drop into bash for interactive use
ENTRYPOINT ["/bin/bash"]
