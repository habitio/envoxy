#!/usr/bin/env bash
# Generate pinned requirements.txt from pyproject.toml using pip-compile
# Usage: ./tools/generate-requirements.sh [--upgrade]
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v pip-compile >/dev/null 2>&1; then
  echo "❌ pip-compile not found. Installing pip-tools..."
  pip install pip-tools
fi

UPGRADE_FLAG=""
if [[ "${1:-}" == "--upgrade" ]]; then
  UPGRADE_FLAG="--upgrade"
  echo "🔄 Upgrading all dependencies to latest compatible versions..."
fi

# Generate main requirements from pyproject.toml
echo "📦 Generating requirements.txt from pyproject.toml..."
pip-compile \
  --output-file=requirements.txt \
  $UPGRADE_FLAG \
  --resolver=backtracking \
  --strip-extras \
  pyproject.toml

# Generate dev requirements if requested
if [[ "${2:-}" == "--dev" ]] || [[ "${1:-}" == "--dev" ]]; then
  echo "🔧 Generating requirements-dev.txt with dev dependencies..."
  pip-compile \
    --output-file=requirements-dev.txt \
    $UPGRADE_FLAG \
    --resolver=backtracking \
    --strip-extras \
    --extra=dev \
    pyproject.toml
fi

echo "✅ Generated requirements.txt"

