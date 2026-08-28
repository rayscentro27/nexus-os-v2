#!/bin/zsh
set -euo pipefail
REPO_ROOT="/Users/raymonddavis/nexus-os-v2"
PYTHON_BIN="$REPO_ROOT/.venv-agent-platform/bin/python3"
if [[ ! -x "$PYTHON_BIN" ]]; then PYTHON_BIN="/usr/bin/python3"; fi
cd "$REPO_ROOT"
exec env PYTHONPATH="$REPO_ROOT/scripts" "$PYTHON_BIN" -m nexus_agent_platform.governed.voice_repair retry
