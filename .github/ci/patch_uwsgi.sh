#!/usr/bin/env bash
# Simplified uwsgi build script - dynamic linking approach (like official uwsgi)
set -xeuo pipefail

echo "CI: Building uwsgi with dynamic Python linking (official approach)"

PY_BIN=${1:-python}

# Upgrade pip and build tools
${PY_BIN} -m pip install --upgrade pip setuptools wheel

# Detect and install build dependencies
if command -v yum >/dev/null 2>&1; then
    yum install -y gcc make pkgconfig python3-devel openssl-devel zlib-devel || true
elif command -v apt-get >/dev/null 2>&1; then
    apt-get update && apt-get install -y build-essential python3-dev libssl-dev zlib1g-dev || true
fi

# Find uwsgi source directory
TARGET=""
if [ -f "./uwsgiconfig.py" ]; then
    TARGET="$(pwd)"
elif [ -d "/project/vendors/uwsgi" ]; then
    TARGET="/project/vendors/uwsgi"
else
    TARGET=$(find /project -maxdepth 4 -type d -name uwsgi 2>/dev/null | head -n1)
fi

if [ -z "$TARGET" ]; then
    echo "ERROR: uwsgi directory not found"
    exit 1
fi

cd "$TARGET"
echo "CI: Building in $(pwd)"

# Copy uwsgi template files from envoxyd
if [ -d "/project/vendors/envoxyd/templates/uwsgi" ]; then
    cp -r /project/vendors/envoxyd/templates/uwsgi/* . || true
    echo "CI: Copied uwsgi template files"
fi

if [ -f "/project/vendors/envoxyd/templates/run.py" ]; then
    mkdir -p embed
    cp /project/vendors/envoxyd/templates/run.py embed/ || true
fi

# Build uwsgi with dynamic Python linking (official method)
echo "CI: Building uwsgi with flask profile"
"${PY_BIN}" uwsgiconfig.py --build flask || {
    echo "ERROR: uwsgi build failed"
    exit 1
}

# Find the built binary
DEST_BIN="/project/vendors/src/envoxyd/envoxyd"
for cand in envoxyd uwsgi; do
    if [ -f "$cand" ] && file "$cand" | grep -q 'ELF'; then
        mkdir -p "$(dirname "$DEST_BIN")"
        cp "$cand" "$DEST_BIN"
        chmod +x "$DEST_BIN"
        echo "CI: Binary built at $DEST_BIN"
        break
    fi
done

if [ ! -f "$DEST_BIN" ]; then
    echo "ERROR: Built binary not found"
    exit 1
fi

echo "CI: Binary info:"
ls -lh "$DEST_BIN"
file "$DEST_BIN"
ldd "$DEST_BIN" | head -20 || true

echo "CI: Build complete - uwsgi uses dynamic Python linking"
