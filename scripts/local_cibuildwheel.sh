#!/usr/bin/env bash
set -euo pipefail

# Local helper to run cibuildwheel and produce manylinux wheels (linux x86_64)
# Usage: ./scripts/local_cibuildwheel.sh
# Requirements: Docker installed and running. This script should be run from the repo root.

cd "$(dirname "$0")/.."

echo "==> Running cibuildwheel locally (target: cp310, cp311, cp312 x86_64)"

if ! command -v docker >/dev/null 2>&1; then
  echo "Error: docker is required to run cibuildwheel locally."
  exit 1
fi

# Clean previous outputs
rm -rf wheelhouse
mkdir -p wheelhouse

# Ensure we have a recent pip and cibuildwheel
python -m pip install --upgrade pip setuptools wheel build cibuildwheel >/dev/null

# Limit builds to modern CPython versions we support. Adjust as needed.
export CIBW_BUILD="cp310-* cp311-* cp312-*"
export CIBW_ARCHS="x86_64"
# Optional: pin manylinux image (uncomment to force)
# export CIBW_MANYLINUX_POLLY="manylinux_2014_x86_64"

# Run cibuildwheel; this will pull manylinux docker images and run builds inside them.
python -m cibuildwheel --output-dir wheelhouse

echo "==> cibuildwheel finished. Wheels written to: $(pwd)/wheelhouse"
ls -lah wheelhouse || true

echo "Tip: upload resulting wheels (wheelhouse/*.whl) to TestPyPI for verification before publishing to PyPI."
