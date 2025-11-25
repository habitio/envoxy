#!/usr/bin/env bash
# Build uwsgi for sdist testing - compiles with local system Python
set -xeuo pipefail

echo "CI: Building uwsgi with local Python (for sdist testing)"

PY_BIN=${1:-python}

# Install uwsgi if needed
cd /project/vendors/uwsgi

# Copy template files
if [ -d "/project/vendors/envoxyd/templates/uwsgi" ]; then
    cp -r /project/vendors/envoxyd/templates/uwsgi/* .
fi

if [ -f "/project/vendors/envoxyd/templates/run.py" ]; then
    mkdir -p embed
    cp /project/vendors/envoxyd/templates/run.py embed/
fi

# Build uwsgi with flask profile using local Python
"${PY_BIN}" uwsgiconfig.py --build flask

# Find and copy binary
DEST_BIN="/project/vendors/src/envoxyd/envoxyd"
for cand in envoxyd uwsgi; do
    if [ -f "$cand" ] && file "$cand" | grep -q 'ELF'; then
        mkdir -p "$(dirname "$DEST_BIN")"
        cp "$cand" "$DEST_BIN"
        chmod +x "$DEST_BIN"
        echo "CI: Built $DEST_BIN"
        break
    fi
done

if [ ! -f "$DEST_BIN" ]; then
    echo "ERROR: Built binary not found"
    exit 1
fi

echo "CI: Build complete"

