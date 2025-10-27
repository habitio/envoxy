#!/bin/bash
# Envoxy Development Helper Scripts
# Usage: source dev.sh

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Envoxy Development Environment${NC}"
echo "=============================="
echo ""

# Build packages (envoxy + envoxyd wheels)
envoxy-build() {
    echo -e "${YELLOW}Building envoxy and envoxyd packages...${NC}"
    docker compose --profile tools run --rm builder bash -s <<'BASH'
set -e
cd /usr/envoxy

# Activate virtual environment
source /opt/envoxy/bin/activate

# Clean old distributions (volumes are mounted, so clean contents)
rm -rf dist/* vendors/dist/*
mkdir -p dist vendors/dist

# Install wheel/twine and packaging helpers if not present (auditwheel and cibuildwheel needed to produce manylinux wheels)
pip install --quiet wheel twine auditwheel cibuildwheel || true

# Build envoxy package using the packaging venv python
echo "Building envoxy package..."
/opt/envoxy/bin/python setup.py sdist bdist_wheel
# Repair wheel for manylinux compatibility (if auditwheel is available)
    if /opt/envoxy/bin/python -m pip show cibuildwheel >/dev/null 2>&1 && command -v docker >/dev/null 2>&1; then
    echo "cibuildwheel: building manylinux wheels for envoxy (this may take a while)"
    mkdir -p /usr/envoxy/wheelhouse_cibuildwheel/envoxy || true
    # Run cibuildwheel for the root package and emit wheels into the wheelhouse
    /opt/envoxy/bin/python -m cibuildwheel --output-dir /usr/envoxy/wheelhouse_cibuildwheel/envoxy --platform linux || true
    # Copy produced wheels back into dist/
    cp -v /usr/envoxy/wheelhouse_cibuildwheel/envoxy/*.whl dist/ 2>/dev/null || true
else
    # Fall back to auditwheel repair if cibuildwheel isn't available
        if /opt/envoxy/bin/python -m pip show auditwheel >/dev/null 2>&1; then
        mkdir -p /usr/envoxy/wheelhouse || true
        for w in dist/*.whl; do /opt/envoxy/bin/python -m auditwheel repair "$w" -w /usr/envoxy/wheelhouse || true; done
        echo "auditwheel: repaired wheels (if any) -> /usr/envoxy/wheelhouse"
        # Copy repaired wheels back into dist/ so publishing picks them up
        cp -v /usr/envoxy/wheelhouse/*.whl dist/ 2>/dev/null || true
    else
        echo "auditwheel: not installed in venv; wheels will not be repaired"
    fi
fi

# Build envoxyd package (preparation already done in Dockerfile)
echo "Building envoxyd package..."
cd vendors
/opt/envoxy/bin/python setup.py sdist bdist_wheel
# Repair envoxyd wheel for manylinux compatibility
        if /opt/envoxy/bin/python -m pip show cibuildwheel >/dev/null 2>&1 && command -v docker >/dev/null 2>&1; then
            echo "cibuildwheel: building manylinux wheels for envoxyd"
            mkdir -p /usr/envoxy/wheelhouse_cibuildwheel/envoxyd || true
            # Build from repo root so cibuildwheel has access to pyproject.toml
            # Compile uWSGI inside the manylinux container (not using the Ubuntu 24.04 pre-built binary)
            cd /usr/envoxy
            # Allow overriding CIBW_BUILD from the environment; default to cp312-*
            CIBW_BUILD="${CIBW_BUILD:-cp312-*}" \
            CIBW_BUILD_FRONTEND="build[uv]" \
            echo "cibuildwheel: CIBW_BUILD=${CIBW_BUILD} (targets)" && \
            # run our patch_and_build inside the uWSGI source dir so uwsgiconfig.py is present
            # cibuildwheel v3 no longer supports the {python} placeholder; the container's
            # `python` binary already points to the interpreter used for this build, so
            # call the script without placeholders and let it use `python` inside the container.
            CIBW_BEFORE_BUILD="cd {package}/uwsgi && /bin/sh /project/docker/dev/patch_and_build.sh" \
            /opt/envoxy/bin/python -m cibuildwheel \
                --output-dir /usr/envoxy/wheelhouse_cibuildwheel/envoxyd \
                --platform linux \
                vendors || true
            cd /usr/envoxy/vendors
            # Copy produced wheels back into dist/ (we're back in vendors/ so target is ./dist/)
            cp -v /usr/envoxy/wheelhouse_cibuildwheel/envoxyd/*.whl dist/ 2>/dev/null || true
        else
    if /opt/envoxy/bin/python -m pip show auditwheel >/dev/null 2>&1; then
        mkdir -p /usr/envoxy/wheelhouse || true
        for w in vendors/dist/*.whl; do /opt/envoxy/bin/python -m auditwheel repair "$w" -w /usr/envoxy/wheelhouse || true; done
        echo "auditwheel: repaired vendors wheels (if any) -> /usr/envoxy/wheelhouse"
        # Copy repaired wheels back into vendors/dist/ so publishing picks them up
        cp -v /usr/envoxy/wheelhouse/*.whl vendors/dist/ 2>/dev/null || true
    else
        echo "auditwheel: not installed in venv; vendors wheels will not be repaired"
    fi
fi
cd ..

# If auditwheel produced repaired wheels, copy them into dist locations
if [ -d /usr/envoxy/wheelhouse ]; then
    echo "Copying repaired wheels to dist/ and vendors/dist/"
    mkdir -p dist vendors/dist || true
    cp -v /usr/envoxy/wheelhouse/*.whl dist/ 2>/dev/null || true
    cp -v /usr/envoxy/wheelhouse/*.whl vendors/dist/ 2>/dev/null || true
    echo "wheelhouse contents:"
    ls -lah /usr/envoxy/wheelhouse || true
fi

echo "Packages built successfully!"
echo "Envoxy: $(ls -1 dist/*.whl 2>/dev/null | head -1)"
echo "Envoxyd: $(ls -1 vendors/dist/*.whl 2>/dev/null | head -1)"
BASH
    echo -e "${GREEN}✓ Packages built in dist/ and vendors/dist/${NC}"
}

# Install packages to local venv
envoxy-install-local() {
    echo -e "${YELLOW}Installing packages to /opt/envoxy...${NC}"
    docker compose --profile tools run --rm builder bash -c "
        source /opt/envoxy/bin/activate &&
        cd /usr/envoxy &&
        pip install -e . &&
        cd vendors &&
        pip install -e .
    "
    echo -e "${GREEN}✓ Installed to /opt/envoxy${NC}"
}

# Publish to PyPI (requires credentials)
envoxy-publish() {
    local repo="${1:-testpypi}"
    echo -e "${YELLOW}Publishing to ${repo}...${NC}"
    
    # Check if .pypirc exists
    if [ ! -f ~/.pypirc ]; then
        echo -e "${RED}Error: ~/.pypirc not found${NC}"
        echo "Create ~/.pypirc with your PyPI credentials:"
        echo ""
        echo "[distutils]"
        echo "index-servers ="
        echo "    pypi"
        echo "    testpypi"
        echo ""
        echo "[pypi]"
        echo "username = __token__"
        echo "password = pypi-YOUR-API-TOKEN"
        echo ""
        echo "[testpypi]"
        echo "repository = https://test.pypi.org/legacy/"
        echo "username = __token__"
        echo "password = pypi-YOUR-TEST-API-TOKEN"
        echo ""
        echo "Also update docker-compose.yml to mount it:"
        echo "  - ~/.pypirc:/root/.pypirc:ro"
        return 1
    fi
    
    if [ "$repo" = "pypi" ]; then
        echo -n "Are you sure you want to publish to PRODUCTION PyPI? (yes/no): "
        read confirm
        if [ "$confirm" != "yes" ]; then
            echo "Cancelled."
            return 1
        fi
    fi
    
    docker compose --profile tools run --rm builder bash -c "
        set -e
        source /opt/envoxy/bin/activate &&
        pip install --quiet twine &&
        echo 'Uploading envoxy package...' &&
        twine upload --repository ${repo} dist/* &&
        echo 'Uploading envoxyd package...' &&
        cd vendors && twine upload --repository ${repo} dist/*
    " && echo -e "${GREEN}✓ Published to ${repo}${NC}" || echo -e "${RED}✗ Failed to publish${NC}"
}

# Export packages to host
envoxy-export() {
    local dest_arg="$1"
    # If no destination passed, default to repository-root/packages
    if [ -z "$dest_arg" ]; then
        # Try to find repo root via git
        if git_root=$(git rev-parse --show-toplevel 2>/dev/null); then
            dest="${git_root}/packages"
        else
            # Fallback: assume two levels up from this script (repo/docker/dev)
            script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
            dest=$(cd "${script_dir}/../.." && pwd -P)/packages
        fi
    else
        dest="$dest_arg"
    fi

    echo -e "${YELLOW}Exporting packages to ${dest}...${NC}"
    mkdir -p "$dest"

    # Use a bind-mount so files are written directly into the host destination directory.
    # This avoids docker cp failures for short-lived run containers.
    # Compute absolute path for bind-mount; fallback if realpath is unavailable
    if command -v realpath >/dev/null 2>&1; then
        DEST_ABS=$(realpath "$dest")
    else
        # fallback: use python to resolve absolute path, or pwd
        DEST_ABS=$(python -c "import os,sys; print(os.path.abspath(sys.argv[1]))" "$dest" 2>/dev/null || pwd -P)
    fi

    docker compose --profile tools run --rm \
        -v "${DEST_ABS}:/tmp/envoxy-export:rw" \
        builder bash -s <<'BASH'
set -e
cp -v dist/*.whl dist/*.tar.gz /tmp/envoxy-export/ 2>/dev/null || true
cp -v vendors/dist/*.whl vendors/dist/*.tar.gz /tmp/envoxy-export/ 2>/dev/null || true
sync || true
BASH

    RESOLVED_DEST=${DEST_ABS:-$dest}
    echo -e "${GREEN}✓ Packages exported to ${RESOLVED_DEST}${NC}"

    # Post-process on host: try to repair wheels with auditwheel (if installed locally)
    # and ensure files are owned by the invoking user (avoid root-owned files).
    if command -v python >/dev/null 2>&1 && python -c 'import importlib,sys; importlib.util.find_spec("auditwheel") or sys.exit(1)' >/dev/null 2>&1; then
        echo -e "${YELLOW}auditwheel found on host — repairing exported wheels into ${RESOLVED_DEST}/wheelhouse${NC}"
        mkdir -p "${RESOLVED_DEST}/wheelhouse"
        for w in "${RESOLVED_DEST}"/*.whl; do
            [ -f "$w" ] || continue
            echo "repairing: $w"
            python -m auditwheel repair "$w" -w "${RESOLVED_DEST}/wheelhouse" || true
        done
        echo -e "${GREEN}auditwheel repair complete (if any wheels repaired).${NC}"
    else
        echo -e "${YELLOW}auditwheel not found on host — skipping host-side wheel repair. To repair, install auditwheel or rebuild in builder with auditwheel available.${NC}"
    fi

    # Fix ownership of exported files (they may be root-owned); try chown, fall back to sudo chown
    USER_UID=$(id -u)
    USER_GID=$(id -g)
    echo -e "${YELLOW}Ensuring exported files are owned by UID:${USER_UID} GID:${USER_GID}${NC}"
    if chown ${USER_UID}:${USER_GID} "${RESOLVED_DEST}"/* 2>/dev/null; then
        echo -e "${GREEN}Ownership fixed.${NC}"
    else
        echo -e "${YELLOW}chown failed without sudo; attempting with sudo...${NC}"
        if command -v sudo >/dev/null 2>&1; then
            sudo chown ${USER_UID}:${USER_GID} "${RESOLVED_DEST}"/* || echo -e "${RED}sudo chown failed; files may remain root-owned${NC}"
        else
            echo -e "${RED}sudo not available; files may remain root-owned${NC}"
        fi
    fi
}

# Clean build artifacts
envoxy-clean() {
    echo -e "${YELLOW}Cleaning build artifacts...${NC}"
    docker compose --profile tools run --rm builder bash -c "
        cd /usr/envoxy &&
        rm -rf dist/* vendors/dist/* build/ *.egg-info vendors/*.egg-info
    "
    echo -e "${GREEN}✓ Cleaned${NC}"
}

# Run tests
envoxy-test() {
    echo -e "${YELLOW}Running tests...${NC}"
    docker compose --profile tools run --rm builder bash -c "
        source /opt/envoxy/bin/activate &&
        cd /usr/envoxy &&
        pytest tests/
    "
}

# Interactive shell in builder
envoxy-shell() {
    echo -e "${YELLOW}Opening shell in builder container...${NC}"
    docker compose --profile tools run --rm builder /bin/bash
}

# Show help
envoxy-help() {
    echo "Available commands:"
    echo "  envoxy-build          - Build envoxy and envoxyd wheel packages"
    echo "  envoxy-install-local  - Install packages to /opt/envoxy venv"
    echo "  envoxy-publish [repo] - Publish to PyPI (testpypi|pypi)"
    echo "  envoxy-export [dir]   - Export packages to local directory"
    echo "  envoxy-clean          - Clean build artifacts"
    echo "  envoxy-test           - Run test suite"
    echo "  envoxy-shell          - Open interactive shell in builder"
    echo "  envoxy-help           - Show this help"
    echo ""
    echo "Examples:"
    echo "  envoxy-build                    # Build packages"
    echo "  envoxy-publish testpypi         # Publish to test PyPI"
    echo "  envoxy-export ./my-packages     # Export to local dir"
}

echo "Helper functions loaded. Type 'envoxy-help' for usage."
