#!/usr/bin/env python3
"""Create or reset the local-only Persona A browser account without printing credentials."""
import certifi
import json, os, secrets, ssl, sys, urllib.error, urllib.request, argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV = ROOT / '.env'
E2E_ENV = ROOT / '.env.e2e.local'
EMAILS = {'a':'nexus-persona-a-browser@goclear.test','b':'nexus-persona-b-browser@goclear.test','c':'nexus-persona-c-browser@goclear.test','admin':'nexus-admin-browser@goclear.test'}

def read_env(path):
    values = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                key, value = line.split('=', 1); values[key.strip()] = value.strip().strip('"').strip("'")
    return values

def request(url, key, method='GET', body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, method=method, headers={'apikey':key, 'Authorization':f'Bearer {key}', 'Content-Type':'application/json'})
    return json.loads(urllib.request.urlopen(req, context=ssl.create_default_context(cafile=certifi.where())).read())

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--persona',choices=EMAILS,default='a'); args=parser.parse_args()
    env = {**read_env(ENV), **os.environ}
    url, key = env.get('SUPABASE_URL') or env.get('VITE_SUPABASE_URL'), env.get('SUPABASE_SERVICE_ROLE_KEY')
    if not url or not key:
        print('FAIL: server-side Supabase credentials are unavailable'); return 1
    password = secrets.token_urlsafe(24) + 'A1!'
    try:
        users = request(f'{url}/auth/v1/admin/users?per_page=1000', key).get('users', [])
        email=EMAILS[args.persona]; existing = next((user for user in users if user.get('email','').lower() == email), None)
        metadata={'name':f'Nexus Synthetic {args.persona.title()}','role':'admin' if args.persona=='admin' else 'client','synthetic':True}
        if existing:
            request(f"{url}/auth/v1/admin/users/{existing['id']}", key, 'PUT', {'password':password, 'email_confirm':True, 'user_metadata':metadata})
            status = 'updated'
        else:
            request(f'{url}/auth/v1/admin/users', key, 'POST', {'email':email, 'password':password, 'email_confirm':True, 'user_metadata':metadata})
            status = 'created'
    except urllib.error.HTTPError as error:
        print(f'FAIL: Supabase auth request returned HTTP {error.code}'); return 1
    current={line.split('=',1)[0]:line.split('=',1)[1] for line in E2E_ENV.read_text().splitlines() if '=' in line} if E2E_ENV.exists() else {}
    prefix='ADMIN' if args.persona=='admin' else args.persona.upper();current.update({'E2E_ENABLE_AUTHENTICATED':'true',f'E2E_PERSONA_{prefix}_EMAIL' if args.persona!='admin' else 'E2E_ADMIN_EMAIL':email,f'E2E_PERSONA_{prefix}_PASSWORD' if args.persona!='admin' else 'E2E_ADMIN_PASSWORD':password})
    E2E_ENV.write_text('\n'.join(f'{k}={v}' for k,v in current.items())+'\n')
    os.chmod(E2E_ENV, 0o600)
    print(f'PASS: synthetic {args.persona} {status}; credentials saved only to ignored .env.e2e.local')
    return 0

if __name__ == '__main__': sys.exit(main())
