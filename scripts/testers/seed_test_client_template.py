#!/usr/bin/env python3
"""
Tester Client Seed Template — Dry-run by default.

Usage:
  python3 seed_test_client_template.py                    # Dry-run (preview only)
  python3 seed_test_client_template.py --write            # Actually create users
  python3 seed_test_client_template.py --count 5          # Create 5 testers
  python3 seed_test_client_template.py --emails t1,t2,t3  # Custom emails

Rules:
- Never prints secrets
- Never commits real data
- Warns before any remote write
- Placeholder data only by default
"""

import argparse
import json
import os
import sys
import hashlib
import secrets

# Placeholder tester data
PLACEHOLDER_TESTERS = [
    {"name": "Alex Rivera", "email": "tester1@goclear.test"},
    {"name": "Jordan Chen", "email": "tester2@goclear.test"},
    {"name": "Sam Williams", "email": "tester3@goclear.test"},
    {"name": "Casey Morgan", "email": "tester4@goclear.test"},
    {"name": "Taylor Kim", "email": "tester5@goclear.test"},
    {"name": "Robin Patel", "email": "tester6@goclear.test"},
    {"name": "Drew Foster", "email": "tester7@goclear.test"},
    {"name": "Jamie Santos", "email": "tester8@goclear.test"},
    {"name": "Avery Brooks", "email": "tester9@goclear.test"},
    {"name": "Quinn Davis", "email": "tester10@goclear.test"},
]

def generate_password():
    """Generate a random placeholder password."""
    return secrets.token_urlsafe(12) + "A1!"

def dry_run(testers):
    """Preview what would be created."""
    print("\n=== DRY RUN — No changes will be made ===\n")
    print(f"Would create {len(testers)} test users:\n")
    for i, t in enumerate(testers, 1):
        client_id = f"gc_{hashlib.md5(t['email'].encode()).hexdigest()[:16]}"
        print(f"  {i}. {t['name']}")
        print(f"     Email: {t['email']}")
        print(f"     Password: [generated, not shown]")
        print(f"     Client ID: {client_id}")
        print(f"     Tenant: goclear")
        print(f"     Role: client")
        print()
    print("To actually create these users, run with --write flag.")
    print("NOTE: This requires SUPABASE_SERVICE_ROLE_KEY in environment.")

def write_users(testers, supabase_url, service_key):
    """Actually create users in Supabase."""
    import urllib.request
    
    print("\n=== WRITING USERS — This will create real auth users ===\n")
    
    for i, t in enumerate(testers, 1):
        password = generate_password()
        client_id = f"gc_{hashlib.md5(t['email'].encode()).hexdigest()[:16]}"
        
        print(f"  Creating {i}/{len(testers)}: {t['email']}...")
        
        # Create user via Supabase Auth Admin API
        payload = json.dumps({
            "email": t["email"],
            "password": password,
            "email_confirm": True,
            "user_metadata": {
                "name": t["name"],
                "role": "client"
            }
        }).encode()
        
        req = urllib.request.Request(
            f"{supabase_url}/auth/v1/admin/users",
            data=payload,
            headers={
                "Authorization": f"Bearer {service_key}",
                "Content-Type": "application/json",
                "apikey": service_key
            }
        )
        
        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read())
                print(f"    ✓ User created: {result.get('id', 'unknown')}")
                print(f"    → Client ID will be: {client_id}")
                print(f"    → Profile/membership auto-created by bootstrap trigger")
        except Exception as e:
            print(f"    ✗ Error: {e}")
    
    print("\n=== Complete ===")
    print("Users can now log in at https://goclearonline.cc/client/login")
    print("Change passwords on first login.")

def main():
    parser = argparse.ArgumentParser(description="Seed test client accounts")
    parser.add_argument("--write", action="store_true", help="Actually create users (default: dry-run)")
    parser.add_argument("--count", type=int, default=10, help="Number of testers to create")
    parser.add_argument("--emails", type=str, help="Comma-separated custom emails")
    args = parser.parse_args()
    
    if args.emails:
        emails = args.emails.split(",")
        testers = [{"name": f"Test User {i+1}", "email": e.strip()} for i, e in enumerate(emails)]
    else:
        testers = PLACEHOLDER_TESTERS[:args.count]
    
    if not args.write:
        dry_run(testers)
        return
    
    # Check for required env vars
    supabase_url = os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not service_key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        print("Set them in .env or export them before running with --write")
        sys.exit(1)
    
    write_users(testers, supabase_url, service_key)

if __name__ == "__main__":
    main()
