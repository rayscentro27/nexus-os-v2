#!/bin/zsh
# Postiz Meta OAuth callback origin (Facebook + Instagram only).
#
#   scripts/ops/postiz_meta_oauth_origin.sh status|apply|rollback
#
# apply: refuses unless the public bounce pages on ORIGIN are live and valid
#   (Systems check `_postiz_oauth_bounce`), then on Contabo:
#   - verifies the running image is the manifest image (v2.25.3) and the staged
#     overrides differ from the originals only on the 4 redirect_uri lines
#   - backs up compose.yaml + providers.env
#   - mounts the two overrides read-only, sets POSTIZ_META_OAUTH_ORIGIN in
#     providers.env (FRONTEND_URL unchanged), recreates only `postiz`
# rollback: restores compose.yaml + providers.env from the latest backup made
#   by apply and recreates only `postiz` (stock v2.25.3 behaviour).
# No secrets are read or printed. Postiz stays tailnet-only throughout.
set -euo pipefail
ORIGIN=https://postiz-auth.goclearonline.cc
ROOT=${0:A:h:h:h}
cmd=${1:-status}

remote() { ssh -o BatchMode=yes -o ConnectTimeout=20 nexus-contabo-ts "$@"; }

case "$cmd" in
status)
  python3 -c "import sys,json; sys.path.insert(0,'$ROOT/scripts/systems'); import maintenance_tick as t
f=t._node_probe('CONTABO_APP_SERVICES'); print(json.dumps({k:v for k,v in f.items() if k.startswith(('POSTIZ_IMAGE','POSTIZ_META','POSTIZ_PROVIDER_'))}))
print(json.dumps(t._postiz_oauth_bounce()))"
  ;;
apply)
  bounce=$(python3 -c "import sys; sys.path.insert(0,'$ROOT/scripts/systems'); import maintenance_tick as t; print(t._postiz_oauth_bounce()['status'])")
  [[ "$bounce" == PASS ]] || { echo "BLOCKED: public bounce pages on $ORIGIN are not valid yet (status=$bounce)"; exit 5; }
  remote "set -e; cd /opt/nexus-app-services/postiz; O=overrides/v2.25.3
D=/app/apps/backend/dist/libraries/nestjs-libraries/src/integrations/social
python3 - <<'PY'
import json, subprocess, hashlib
m = json.load(open('overrides/v2.25.3/MANIFEST.json'))
img = subprocess.run(['docker','inspect','-f','{{.Image}}','postiz'], capture_output=True, text=True).stdout.strip()
assert img == m['image_id'], 'BLOCKED: running image is not the manifest image'
for p in ('facebook', 'instagram'):
    f = m['files'][p + '.provider.js']
    o = open('overrides/v2.25.3/original/%s.provider.js' % p, 'rb').read()
    n = open('overrides/v2.25.3/%s.provider.js' % p, 'rb').read()
    assert hashlib.sha256(o).hexdigest() == f['original_sha256'], 'BLOCKED: original copy changed'
    assert hashlib.sha256(n).hexdigest() == f['override_sha256'], 'BLOCKED: override changed'
    ol, nl = o.decode().splitlines(), n.decode().splitlines()
    diff = [i for i, (a, b) in enumerate(zip(ol, nl)) if a != b]
    assert len(ol) == len(nl) and len(diff) == 2, 'BLOCKED: unexpected override diff'
    for i in diff:
        assert nl[i] == ol[i].replace('\${process.env.FRONTEND_URL}/integrations/social/' + p,
            '\${process.env.POSTIZ_META_OAUTH_ORIGIN || process.env.FRONTEND_URL}/integrations/social/' + p), 'BLOCKED: override line'
print('OVERRIDES_VERIFIED')
PY
TS=\$(date -u +%Y%m%dT%H%M%SZ); B=rollback/apply-meta-oauth-origin-\$TS; mkdir -p \$B
cp -p compose.yaml \$B/; cp -p providers.env \$B/; chmod 600 \$B/providers.env; echo \$B > rollback/LATEST_META_OAUTH_APPLY
python3 - <<'PY'
p = 'compose.yaml'; s = open(p).read()
D = '/app/apps/backend/dist/libraries/nestjs-libraries/src/integrations/social'
anchor = '      - postiz-uploads:/uploads/\n'
add = ''.join('      - ./overrides/v2.25.3/%s.provider.js:%s/%s.provider.js:ro\n' % (x, D, x) for x in ('facebook', 'instagram'))
if add not in s:
    assert s.count(anchor) == 1, 'BLOCKED: compose anchor'
    s = s.replace(anchor, anchor + add)
open(p + '.tmp', 'w').write(s)
import os; os.replace(p + '.tmp', p)
p = 'providers.env'
lines = [l for l in open(p).read().splitlines() if not l.startswith('POSTIZ_META_OAUTH_ORIGIN=')]
lines.append('POSTIZ_META_OAUTH_ORIGIN=$ORIGIN')
open(p + '.tmp', 'w').write('\n'.join(lines) + '\n'); os.chmod(p + '.tmp', 0o600); os.replace(p + '.tmp', p)
PY
docker compose config -q && echo COMPOSE_VALID
docker compose up -d postiz >/dev/null 2>&1
for i in \$(seq 1 60); do s=\$(docker inspect -f '{{.State.Health.Status}}' postiz); [ \"\$s\" = healthy ] && break; sleep 5; done
echo POSTIZ_HEALTH=\$s; echo ROLLBACK_BACKUP=\$B
echo FRONTEND_URL=\$(docker exec postiz printenv FRONTEND_URL)"
  ;;
rollback)
  remote "set -e; cd /opt/nexus-app-services/postiz; B=\$(cat rollback/LATEST_META_OAUTH_APPLY)
cp -p \$B/compose.yaml compose.yaml; cp -p \$B/providers.env providers.env; chmod 600 providers.env
docker compose config -q && docker compose up -d postiz >/dev/null 2>&1
for i in \$(seq 1 60); do s=\$(docker inspect -f '{{.State.Health.Status}}' postiz); [ \"\$s\" = healthy ] && break; sleep 5; done
echo RESTORED_FROM=\$B POSTIZ_HEALTH=\$s"
  ;;
*) echo "usage: $0 status|apply|rollback" >&2; exit 2 ;;
esac
