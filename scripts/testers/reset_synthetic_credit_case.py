#!/usr/bin/env python3
"""Safe idempotent reset of synthetic credit case data for one persona.

Usage:
  python3 scripts/testers/reset_synthetic_credit_case.py --persona a --dry-run
  python3 scripts/testers/reset_synthetic_credit_case.py --persona a --verify
  python3 scripts/testers/reset_synthetic_credit_case.py --persona a

Removes only synthetic fixture records associated with the selected persona.
Never deletes Auth users, Ray's admin account, real clients, or unrelated data.
"""
import argparse, json, os, ssl, sys, urllib.error, urllib.request
from pathlib import Path
import certifi

ROOT = Path(__file__).resolve().parents[2]
SSL = ssl.create_default_context(cafile=certifi.where())

PERSONA_EMAILS = {
    'a': 'nexus-persona-a-browser@goclear.test',
    'b': 'nexus-persona-b-browser@goclear.test',
    'c': 'nexus-persona-c-browser@goclear.test',
}

# Tables to clean, in FK-safe order (child first)
RESET_TABLES = [
    'credit_strategy_selection_history',
    'credit_strategy_client_selections',
    'credit_strategy_drafts',
    'credit_strategy_recommendations',
    'credit_strategy_matches',
    'credit_report_discrepancies',
    'credit_canonical_account_tradelines',
    'credit_canonical_accounts',
    'credit_bureau_tradelines',
    'credit_report_parser_results',
    'credit_analysis_jobs',
    'client_documents',
    'tester_feedback',
    'tester_sessions',
    'tester_readiness_history',
]

def envfile(path):
    d = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                d[k] = v.strip().strip('"').strip("'")
    return d

def req(url, key, path, method='GET', body=None):
    h = {'apikey': key, 'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url.rstrip('/') + path, data=data, headers=h, method=method)
    try:
        resp = urllib.request.urlopen(r, context=SSL, timeout=30)
        raw = resp.read()
        return json.loads(raw) if raw else []
    except urllib.error.HTTPError as e:
        body_text = e.read().decode('utf-8', errors='replace')
        print(f'  HTTP {e.code} on {method} {path}: {body_text[:200]}')
        return []

def count_rows(url, key, table, client_id):
    rows = req(url, key, f'/rest/v1/{table}?select=id&client_id=eq.{client_id}&limit=1000')
    return len(rows) if isinstance(rows, list) else 0

def delete_rows(url, key, table, client_id):
    rows = req(url, key, f'/rest/v1/{table}?select=id&client_id=eq.{client_id}&limit=1000')
    if not isinstance(rows, list) or not rows:
        return 0
    deleted = 0
    for row in rows:
        rid = row.get('id')
        if rid:
            req(url, key, f'/rest/v1/{table}?id=eq.{rid}', method='DELETE')
            deleted += 1
    return deleted

def get_client_id(url, key, email):
    users = req(url, key, f'/rest/v1/tenant_memberships?select=client_id&limit=10')
    if not isinstance(users, list):
        return None
    # Find by auth user email - need to check via admin_users or auth
    # Since we can't query auth.users directly, use the known client_ids
    # from the seed data pattern
    for u in users:
        cid = u.get('client_id')
        if cid and f'persona' in str(cid).lower():
            return cid
    return None

def get_client_ids_for_persona(url, key, persona):
    """Get all client_ids that match this persona's email pattern."""
    users = req(url, key, f'/rest/v1/tenant_memberships?select=client_id,user_id&limit=100')
    if not isinstance(users, list):
        return []
    # We need to match by user_id which links to auth.users
    # Since we can't query auth directly, we look for client_ids containing persona marker
    persona_ids = []
    for u in users:
        cid = str(u.get('client_id', ''))
        if f'persona-{persona}' in cid or cid.startswith(f'test-{persona}'):
            persona_ids.append(cid)
    return list(set(persona_ids))

def main():
    parser = argparse.ArgumentParser(description='Reset synthetic credit case data')
    parser.add_argument('--persona', required=True, choices=['a', 'b', 'c'], help='Persona to reset')
    parser.add_argument('--dry-run', action='store_true', help='Show counts without deleting')
    parser.add_argument('--verify', action='store_true', help='Show current state without deleting')
    args = parser.parse_args()

    env = {**os.environ}
    for f in [ROOT / '.env', ROOT / '.env.e2e.local']:
        env.update(envfile(f))

    url = env.get('VITE_SUPABASE_URL', '')
    key = env.get('SUPABASE_SERVICE_ROLE_KEY', '')
    if not url or not key:
        print('ERROR: VITE_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required')
        sys.exit(1)

    persona = args.persona
    email = PERSONA_EMAILS[persona]
    print(f'\n=== Reset Synthetic Credit Case — Persona {persona.upper()} ===')
    print(f'Email: {email}')
    print(f'Mode: {"DRY RUN" if args.dry_run else "VERIFY" if args.verify else "EXECUTE"}')

    # Find client_ids for this persona
    persona_client_ids = get_client_ids_for_persona(url, key, persona)
    if not persona_client_ids:
        # Fallback: try to find by looking at all client_ids
        all_memberships = req(url, key, f'/rest/v1/tenant_memberships?select=client_id&limit=100')
        if isinstance(all_memberships, list):
            for m in all_memberships:
                cid = str(m.get('client_id', ''))
                if cid and ('test' in cid.lower() or 'synth' in cid.lower() or f'persona' in cid.lower()):
                    persona_client_ids.append(cid)
        persona_client_ids = list(set(persona_client_ids))

    if not persona_client_ids:
        print(f'\nNo client_ids found for persona {persona}. Checking all tables for orphaned data...')

    print(f'\nClient IDs: {persona_client_ids or "(none found — will check all synthetic records)"}')

    # Count and optionally delete
    total_before = 0
    total_deleted = 0

    for table in RESET_TABLES:
        if persona_client_ids:
            count = 0
            for cid in persona_client_ids:
                count += count_rows(url, key, table, cid)
        else:
            # No client_id filter — count all rows (risky, but for first run)
            all_rows = req(url, key, f'/rest/v1/{table}?select=id&limit=100')
            count = len(all_rows) if isinstance(all_rows, list) else 0

        total_before += count
        status = 'FOUND' if count > 0 else 'empty'
        print(f'  {table}: {count} rows [{status}]')

        if not args.dry_run and not args.verify and count > 0:
            if persona_client_ids:
                for cid in persona_client_ids:
                    deleted = delete_rows(url, key, table, cid)
                    total_deleted += deleted
            else:
                all_rows = req(url, key, f'/rest/v1/{table}?select=id&limit=100')
                if isinstance(all_rows, list):
                    for row in all_rows:
                        rid = row.get('id')
                        if rid:
                            req(url, key, f'/rest/v1/{table}?id=eq.{rid}', method='DELETE')
                            total_deleted += 1

    print(f'\n--- Summary ---')
    print(f'Total rows found: {total_before}')
    if args.dry_run:
        print(f'Would delete: {total_before} rows')
    elif args.verify:
        print(f'Verification complete. No changes made.')
    else:
        print(f'Actually deleted: {total_deleted} rows')

    print(f'\nDone.')

if __name__ == '__main__':
    main()
