#!/usr/bin/env zsh
# Central alembic helper for the framework. It uses tools/alembic/alembic.ini by default
# and runs alembic with the provided SERVICE_MODELS and PYTHONPATH.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${0}")" >/dev/null 2>&1 && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." >/dev/null 2>&1 && pwd)"
SRC_PATH="$REPO_ROOT/src"

: ${PYTHONPATH:=$SRC_PATH}
: ${SERVICE_MODELS:=}
export PYTHONPATH SERVICE_MODELS

FRAMEWORK_INI="$SCRIPT_DIR/alembic.ini"
if [[ -f "$FRAMEWORK_INI" ]]; then
  ALEMBIC_CONFIG="$FRAMEWORK_INI"
  export ALEMBIC_CONFIG
fi

run_alembic() {
  if [[ -n "${ALEMBIC_CONFIG:-}" ]]; then
    alembic -c "$ALEMBIC_CONFIG" "$@"
  else
    alembic "$@"
  fi
}

if [[ "$#" -lt 1 ]]; then
  echo "Usage: $0 <alembic-command> [args...]" >&2
  exit 1
fi

exec run_alembic "$@"
