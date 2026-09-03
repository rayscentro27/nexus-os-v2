#!/bin/bash
# Hermes Nova Telegram Worker — launchd runner
# Sources runtime.env and runs the Nova Telegram worker in --once mode.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RUNTIME_ENV="$HOME/.config/nexus/runtime.env"
PYTHON="$REPO_ROOT/.venv-agent-platform/bin/python3"

if [ ! -x "$PYTHON" ]; then
    PYTHON="$(command -v python3)"
fi

# Source runtime env
if [ -f "$RUNTIME_ENV" ]; then
    set -a
    source "$RUNTIME_ENV"
    set +a
fi

# Homebrew's Python/SSL install currently resolves OpenSSL from this local
# Cellar path. Keep the runtime self-contained for launchd and manual cycles.
export DYLD_LIBRARY_PATH="${DYLD_LIBRARY_PATH:-/usr/local/Cellar/openssl@3/3.6.3/lib}"

# Keep launchd's interval supervision effective even if a network/library call
# ignores its inner timeout.  Accepted missions are persisted before Hermes
# execution and are resumed by the worker on the next cycle.
exec /usr/bin/perl -e 'alarm 300; exec @ARGV' "$PYTHON" "$REPO_ROOT/scripts/nova/nova_telegram_worker.py" --once
