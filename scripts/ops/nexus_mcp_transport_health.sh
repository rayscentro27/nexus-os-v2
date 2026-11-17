#!/bin/zsh
set -u

ORACLE='opc@161.153.40.41'
SSH=(/usr/bin/ssh -i "$HOME/.ssh/oracle_vm" -o BatchMode=yes -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new)

local_status=$(/usr/bin/curl --silent --output /dev/null --write-out '%{http_code}' --max-time 5 http://127.0.0.1:18765/mcp || true)
if [[ "$local_status" != '401' ]]; then
  print 'MCP_SERVER_DOWN'
  exit 2
fi

remote_status=$("${SSH[@]}" "$ORACLE" "curl --silent --output /dev/null --write-out '%{http_code}' --max-time 5 http://127.0.0.1:18765/mcp" 2>/dev/null || true)
if [[ "$remote_status" == '000' || -z "$remote_status" ]]; then
  print 'TUNNEL_DOWN'
  exit 3
elif [[ "$remote_status" == '500' || "$remote_status" == '502' || "$remote_status" == '503' ]]; then
  print 'MCP_SERVER_DOWN'
  exit 4
elif [[ "$remote_status" != '401' ]]; then
  print 'MCP_PROTOCOL_FAILURE'
  exit 5
fi

hermes_result=$("${SSH[@]}" "$ORACLE" 'podman exec nexus-hermes-0206 /opt/hermes/.venv/bin/hermes --profile nova_nexus mcp test nexus_mcp_remote' 2>&1 || true)
if print -r -- "$hermes_result" | /usr/bin/grep -q '401\|Unauthorized\|unauthorized'; then
  print 'AUTH_FAILURE'
  exit 6
elif print -r -- "$hermes_result" | /usr/bin/grep -q 'Tools discovered: 28'; then
  print 'PASS transport=UP server=UP auth=PASS hermes=PASS tools=28'
  exit 0
elif print -r -- "$hermes_result" | /usr/bin/grep -q 'Connected'; then
  print 'MCP_TOOL_DISCOVERY_FAILURE'
  exit 7
else
  print 'HERMES_FAILURE'
  exit 8
fi
