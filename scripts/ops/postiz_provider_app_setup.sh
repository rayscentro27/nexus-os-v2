#!/bin/zsh
# Owner-only: install one social provider's developer-app credentials into the
# self-hosted Postiz on Contabo, then recreate the Postiz container.
#
#   scripts/ops/postiz_provider_app_setup.sh facebook|youtube|tiktok|linkedin
#
# Values are typed (secret hidden), sent over SSH on stdin (never argv, never
# echoed), and written to /opt/nexus-app-services/postiz/providers.env (0600).
# The agent must never run this: it refuses non-interactive / agent sessions.
set -euo pipefail

provider="${1:-}"
case "$provider" in
  facebook) id_var=FACEBOOK_APP_ID;   secret_var=FACEBOOK_APP_SECRET ;;   # also used by Postiz Instagram (via Facebook)
  youtube)  id_var=YOUTUBE_CLIENT_ID; secret_var=YOUTUBE_CLIENT_SECRET ;;
  tiktok)   id_var=TIKTOK_CLIENT_ID;  secret_var=TIKTOK_CLIENT_SECRET ;;
  linkedin) id_var=LINKEDIN_CLIENT_ID; secret_var=LINKEDIN_CLIENT_SECRET ;; # linkedin + linkedin-page
  *) echo "usage: $0 facebook|youtube|tiktok|linkedin" >&2; exit 2 ;;
esac

if [[ ! -t 0 || -n "${CLAUDECODE:-}${CLAUDE_CODE_ENTRYPOINT:-}${CODEX_SANDBOX:-}" ]]; then
  echo "REFUSED: run this yourself in an interactive Terminal (owner action)." >&2
  exit 3
fi

print -n "$id_var (app/client id): "; read -r app_id
print -n "$secret_var (hidden): "; read -rs app_secret; echo
[[ -n "$app_id" && -n "$app_secret" ]] || { echo "both values are required" >&2; exit 4; }

printf '%s\n%s\n%s\n%s\n' "$id_var" "$app_id" "$secret_var" "$app_secret" | \
ssh -o BatchMode=yes nexus-contabo-ts 'set -e; umask 077; cd /opt/nexus-app-services/postiz
python3 -c "
import sys, os
k1, v1, k2, v2 = [l.rstrip(chr(10)) for l in sys.stdin.readlines()[:4]]
p = \"providers.env\"
lines = open(p).read().splitlines() if os.path.exists(p) else []
lines = [l for l in lines if not l.startswith((k1 + \"=\", k2 + \"=\"))] + [k1 + \"=\" + v1, k2 + \"=\" + v2]
open(p + \".tmp\", \"w\").write(chr(10).join(lines) + chr(10)); os.chmod(p + \".tmp\", 0o600); os.replace(p + \".tmp\", p)
"
docker compose up -d postiz >/dev/null 2>&1
for i in $(seq 1 60); do s=$(docker inspect -f "{{.State.Health.Status}}" postiz); [ "$s" = healthy ] && break; sleep 5; done
echo "POSTIZ_HEALTH=$s"; echo "PROVIDER_VARS_SET=$(cut -d= -f1 providers.env | paste -sd, -)"'
unset app_id app_secret
echo "Done. Next: connect the account in the Postiz UI (Add Channel), then tell Claude to run discovery."
