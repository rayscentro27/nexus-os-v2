#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd -P -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(cd -P -- "$SCRIPT_DIR/../.." && pwd)"
PRODUCTION_ROOT="${NEXUS_RESEARCH_STATE_ROOT:-$REPO_ROOT/data}"
CERTIFICATION_ROOT="${NEXUS_CERTIFICATION_RESEARCH_STATE_ROOT:-$HOME/.nexus/state/certification/research}"

python3 - "$PRODUCTION_ROOT" "$CERTIFICATION_ROOT" <<'PY'
import sys
from pathlib import Path

production = Path(sys.argv[1]).expanduser().resolve()
certification = Path(sys.argv[2]).expanduser().resolve()
if (production == certification or production in certification.parents
        or certification in production.parents):
    raise SystemExit("CERTIFICATION_AND_PRODUCTION_STATE_ROOTS_OVERLAP")
PY

if (( $# == 0 )); then
  print -u2 "usage: with_certification_research_state.sh command [args...]"
  exit 64
fi

export NEXUS_CERTIFICATION_RESEARCH_STATE_ROOT="$CERTIFICATION_ROOT"
export NEXUS_RESEARCH_STATE_ROOT="$CERTIFICATION_ROOT"
export NEXUS_GOVERNED_DATA_DIR="$CERTIFICATION_ROOT/governed"
exec "$@"
