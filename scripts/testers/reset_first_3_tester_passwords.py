#!/usr/bin/env python3
"""
Reset First 3 Tester Passwords — Dry-run by default.

Usage:
  python3 scripts/testers/reset_first_3_tester_passwords.py --dry-run
  python3 scripts/testers/reset_first_3_tester_passwords.py --apply

Rules:
- Generates new 18+ char passwords (safe char set)
- Updates via Supabase Admin API (service role)
- Writes new passwords to local file only
- Never prints passwords
"""

import json
import os
import secrets
import ssl
import string
import sys
import urllib.request

LOCAL_FILE = 'data/private/first_3_testers.local.json'


def gen_password(length=20):
    """Generate password with safe chars: letters, digits, !@#%"""
    safe = string.ascii_letters + string.digits + '!@#%'
    while True:
        pwd = ''.join(secrets.choice(safe) for _ in range(length))
        if any(c.isupper() for c in pwd) and any(c.isdigit() for c in pwd) and any(c in '!@#%' for c in pwd):
            return pwd


def load_local():
    with open(LOCAL_FILE) as f:
        return json.load(f)


def save_local(data):
    with open(LOCAL_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def load_env():
    env = {}
    with open('.env') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def reset_password(url, service_key, user_id, new_password):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    payload = json.dumps({'password': new_password}).encode()
    req = urllib.request.Request(
        f'{url}/auth/v1/admin/users/{user_id}',
        data=payload,
        headers={
            'Authorization': f'Bearer {service_key}',
            'Content-Type': 'application/json',
            'apikey': service_key,
        },
        method='PUT'
    )

    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            return True, 'OK'
    except Exception as e:
        return False, str(e)[:80]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    testers = load_local()
    env = load_env()

    url = env.get('VITE_SUPABASE_URL')
    service_key = env.get('SUPABASE_SERVICE_ROLE_KEY')

    if not url or not service_key:
        print("ERROR: VITE_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required")
        sys.exit(1)

    print("\n=== Password Reset ===\n")

    new_passwords = {}
    for t in testers:
        new_pwd = gen_password()
        new_passwords[t['email']] = new_pwd
        uid = t.get('auth_user_id', '')
        redacted = t['email'][:3] + '***@' + t['email'].split('@')[1]
        print(f"  {redacted:30} new password: [generated, not shown]")

    if not args.apply:
        print("\nDRY RUN — No passwords changed.")
        print("Run with --apply to reset passwords.")
        return

    print("\nApplying...")
    for t in testers:
        uid = t.get('auth_user_id', '')
        if not uid:
            print(f"  SKIP: {t['email'][:20]} — no auth_id")
            continue

        new_pwd = new_passwords[t['email']]
        ok, msg = reset_password(url, service_key, uid, new_pwd)
        redacted = t['email'][:3] + '***@' + t['email'].split('@')[1]

        if ok:
            t['temporary_password'] = new_pwd
            print(f"  {redacted:30} RESET ✓")
        else:
            print(f"  {redacted:30} FAILED: {msg}")

    save_local(testers)
    print("\nNew passwords saved to local file.")


if __name__ == '__main__':
    import argparse
    main()
