#!/bin/bash
# Run Alpha Telegram Worker with canonical runtime.env
set -euo pipefail

RUNTIME_ENV="$HOME/.config/nexus/runtime.env"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [ -f "$RUNTIME_ENV" ]; then
    set -a
    source "$RUNTIME_ENV"
    set +a
fi

cd "$REPO_ROOT"
exec python3 scripts/alpha/alpha_telegram_worker.py "$@"
