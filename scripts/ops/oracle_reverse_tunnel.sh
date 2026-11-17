#!/bin/zsh
# Canonical Mac -> Oracle reverse tunnel for one loopback bridge port.
#
#   oracle_reverse_tunnel.sh <port> <label>
#
# Oracle consumers (Hermes nova_nexus MCP servers) keep calling 127.0.0.1:<port>
# on Oracle; only the transport underneath changes:
#   1. TAILSCALE (preferred): ssh to Oracle's tailnet address 100.91.191.32.
#   2. LEGACY_PUBLIC_FALLBACK: the original public-IP ssh path, used only when
#      the tailnet path is unreachable. While on fallback the tunnel re-probes
#      Tailscale every NEXUS_TUNNEL_FALLBACK_REPROBE_SECONDS and exits when it
#      is back so launchd (KeepAlive) restarts it on the preferred path.
# Both ends stay bound to 127.0.0.1. Nothing is exposed on the tailnet.
# The selected transport is recorded (no secrets) in
# ~/.nexus/state/transport/oracle_reverse_<port>.json for Systems health.
set -u

PORT="${1:?port required}"
LABEL="${2:-port_$PORT}"
[[ "$PORT" == <1024-65535> ]] || { print -u2 "invalid port: $PORT"; exit 64; }

TAILSCALE_HOST="${NEXUS_ORACLE_TAILSCALE_HOST:-100.91.191.32}"
PUBLIC_HOST="${NEXUS_ORACLE_PUBLIC_HOST:-161.153.40.41}"
HOST_KEY_ALIAS="161.153.40.41"   # one known_hosts identity for both paths
KEY="$HOME/.ssh/oracle_vm"
REPROBE="${NEXUS_TUNNEL_FALLBACK_REPROBE_SECONDS:-600}"
STATE_DIR="$HOME/.nexus/state/transport"
STATE="$STATE_DIR/oracle_reverse_$PORT.json"
mkdir -p "$STATE_DIR"

tailscale_reachable() { /usr/bin/nc -z -G 3 "$TAILSCALE_HOST" 22 >/dev/null 2>&1 }

if tailscale_reachable; then
  TRANSPORT=TAILSCALE; TARGET="$TAILSCALE_HOST"; HOSTKEY_POLICY=yes
else
  TRANSPORT=LEGACY_PUBLIC_FALLBACK; TARGET="$PUBLIC_HOST"; HOSTKEY_POLICY=accept-new
fi

/usr/bin/ssh -N -T \
  -o BatchMode=yes -o IdentitiesOnly=yes -o ConnectTimeout=10 \
  -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
  -o TCPKeepAlive=yes -o StrictHostKeyChecking="$HOSTKEY_POLICY" \
  -o HostKeyAlias="$HOST_KEY_ALIAS" \
  -i "$KEY" -R "127.0.0.1:$PORT:127.0.0.1:$PORT" "opc@$TARGET" &
SSH_PID=$!
trap 'kill $SSH_PID 2>/dev/null; wait $SSH_PID 2>/dev/null; exit 0' TERM INT

STARTED=$(/bin/date -u +%Y-%m-%dT%H:%M:%SZ)
print -r -- "{\"schema\":\"nexus.oracle-reverse-tunnel.v1\",\"label\":\"$LABEL\",\"port\":$PORT,\"transport\":\"$TRANSPORT\",\"target\":\"$TARGET\",\"ssh_pid\":$SSH_PID,\"started_at\":\"$STARTED\"}" >| "$STATE.tmp" && mv -f "$STATE.tmp" "$STATE"
print -r -- "$STARTED $LABEL port=$PORT transport=$TRANSPORT target=$TARGET"

if [[ "$TRANSPORT" == LEGACY_PUBLIC_FALLBACK ]]; then
  while kill -0 $SSH_PID 2>/dev/null; do
    integer waited=0
    while (( waited < REPROBE )) && kill -0 $SSH_PID 2>/dev/null; do sleep 15; (( waited += 15 )); done
    if kill -0 $SSH_PID 2>/dev/null && tailscale_reachable; then
      print -r -- "$(/bin/date -u +%Y-%m-%dT%H:%M:%SZ) $LABEL tailscale recovered; restarting on preferred path"
      kill $SSH_PID 2>/dev/null; wait $SSH_PID 2>/dev/null; exit 0
    fi
  done
fi

wait $SSH_PID
exit $?
