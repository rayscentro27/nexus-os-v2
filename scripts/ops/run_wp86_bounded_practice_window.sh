#!/bin/zsh
# Ray-approved bounded operator command; does not start automatically.
# The engine exits after MAX_CYCLES and remains Practice-only.
set -euo pipefail
ROOT="${0:A:h:h}"
exec "$ROOT/scripts/ops/run_with_nexus_runtime_env.sh" /usr/bin/python3 "$ROOT/scripts/trading/nexus_oanda_practice_engine.py" --daemon --interval-seconds "${INTERVAL_SECONDS:-3600}" --max-cycles "${MAX_CYCLES:-8}" --json
