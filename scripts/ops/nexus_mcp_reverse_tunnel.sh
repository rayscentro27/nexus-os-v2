#!/bin/zsh
set -eu

# Keep Nexus MCP private on both hosts. Oracle's forward binds only to loopback.
# Run by system LaunchDaemon com.nexus.nexus-mcp-reverse-tunnel (KeepAlive).
# Transport: Tailscale preferred, legacy public-IP ssh as fallback (see
# oracle_reverse_tunnel.sh). Rollback copy (public-IP only):
#   ~/.nexus/state/transport/rollback/nexus_mcp_reverse_tunnel.sh.pre-tailscale-20261113
exec "${0:A:h}/oracle_reverse_tunnel.sh" 18765 nexus_mcp
