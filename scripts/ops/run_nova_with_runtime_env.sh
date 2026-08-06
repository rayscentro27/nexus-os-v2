#!/bin/bash
# Hermes Nova Telegram Worker — launchd runner
# Sources runtime.env and runs the Nova Telegram worker in --once mode.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RUNTIME_ENV="$HOME/.config/nexus/runtime.env"
PYTHON="$REPO_ROOT/.venv-agent-platform/bin/python3"

if [ ! -f "$PYTHON" ]; then
    PYTHON="$(command -v python3)"
fi

# Source runtime env
if [ -f "$RUNTIME_ENV" ]; then
    set -a
    source "$RUNTIME_ENV"
    set +a
fi

exec "$PYTHON" "$REPO_ROOT/scripts/nova/nova_telegram_worker.py" --once
