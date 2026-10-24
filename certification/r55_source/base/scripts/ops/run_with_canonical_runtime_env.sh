#!/bin/zsh
set -eu

RUNTIME_ENV="/Users/raymonddavis/.config/nexus/runtime.env"
if [ ! -r "$RUNTIME_ENV" ]; then
  echo "Nexus canonical runtime environment is missing or unreadable: $RUNTIME_ENV" >&2
  exit 78
fi

set -a
source "$RUNTIME_ENV"
set +a

NEXUS_CANONICAL_ROOT="/Users/raymonddavis/nexus-os-v2-canonical"
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$NEXUS_CANONICAL_ROOT/scripts"
export NEXUS_REPO_ROOT="$NEXUS_CANONICAL_ROOT"
export NEXUS_RESEARCH_STATE_ROOT="${NEXUS_RESEARCH_STATE_ROOT:-$NEXUS_CANONICAL_ROOT/data}"
NEXUS_NODE_ROOT="/Users/raymonddavis/.nvm/versions/node"
if [ -d "$NEXUS_NODE_ROOT" ]; then
  NEXUS_NODE_BINS=( "$NEXUS_NODE_ROOT"/v*/bin )
  NEXUS_NODE_INDEX=${#NEXUS_NODE_BINS[@]}
  while (( NEXUS_NODE_INDEX > 0 )); do
    NEXUS_NODE_BIN="${NEXUS_NODE_BINS[$NEXUS_NODE_INDEX]}"
    if [ -x "$NEXUS_NODE_BIN/node" ] && [ -x "$NEXUS_NODE_BIN/npm" ]; then
      export PATH="$NEXUS_NODE_BIN:$PATH"
      break
    fi
    ((NEXUS_NODE_INDEX--))
  done
fi

export NEXUS_AUTONOMY_STRIPE_DISABLED=1
unset STRIPE_SECRET_KEY STRIPE_PUBLISHABLE_KEY STRIPE_WEBHOOK_SECRET \
  STRIPE_LIVE_WEBHOOK_SECRET VITE_STRIPE_PUBLISHABLE_KEY VITE_STRIPE_SECRET_KEY

exec "$@"
