#!/bin/zsh
set -eu

SCRIPT_DIR="${0:A:h}"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd -P)"
CANONICAL="/Users/raymonddavis/nexus-os-v2-canonical"
PYTHON="${NEXUS_MCP_PYTHON:-$CANONICAL/.venv-agent-platform/bin/python3}"

if [[ "${NEXUS_MCP_LAUNCHER_ROOT_ONLY:-0}" == "1" ]]; then
  print -r -- "$ROOT"
  exit 0
fi
RUNTIME_ENV="$HOME/.config/nexus/runtime.env"
SERVICE="nexus/credential.nexus.mcp.bridge.v1"
ACCOUNT="bridge_token"

if [[ ! -r "$RUNTIME_ENV" ]]; then
  print -u2 "Nexus canonical runtime environment is missing or unreadable: $RUNTIME_ENV"
  exit 78
fi

set -a
source "$RUNTIME_ENV"
set +a

TOKEN=$(/usr/bin/security find-generic-password -s "$SERVICE" -a "$ACCOUNT" -w)
if [[ -z "$TOKEN" ]]; then
  print -u2 "Nexus MCP bridge credential is not configured"
  exit 78
fi

cd "$ROOT"
export PYTHONPATH="$ROOT:$ROOT/scripts"
export NEXUS_REPO_ROOT="$CANONICAL"
export NEXUS_RESEARCH_STATE_ROOT="${NEXUS_RESEARCH_STATE_ROOT:-$CANONICAL/data}"
export VIRTUAL_ENV="$CANONICAL/.venv-agent-platform"
export PATH="$VIRTUAL_ENV/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
HOST="${NEXUS_MCP_BRIDGE_HOST:-127.0.0.1}"
PORT="${NEXUS_MCP_BRIDGE_PORT:-18765}"
export NEXUS_MCP_BRIDGE_HOST="$HOST"
export NEXUS_MCP_BRIDGE_PORT="$PORT"
export NEXUS_MCP_BRIDGE_TOKEN="$TOKEN"
unset TOKEN
exec "$PYTHON" -m uvicorn services.nexus_mcp.http_server:app \
  --host "$HOST" --port "$PORT" --log-level warning
