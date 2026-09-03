#!/bin/zsh
set -eu

ROOT="/Users/raymonddavis/nexus-os-v2"
PYTHON="/Users/raymonddavis/nexus-hermes-runtime/.venv/bin/python"
SERVICE="nexus/credential.nexus.mcp.bridge.v1"
ACCOUNT="bridge_token"

TOKEN=$(/usr/bin/security find-generic-password -s "$SERVICE" -a "$ACCOUNT" -w)
if [[ -z "$TOKEN" ]]; then
  print -u2 "Nexus MCP bridge credential is not configured"
  exit 78
fi

cd "$ROOT"
export PYTHONPATH="$ROOT"
export NEXUS_MCP_BRIDGE_HOST="127.0.0.1"
export NEXUS_MCP_BRIDGE_PORT="18765"
export NEXUS_MCP_BRIDGE_TOKEN="$TOKEN"
exec "$PYTHON" -m uvicorn services.nexus_mcp.http_server:app \
  --host 127.0.0.1 --port 18765 --log-level warning
