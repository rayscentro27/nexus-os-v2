#!/bin/zsh
# Postiz TikTok OAuth callback origin + least-privilege scopes (TikTok only).
#
#   scripts/ops/postiz_tiktok_oauth_origin.sh status|apply|rollback
#
# apply: refuses unless the public TikTok bounce page on ORIGIN is live and
#   valid, then on Contabo:
#   - verifies the running image is the manifest image (v2.25.3) and that the
#     staged tiktok.provider.js differs from the original ONLY by
#       scopes -> [user.info.basic, video.upload]   (user.info.profile is not
#         enabled in the Sandbox; username is therefore not requested)
#       2 redirect sites -> ${POSTIZ_TIKTOK_OAUTH_ORIGIN || <stock expression>}
#       2 user/info field lists -> without ,username
#   - backs up compose.yaml + providers.env
#   - mounts the override read-only, sets POSTIZ_TIKTOK_OAUTH_ORIGIN in
#     providers.env (FRONTEND_URL and the Meta overrides unchanged), recreates
#     only `postiz`
# rollback: restores compose.yaml + providers.env from the latest backup made
#   by apply and recreates only `postiz`.
# No secrets are read or printed. Postiz stays tailnet-only throughout.
set -euo pipefail
ORIGIN=https://postiz-auth.goclearonline.cc
ROOT=${0:A:h:h:h}
cmd=${1:-status}

remote() { ssh -o BatchMode=yes -o ConnectTimeout=20 nexus-contabo-ts "$@"; }

case "$cmd" in
status)
  python3 -c "import sys,json; sys.path.insert(0,'$ROOT/scripts/systems'); import maintenance_tick as t
f=t._node_probe('CONTABO_APP_SERVICES'); print(json.dumps({k:v for k,v in f.items() if k.startswith(('POSTIZ_IMAGE','POSTIZ_TIKTOK','POSTIZ_PROVIDER_TIKTOK'))}))
b=t._postiz_oauth_bounce(); print(json.dumps({'status':b['status'],'tiktok':b['callback_pages'].get('tiktok')}))"
  ;;
apply)
  bounce=$(python3 -c "import sys; sys.path.insert(0,'$ROOT/scripts/systems'); import maintenance_tick as t; b=t._postiz_oauth_bounce(); print('PASS' if (b['callback_pages'].get('tiktok') or {}).get('valid') and all(v==404 for v in b['unrelated_paths'].values()) else 'FAIL')")
  [[ "$bounce" == PASS ]] || { echo "BLOCKED: public TikTok bounce page on $ORIGIN is not valid yet"; exit 5; }
  remote 'bash -s' <<REMOTE
set -e; cd /opt/nexus-app-services/postiz
python3 - <<'PY'
import json, subprocess, hashlib
m = json.load(open('overrides/v2.25.3/MANIFEST.json'))
img = subprocess.run(['docker','inspect','-f','{{.Image}}','postiz'], capture_output=True, text=True).stdout.strip()
assert img == m['image_id'], 'BLOCKED: running image is not the manifest image'
f = m['files']['tiktok.provider.js']
o = open('overrides/v2.25.3/original/tiktok.provider.js').read()
n = open('overrides/v2.25.3/tiktok.provider.js').read()
assert hashlib.sha256(o.encode()).hexdigest() == f['original_sha256'], 'BLOCKED: original copy changed'
assert hashlib.sha256(n.encode()).hexdigest() == f['override_sha256'], 'BLOCKED: override changed'
scopes = n.split('this.scopes = [', 1)[1].split('];', 1)[0]
assert [s.strip().strip("',") for s in scopes.strip().splitlines()] == ['user.info.basic', 'video.upload'], 'BLOCKED: scopes'
assert n.count('process.env.POSTIZ_TIKTOK_OAUTH_ORIGIN ||') == 2, 'BLOCKED: redirect sites'
# Undo the two bounded edits on the override: must reproduce the original exactly.
stock_scopes = "\n            'video.list',\n            'user.info.basic',\n            'video.publish',\n            'video.upload',\n            'user.info.profile',\n            'user.info.stats',\n        "
back = n.replace('this.scopes = [' + scopes + '];', 'this.scopes = [' + stock_scopes + '];', 1)
new_redir = "\${process.env.POSTIZ_TIKTOK_OAUTH_ORIGIN || ((process?.env?.FRONTEND_URL?.indexOf('https') === -1 ? 'https://redirectmeto.com/' : '') + process?.env?.FRONTEND_URL)}/integrations/social/tiktok"
r1 = "\${process?.env?.FRONTEND_URL?.indexOf('https') === -1\n                    ? 'https://redirectmeto.com/'\n                    : ''}\${process?.env?.FRONTEND_URL}/integrations/social/tiktok"
r2 = "\${process?.env?.FRONTEND_URL?.indexOf('https') === -1\n                ? 'https://redirectmeto.com/'\n                : ''}\${process?.env?.FRONTEND_URL}/integrations/social/tiktok"
back = back.replace(new_redir, r1, 1).replace(new_redir, r2, 1)
assert n.count("fields=open_id,avatar_url,display_name,union_id'") == 2 and 'union_id,username' not in n, 'BLOCKED: user/info fields'
back = back.replace("fields=open_id,avatar_url,display_name,union_id'", "fields=open_id,avatar_url,display_name,union_id,username'")
assert back == o, 'BLOCKED: override contains changes beyond scopes + redirect origin'
print('TIKTOK_OVERRIDE_VERIFIED')
PY
TS=\$(date -u +%Y%m%dT%H%M%SZ); B=rollback/apply-tiktok-oauth-origin-\$TS; mkdir -p \$B
cp -p compose.yaml \$B/; cp -p providers.env \$B/; chmod 600 \$B/providers.env; echo \$B > rollback/LATEST_TIKTOK_OAUTH_APPLY
python3 - <<'PY'
import os
p = 'compose.yaml'; s = open(p).read()
D = '/app/apps/backend/dist/libraries/nestjs-libraries/src/integrations/social'
anchor = '      - ./overrides/v2.25.3/instagram.provider.js:%s/instagram.provider.js:ro\n' % D
add = '      - ./overrides/v2.25.3/tiktok.provider.js:%s/tiktok.provider.js:ro\n' % D
if add not in s:
    assert s.count(anchor) == 1, 'BLOCKED: compose anchor (Meta overrides must be mounted)'
    s = s.replace(anchor, anchor + add)
open(p + '.tmp', 'w').write(s); os.replace(p + '.tmp', p)
p = 'providers.env'
lines = [l for l in open(p).read().splitlines() if not l.startswith('POSTIZ_TIKTOK_OAUTH_ORIGIN=')]
lines.append('POSTIZ_TIKTOK_OAUTH_ORIGIN=$ORIGIN')
open(p + '.tmp', 'w').write('\n'.join(lines) + '\n'); os.chmod(p + '.tmp', 0o600); os.replace(p + '.tmp', p)
PY
docker compose config -q && echo COMPOSE_VALID
docker compose up -d --force-recreate postiz >/dev/null 2>&1 </dev/null
for i in \$(seq 1 60); do s=\$(docker inspect -f '{{.State.Health.Status}}' postiz); [ "\$s" = healthy ] && break; sleep 5; done
echo POSTIZ_HEALTH=\$s; echo ROLLBACK_BACKUP=\$B
echo FRONTEND_URL=\$(docker exec postiz printenv FRONTEND_URL </dev/null)
REMOTE
  ;;
rollback)
  remote 'bash -s' <<'REMOTE'
set -e; cd /opt/nexus-app-services/postiz; B=$(cat rollback/LATEST_TIKTOK_OAUTH_APPLY)
cp -p $B/compose.yaml compose.yaml; cp -p $B/providers.env providers.env; chmod 600 providers.env
docker compose config -q && docker compose up -d postiz >/dev/null 2>&1 </dev/null
for i in $(seq 1 60); do s=$(docker inspect -f '{{.State.Health.Status}}' postiz); [ "$s" = healthy ] && break; sleep 5; done
echo RESTORED_FROM=$B POSTIZ_HEALTH=$s
REMOTE
  ;;
*) echo "usage: $0 status|apply|rollback" >&2; exit 2 ;;
esac
