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

# launchd may not preserve the plist PYTHONPATH through the environment
# bootstrap shell. Keep the canonical repository package importable for the
# bounded scheduler and the existing Hermes transport callers.
export PYTHONPATH="/Users/raymonddavis/nexus-os-v2/scripts${PYTHONPATH:+:$PYTHONPATH}"

exec "$@"
