#!/usr/bin/env python3
"""
Direct Anon SignIn Test — Tests real Supabase auth signInWithPassword.

Usage:
  python3 scripts/testers/test_first_3_signin_with_password.py

Rules:
- Uses VITE_SUPABASE_URL + VITE_SUPABASE_ANON_KEY (anon, not service role)
- Reads passwords from data/private/first_3_testers.local.json
- Never prints passwords
- Never prints keys
- Signs out after each successful login
"""

import json
import os
import ssl
import sys
import urllib.request

LOCAL_FILE = 'data/private/first_3_testers.local.json'


def load_local():
    if not os.path.exists(LOCAL_FILE):
        print(f"ERROR: {LOCAL_FILE} not found")
        sys.exit(1)
    with open(LOCAL_FILE) as f:
        return json.load(f)


def load_env():
    env = {}
    with open('.env') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def anon_signin(url, anon_key, email, password):
    """Attempt signInWithPassword using anon key (same as frontend)."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    payload = json.dumps({'email': email, 'password': password}).encode()
    req = urllib.request.Request(
        f'{url}/auth/v1/token?grant_type=password',
        data=payload,
        headers={
            'apikey': anon_key,
            'Content-Type': 'application/json',
        },
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            result = json.loads(resp.read())
            return True, result.get('user', {}).get('id', ''), result.get('access_token', '')[:20] + '...'
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            err = json.loads(body)
            return False, err.get('error_code', ''), err.get('msg', str(e))
        except:
            return False, '', str(e)[:80]


def anon_signout(url, anon_key, access_token):
    """Sign out to clean up session."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(
        f'{url}/auth/v1/logout',
        headers={
            'apikey': anon_key,
            'Authorization': f'Bearer {access_token}',
        },
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            return True
    except:
        return False


def main():
    testers = load_local()
    env = load_env()

    url = env.get('VITE_SUPABASE_URL')
    anon_key = env.get('VITE_SUPABASE_ANON_KEY')

    if not url or not anon_key:
        print("ERROR: VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY required")
        sys.exit(1)

    print(f"\n=== Direct Anon SignIn Test ===")
    print(f"Project: {url.split('//')[1].split('.')[0] if '//' in url else 'unknown'}")
    print(f"Anon key: {'present' if anon_key else 'MISSING'}\n")

    results = []
    for t in testers:
        email = t['email']
        pwd = t['temporary_password']
        expected_id = t.get('auth_user_id', '')

        success, user_id, token_preview = anon_signin(url, anon_key, email, pwd)

        # Redact email
        parts = email.split('@')
        redacted = parts[0][:3] + '***@' + parts[1]

        id_match = ''
        if success and expected_id:
            id_match = '✓ match' if user_id == expected_id else f'✗ mismatch (expected {expected_id[:8]}...)'

        status = 'PASS' if success else 'FAIL'
        print(f"  {redacted:30} {status:5} {id_match}")

        if not success:
            print(f"    error_code: {user_id}")
            print(f"    message: {token_preview}")

        if success and token_preview:
            anon_signout(url, anon_key, token_preview + '...')

        results.append({'email': redacted, 'success': success})

    passed = sum(1 for r in results if r['success'])
    total = len(results)
    print(f"\n=== Result: {passed}/{total} passed ===")

    if passed == 0:
        print("\nALL TESTS FAILED — passwords may not match Supabase Auth.")
        print("Recommend: Reset passwords in Phase C.")
    elif passed < total:
        print(f"\n{total - passed} FAILED — partial auth issue.")
    else:
        print("\nALL TESTS PASSED — Auth is working. Check frontend/Netlify.")


if __name__ == '__main__':
    main()
