#!/bin/bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RUNTIME_ENV="$HOME/.config/nexus/runtime.env"
PYTHON="$REPO_ROOT/.venv-agent-platform/bin/python3"
if [ ! -x "$PYTHON" ]; then PYTHON="$(command -v python3)"; fi
if [ -f "$RUNTIME_ENV" ]; then set -a; source "$RUNTIME_ENV"; set +a; fi
export NEXUS_VOICE_ALLOWED_ORIGINS="https://goclearonline.cc"
export PYTHONPATH="$REPO_ROOT/scripts${PYTHONPATH:+:$PYTHONPATH}"
export DYLD_LIBRARY_PATH="${DYLD_LIBRARY_PATH:-/usr/local/Cellar/openssl@3/3.6.3/lib}"
exec "$PYTHON" -m scripts.nexus_agent_platform.voice.local_server --host 127.0.0.1 --port 8789
