#!/usr/bin/env python3
"""
Create First 3 Auth Users — Dry-run by default.

Usage:
  python3 create_first_3_auth_users.py --dry-run   # Preview
  python3 create_first_3_auth_users.py --apply      # Create users

Requires:
  data/private/first_3_testers.local.json
  SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY in env

Rules:
- Never prints passwords
- Never prints secrets
- Writes auth_user_id back to local file only
- Creates email-confirmed users for instant login
"""

import argparse
import json
import os
import sys
import urllib.request

LOCAL_FILE = 'data/private/first_3_testers.local.json'


def load_local():
    if not os.path.exists(LOCAL_FILE):
        print(f"ERROR: {LOCAL_FILE} not found")
        sys.exit(1)
    with open(LOCAL_FILE) as f:
        return json.load(f)


def save_local(data):
    with open(LOCAL_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def dry_run(testers):
    print("\n=== DRY RUN — No users will be created ===\n")
    for t in testers:
        uid = t.get('auth_user_id') or 'NOT YET CREATED'
        print(f"  Tester {t['tester_number']}: {t['email']}")
        print(f"    Name: {t['display_name']}")
        print(f"    Auth ID: {uid[:8] + '...' if uid != 'NOT YET CREATED' else uid}")
        print(f"    Password: [hidden]")
        print()


def apply_users(testers, supabase_url, service_key):
    print("\n=== APPLYING — Creating auth users ===\n")
    updated = False

    for t in testers:
        if t.get('auth_user_id'):
            print(f"  SKIP: Tester {t['tester_number']} already has auth_id")
            continue

        print(f"  Creating: {t['email'][:20]}...")

        payload = json.dumps({
            'email': t['email'],
            'password': t['temporary_password'],
            'email_confirm': True,
            'user_metadata': {'name': t['display_name'], 'role': 'client'}
        }).encode()

        req = urllib.request.Request(
            f"{supabase_url}/auth/v1/admin/users",
            data=payload,
            headers={
                'Authorization': f'Bearer {service_key}',
                'Content-Type': 'application/json',
                'apikey': service_key,
            }
        )

        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read())
                user_id = result.get('id', '')
                t['auth_user_id'] = user_id
                updated = True
                print(f"    ✓ Created: {user_id[:8]}...")
        except Exception as e:
            print(f"    ✗ Error: {str(e)[:80]}")

    if updated:
        save_local(testers)
        print("\n  Auth user IDs saved to local file.")
    print("\n=== Complete ===")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    testers = load_local()

    if not args.apply:
        dry_run(testers)
        return

    supabase_url = os.environ.get('SUPABASE_URL') or os.environ.get('VITE_SUPABASE_URL')
    service_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')

    if not supabase_url or not service_key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required")
        sys.exit(1)

    dry_run(testers)
    confirm = input("Type 'YES APPLY' to create auth users: ")
    if confirm != 'YES APPLY':
        print("Aborted.")
        sys.exit(0)

    apply_users(testers, supabase_url, service_key)


if __name__ == '__main__':
    main()
