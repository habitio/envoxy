#!/bin/bash
set -euo pipefail

# Envoxy Build Script
# Standardized build system for Envoxy framework and envoxyd daemon
# Requires: Python 3.12+, build tools, PostgreSQL development libraries

# Configuration
PYTHON_VERSION="${PYTHON_VERSION:-3.12}"
PYTHON="python${PYTHON_VERSION}"
VENV_PATH="${VENV_PATH:-/opt/envoxy}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}➜${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

# Help
help() {
    cat << EOF

ENVOXY BUILD SYSTEM
===================

Commands available:
  $ make help                Show Makefile help
  $ make envoxyd             Build envoxyd from uWSGI sources
  $ make build               Full build (envoxy + envoxyd)
  $ sudo make install        System-wide installation to ${VENV_PATH}
  $ make packages            Build distribution packages (wheels)
  $ make clean               Clean build artifacts
  $ make [prompt|shell]      Interactive Python shell

Environment Variables:
  PYTHON_VERSION             Python version to use (default: 3.12)
  VENV_PATH                  Virtual environment path (default: /opt/envoxy)

Requirements:
  - Python ${PYTHON_VERSION} with development headers
  - PostgreSQL development libraries (libpq-dev)
  - systemd development libraries (libsystemd-dev)
  - Build essentials (gcc, make, pkg-config)

Examples:
  $ ./tools/build.sh clean         # Clean build artifacts
  $ ./tools/build.sh install       # Full system installation
  $ PYTHON_VERSION=3.12 make packages  # Build with specific Python version

EOF
}

# Clean build artifacts
clean() {
    log_info "Removing old build objects..."
    rm -rfv build/envoxyd
    rm -rfv vendors/src/envoxyd
    rm -rfv vendors/build vendors/dist
    
    log_info "Removing old bin folder..."
    rm -rfv bin deb_dist
    
    log_info "Removing all *.pyc files..."
    find . -name "*.pyc" -type f -delete -print
    
    log_info "Removing all *.o files..."
    find . -name "*.o" -type f -delete -print
    
    log_info "Removing all __pycache__ folders..."
    find . -type d -name "__pycache__" -exec rm -rfv {} + 2>/dev/null || true
    
    log_info "Removing dist and egg-info..."
    rm -rfv dist *.egg-info
    
    log_success "Clean complete"
}

# Try to install packages function
try_install() {
    if sudo dpkg -l "$1" 2>/dev/null | grep -q ^ii; then
        log_info "Package $1 already installed"
        return 1
    fi
    log_info "Installing $1..."
    sudo apt-get -y install "$@"
    return 0
}

# Check Python version
check_python_version() {
    if ! command -v ${PYTHON} &> /dev/null; then
        log_error "Python ${PYTHON_VERSION} not found!"
        log_error "Install it with: sudo apt-get install ${PYTHON} ${PYTHON}-dev ${PYTHON}-venv"
        exit 1
    fi
    
    local version=$(${PYTHON} --version 2>&1 | awk '{print $2}')
    log_info "Using Python ${version}"
}

# Build envoxyd from uWSGI sources
envoxyd() {
    log_info "Building envoxyd from uWSGI sources..."
    
    if [ ! -d "vendors/uwsgi" ]; then
        log_error "uWSGI submodule not found! Run: git submodule update --init --recursive"
        exit 1
    fi
    
    log_info "Removing old build objects..."
    rm -rf vendors/src
    
    log_info "Creating vendors/src/envoxyd folder..."
    mkdir -p vendors/src/envoxyd
    
    log_info "Copying original uWSGI submodule to build folder..."
    cp -R vendors/uwsgi/* vendors/src/envoxyd/
    
    log_info "Injecting envoxyd customizations..."
    cp -R vendors/envoxyd/templates/uwsgi/* vendors/src/envoxyd/
    
    log_info "Injecting run.py file..."
    cp vendors/envoxyd/run.py vendors/src/envoxyd/embed/
    
    cd vendors/
    log_success "envoxyd build preparation complete"
}

# Install envoxyd
envoxyd_install() {
    log_info "Installing envoxyd..."
    # Prefer using the virtualenv python if available to ensure built binary
    # links against the venv's libpython (if that's the intended target).
    if [ -x "${VENV_PATH}/bin/python" ]; then
        "${VENV_PATH}/bin/python" setup.py install
    else
        ${PYTHON} setup.py install
    fi
    log_success "envoxyd installed"
}

# After install, try to set RUNPATH on the envoxyd binary so it will prefer the
# venv lib directory for libpython. This is a best-effort step and requires
# patchelf to be available in the build environment.
fix_envoxyd_rpath() {
    local binpath
    # look for installed binary in venv or local src
    if [ -f "${VENV_PATH}/bin/envoxyd" ]; then
        binpath="${VENV_PATH}/bin/envoxyd"
    elif [ -f "./vendors/src/envoxyd/envoxyd" ]; then
        binpath="./vendors/src/envoxyd/envoxyd"
    elif [ -f "./src/envoxyd/envoxyd" ]; then
        binpath="./src/envoxyd/envoxyd"
    else
        log_warn "envoxyd binary not found for RPATH fix"
        return 0
    fi

    if command -v patchelf >/dev/null 2>&1; then
        log_info "Setting RUNPATH on ${binpath} to /opt/envoxy/lib"
        patchelf --set-rpath "/opt/envoxy/lib" "${binpath}" || log_warn "patchelf failed"
    else
        log_warn "patchelf not available; skipping RPATH fix"
    fi
}

# Install envoxy
envoxy_install() {
    log_info "Activating virtual environment..."
    source ${VENV_PATH}/bin/activate
    
    log_info "Upgrading pip and setuptools..."
    pip install --upgrade pip setuptools wheel
    
    log_info "Installing envoxy..."
    # Use the venv python explicitly to make sure packages and any
    # compiled extensions are built against the venv's Python runtime.
    "${VENV_PATH}/bin/python" setup.py install
    
    log_success "envoxy installed"
}

# Full system installation
install() {
    log_info "Starting full system installation to ${VENV_PATH}..."
    
    # Set locale
    log_info "Configuring locale..."
    if [ -f /etc/locale.gen ]; then
        sudo sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen
        sudo locale-gen
    fi
    export LANG="en_US.UTF-8"
    export LANGUAGE="en_US:en"
    export LC_ALL="en_US.UTF-8"
    export LC_CTYPE="en_US.UTF-8"
    
    # Check Python version
    check_python_version
    
    # Install system dependencies
    log_info "Installing system dependencies..."
    try_install ${PYTHON}-dev
    try_install python-setuptools
    try_install python3-setuptools
    try_install ${PYTHON}-venv
    try_install libpq-dev
    try_install pkg-config
    try_install libsystemd-dev
    try_install build-essential
    
    # Create virtual environment
    log_info "Creating virtual environment at ${VENV_PATH}..."
    sudo rm -rf ${VENV_PATH}
    sudo ${PYTHON} -m venv ${VENV_PATH}
    sudo chown -R $(whoami):$(whoami) ${VENV_PATH}
    
    # Install envoxy
    envoxy_install
    
    # Build and install envoxyd
    envoxyd
    envoxyd_install
    
    cd ..
    
    log_success "Installation complete!"
    log_info "Virtual environment: ${VENV_PATH}"
    log_info "Activate with: source ${VENV_PATH}/bin/activate"
}

# Build distribution packages
packages() {
    log_info "Building distribution packages..."
    
    # Ensure we have a clean build
    install
    
    # Clean old distributions
    log_info "Cleaning old distributions..."
    sudo rm -rf dist
    sudo rm -rf vendors/dist
    
    # Install wheel if not present
    log_info "Ensuring wheel is installed..."
    pip3 install wheel twine
    
    # Build envoxy package using venv python when available
    log_info "Building envoxy package..."
    if [ -x "${VENV_PATH}/bin/python" ]; then
        "${VENV_PATH}/bin/python" setup.py sdist bdist_wheel
    else
        ${PYTHON} setup.py sdist bdist_wheel
    fi
    
    # Build envoxyd package (use venv python when available so extensions
    # are compiled/linked consistently with the venv target)
    log_info "Building envoxyd package..."
    cd vendors
    if [ -x "${VENV_PATH}/bin/python" ]; then
        "${VENV_PATH}/bin/python" setup.py sdist bdist_wheel
    else
        ${PYTHON} setup.py sdist bdist_wheel
    fi
    cd ..
    # Try to fix rpath for the installed envoxyd binary
    fix_envoxyd_rpath
    
    log_success "Packages built successfully!"
    log_info "Envoxy packages: dist/"
    log_info "Envoxyd packages: vendors/dist/"
    echo
    log_info "To upload to PyPI:"
    echo "  twine upload dist/*"
    echo "  cd vendors && twine upload dist/*"
}

# Build for development (editable install)
develop() {
    log_info "Setting up development environment..."
    
    check_python_version
    
    # Create venv if it doesn't exist
    if [ ! -d "${VENV_PATH}" ]; then
        log_info "Creating virtual environment..."
        ${PYTHON} -m venv ${VENV_PATH}
    fi
    
    source ${VENV_PATH}/bin/activate
    
    log_info "Installing in editable mode..."
    pip install --upgrade pip setuptools wheel
    pip install -e .[dev,test]
    
    log_success "Development environment ready!"
    log_info "Activate with: source ${VENV_PATH}/bin/activate"
}

# Show system information
info() {
    echo
    log_info "System Information"
    echo "=================="
    echo
    echo "Python version:     $(${PYTHON} --version 2>&1)"
    echo "Python path:        $(which ${PYTHON})"
    echo "Virtual env:        ${VENV_PATH}"
    echo "Project root:       ${PROJECT_ROOT}"
    echo "Current user:       $(whoami)"
    echo "Architecture:       $(uname -m)"
    echo "OS:                 $(uname -s)"
    echo
    
    if [ -d "${VENV_PATH}" ]; then
        log_success "Virtual environment exists"
        if [ -f "${VENV_PATH}/bin/envoxy-alembic" ]; then
            log_success "envoxy-alembic installed"
        fi
    else
        log_warn "Virtual environment not found"
    fi
}

# Main execution
main() {
    cd "${PROJECT_ROOT}"
    
    if [ $# -eq 0 ]; then
        help
        exit 0
    fi
    
    case "$1" in
        help)
            help
            ;;
        clean)
            clean
            ;;
        envoxyd)
            envoxyd
            ;;
        install)
            install
            ;;
        packages)
            packages
            ;;
        develop)
            develop
            ;;
        info)
            info
            ;;
        *)
            log_error "Unknown command: $1"
            help
            exit 1
            ;;
    esac
}

# Run main with all arguments
main "$@"
