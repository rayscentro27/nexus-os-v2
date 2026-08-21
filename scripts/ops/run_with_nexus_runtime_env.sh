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

# The continuous-loop runtime has no Stripe execution responsibility. Keep
# shared application credentials available to their legitimate consumers, but
# prevent them from crossing into this autonomous child process.
export NEXUS_AUTONOMY_STRIPE_DISABLED=1
unset STRIPE_SECRET_KEY STRIPE_PUBLISHABLE_KEY STRIPE_WEBHOOK_SECRET \
  STRIPE_LIVE_WEBHOOK_SECRET VITE_STRIPE_PUBLISHABLE_KEY VITE_STRIPE_SECRET_KEY

exec "$@"
