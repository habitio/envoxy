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
    docker compose --profile tools run --rm builder bash -c '
        set -e
        cd /usr/envoxy
        
        # Activate virtual environment
        source /opt/envoxy/bin/activate
        
        # Clean old distributions (volumes are mounted, so clean contents)
        rm -rf dist/* vendors/dist/*
        mkdir -p dist vendors/dist
        
        # Install wheel if not present
        pip install --quiet wheel twine
        
        # Build envoxy package
        echo "Building envoxy package..."
        python setup.py sdist bdist_wheel
        
        # Build envoxyd package (preparation already done in Dockerfile)
        echo "Building envoxyd package..."
        cd vendors
        python setup.py sdist bdist_wheel
        cd ..
        
        echo "Packages built successfully!"
        echo "Envoxy: $(ls -1 dist/*.whl 2>/dev/null | head -1)"
        echo "Envoxyd: $(ls -1 vendors/dist/*.whl 2>/dev/null | head -1)"
    '
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
    local dest="${1:-./packages}"
    echo -e "${YELLOW}Exporting packages to ${dest}...${NC}"
    mkdir -p "$dest"
    docker compose --profile tools run --rm builder bash -c "
        cp -v dist/*.whl dist/*.tar.gz /tmp/ 2>/dev/null || true &&
        cp -v vendors/dist/*.whl vendors/dist/*.tar.gz /tmp/ 2>/dev/null || true
    "
    docker cp $(docker compose ps -q builder):/tmp/*.whl "$dest/" 2>/dev/null || true
    docker cp $(docker compose ps -q builder):/tmp/*.tar.gz "$dest/" 2>/dev/null || true
    echo -e "${GREEN}✓ Packages exported to ${dest}${NC}"
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
