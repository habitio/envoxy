#!/usr/bin/env zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${0}")" >/dev/null 2>&1 && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." >/dev/null 2>&1 && pwd)"

# Default service models module
: ${SERVICE_MODELS:="examples.template_service.models"}
export SERVICE_MODELS

# Accept --service and --alembic-config overrides
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --service)
      shift
      SERVICE_MODELS="$1"
      shift
      ;;
    --alembic-config)
      shift
      ALEMBIC_CONFIG_OVERRIDE="$1"
      shift
      ;;
    --)
      shift
      break
      ;;
    *)
      break
      ;;
  esac
done

# Try to find envoxy's bundled alembic.ini via the installed package
ALEMBIC_INI=""
if [[ -n "${ALEMBIC_CONFIG_OVERRIDE:-}" ]]; then
  ALEMBIC_INI="$ALEMBIC_CONFIG_OVERRIDE"
else
  PY_INI=$(python - <<'PY'
import importlib, os
try:
    envoxy = importlib.import_module('envoxy')
    candidate = os.path.join(os.path.dirname(envoxy.__file__), 'tools', 'alembic', 'alembic.ini')
    if os.path.isfile(candidate):
        print(candidate)
except Exception:
    pass
PY
)
  if [[ -n "$PY_INI" ]]; then
    ALEMBIC_INI="$PY_INI"
  else
    for c in "${REPO_ROOT}/../envoxy/tools/alembic/alembic.ini" "${REPO_ROOT}/envoxy/tools/alembic/alembic.ini"; do
      if [[ -f "$c" ]]; then
        ALEMBIC_INI="$c"
        break
      fi
    done
  fi
fi

if [[ -z "$ALEMBIC_INI" ]]; then
  echo "Could not find envoxy's alembic.ini; install envoxy in this env or provide --alembic-config" >&2
  exit 2
fi

export PYTHONPATH
export SERVICE_MODELS
export ALEMBIC_CONFIG="$ALEMBIC_INI"

echo "Running: python -m alembic -c '$ALEMBIC_CONFIG' $*"
exec python -m alembic -c "$ALEMBIC_CONFIG" "$@"
