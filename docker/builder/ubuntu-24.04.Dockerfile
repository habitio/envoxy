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
    patchelf \
    && rm -rf /var/lib/apt/lists/*

# Create user with matching UID so bind-mounted files remain writable
RUN groupadd -g ${GID} ${USER} || true \
    && useradd -m -u ${UID} -g ${GID} -s /bin/bash ${USER}

# Create venv for packaging and testing
RUN python3.12 -m venv /opt/envoxy && \
    /opt/envoxy/bin/pip install --upgrade pip setuptools wheel twine
RUN /opt/envoxy/bin/pip install auditwheel


# Copy the system libpython into the venv so compiled binaries can reference
# a colocated interpreter shared object at runtime. This helps make the
# runtime image portable when we copy /opt/envoxy into the final image.
RUN python3.12 - <<'PY'
import sysconfig, shutil, os
libname = sysconfig.get_config_var('LDLIBRARY')
libdir = sysconfig.get_config_var('LIBDIR')
src = os.path.join(libdir, libname)
dst_dir = '/opt/envoxy/lib'
os.makedirs(dst_dir, exist_ok=True)
if os.path.exists(src):
    dst = os.path.join(dst_dir, libname)
    print('Copying', src, 'to', dst)
    shutil.copy(src, dst)
else:
    print('Warning: libpython not found at', src)
PY

# Create working dir and ensure permissions
WORKDIR /usr/envoxy
RUN chown -R ${USER}:${USER} /usr/envoxy /opt/envoxy || true

# Switch to unprivileged user by default in interactive runs
USER ${USER}
ENV PATH="/opt/envoxy/bin:${PATH}"

# Default entrypoint: drop into bash for interactive use
ENTRYPOINT ["/bin/bash"]
