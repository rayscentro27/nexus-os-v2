#!/bin/zsh
set -eu

ROOT="/Users/raymonddavis/nexus-os-v2-activation-20260804T014509Z"
exec "$ROOT/scripts/ops/run_with_nexus_runtime_env.sh" /usr/bin/python3 "$ROOT/scripts/trading/nexus_oanda_practice_engine.py" --daemon --interval-seconds 60
