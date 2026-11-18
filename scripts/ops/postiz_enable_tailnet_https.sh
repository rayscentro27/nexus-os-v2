#!/bin/zsh
# Switch Postiz's public-facing origin to tailnet-only HTTPS
# (https://nexus-app-services.tailb1e262.ts.net) so OAuth redirect URIs are
# HTTPS on Postiz's own origin (required by Meta/Google/LinkedIn; TikTok
# otherwise falls back to the third-party redirectmeto.com).
#
# Precondition (owner, once): Tailscale admin -> DNS -> enable HTTPS
# certificates. Access stays tailnet-only (no Funnel). The existing
# http://...:4007 tailnet route is kept for the Nexus adapter/n8n.
# Rollback: restore the printed .env backup, `tailscale serve --https=443 off`,
# `docker compose up -d postiz`.
set -euo pipefail
HOST=nexus-app-services.tailb1e262.ts.net
ssh -o BatchMode=yes nexus-contabo-ts "set -e
certs=\$(tailscale status --json | python3 -c 'import json,sys; print(json.load(sys.stdin).get(\"CertDomains\") or \"\")')
case \"\$certs\" in *$HOST*) ;; *) echo 'BLOCKED: tailnet HTTPS certificates are not enabled (owner: Tailscale admin -> DNS -> Enable HTTPS)'; exit 5;; esac
cd /opt/nexus-app-services/postiz
TS=\$(date -u +%Y%m%dT%H%M%SZ); cp -p .env .env.bak-pre-https-\$TS
sudo tailscale serve --bg --https=443 http://127.0.0.1:4007
sed -i 's#^POSTIZ_URL=.*#POSTIZ_URL=https://$HOST#' .env
docker compose up -d postiz >/dev/null 2>&1
for i in \$(seq 1 60); do s=\$(docker inspect -f '{{.State.Health.Status}}' postiz); [ \"\$s\" = healthy ] && break; sleep 5; done
echo POSTIZ_HEALTH=\$s; echo ENV_BACKUP=.env.bak-pre-https-\$TS
curl -s -o /dev/null -w 'HTTPS_FRONTEND=%{http_code}\n' -m 15 https://$HOST/
tailscale serve status"
