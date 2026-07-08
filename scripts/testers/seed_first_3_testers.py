#!/usr/bin/env python3
"""
Seed First 3 Testers — Dry-run by default.

Usage:
  python3 seed_first_3_testers.py                    # Dry-run (preview only)
  python3 seed_first_3_testers.py --apply            # Actually write to DB
  python3 seed_first_3_testers.py --dry-run          # Explicit dry-run

Requires:
  data/private/first_3_testers.local.json
  (maps placeholder emails to real auth user IDs)

Rules:
- Never prints secrets
- Never runs --apply without local file
- Never runs --apply with placeholder auth IDs
- Uses actual Nexus schema tables only
"""

import argparse
import json
import os
import sys

ACTUAL_TABLES = [
    'tenant_memberships',
    'client_profiles',
    'readiness_scores',
    'client_tasks',
    'client_documents',
    'credit_workflow_items',
    'business_profile_requirements',
    'approved_client_guidance',
]

LOCAL_FILE = 'data/private/first_3_testers.local.json'
TEMPLATE_FILE = 'data/first_3_testers_seed_template.json'


def load_template():
    if not os.path.exists(TEMPLATE_FILE):
        print(f"ERROR: Template not found: {TEMPLATE_FILE}")
        sys.exit(1)
    with open(TEMPLATE_FILE) as f:
        return json.load(f)


def load_local_testers():
    if not os.path.exists(LOCAL_FILE):
        print(f"ERROR: Local tester file not found: {LOCAL_FILE}")
        print("Create it with real auth user IDs from Supabase Dashboard.")
        print("See reports/testers/first_3_tester_manual_seed_steps_latest.md")
        sys.exit(1)
    with open(LOCAL_FILE) as f:
        return json.load(f)


def generate_client_id(auth_user_id):
    """Generate client_id from auth user ID (matching bootstrap trigger pattern)."""
    return 'gc_' + auth_user_id.replace('-', '')


def dry_run(template, local_testers):
    print("\n=== DRY RUN — No changes will be made ===\n")
    print(f"Tables that will be written to: {', '.join(ACTUAL_TABLES)}\n")

    for i, tester in enumerate(template):
        local = local_testers[i] if i < len(local_testers) else None
        auth_id = local.get('auth_user_id', 'PENDING') if local else 'PENDING'
        email = local.get('email', tester['auth_email_placeholder']) if local else tester['auth_email_placeholder']
        client_id = generate_client_id(auth_id) if auth_id != 'PENDING' else f"gc_{tester['client_id_prefix']}"

        print(f"--- Tester {tester['tester_number']} ---")
        print(f"  Email: {email}")
        print(f"  Auth ID: {auth_id[:8]}... (redacted)")
        print(f"  Client ID: {client_id}")
        print(f"  Display: {tester['display_name']}")
        print(f"  Step: {tester['current_step']}")
        print(f"  Rows to create:")
        print(f"    tenant_memberships: 1")
        print(f"    client_profiles: 1")
        print(f"    readiness_scores: {len(tester['readiness_scores'])}")
        print(f"    client_tasks: {len(tester['client_tasks'])}")
        print(f"    client_documents: {len(tester['client_documents'])}")
        print(f"    credit_workflow_items: {len(tester['credit_workflow_items'])}")
        print(f"    business_profile_requirements: {len(tester['business_profile_requirements'])}")
        print(f"    approved_client_guidance: {len(tester['approved_client_guidance'])}")
        print()

    print("To apply, run with --apply flag.")
    print("Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in environment.")


def apply_testers(template, local_testers, supabase_url, service_key):
    import urllib.request

    print("\n=== APPLYING — Writing to live database ===\n")

    for i, tester in enumerate(template):
        local = local_testers[i] if i < len(local_testers) else None
        if not local:
            print(f"SKIP: No local data for tester {tester['tester_number']}")
            continue

        auth_id = local.get('auth_user_id', '')
        if not auth_id or 'PASTE' in auth_id:
            print(f"SKIP: Tester {tester['tester_number']} has placeholder auth ID")
            continue

        email = local.get('email', '')
        client_id = generate_client_id(auth_id)
        tenant_id = 'goclear'

        print(f"Creating tester {tester['tester_number']}: {email[:20]}...")

        # Build all rows
        rows = []

        # tenant_memberships
        rows.append({
            'table': 'tenant_memberships',
            'data': {'tenant_id': tenant_id, 'user_id': auth_id, 'role': 'client', 'client_id': client_id}
        })

        # client_profiles
        rows.append({
            'table': 'client_profiles',
            'data': {
                'tenant_id': tenant_id, 'client_id': client_id,
                'title': tester['display_name'], 'status': 'active',
                'client_visible': True, 'category': 'tester',
                'payload': {'currentStep': tester['current_step'], 'membershipTier': 'GoClear Readiness'}
            }
        })

        # readiness_scores
        for rs in tester['readiness_scores']:
            rows.append({
                'table': 'readiness_scores',
                'data': {
                    'id': f"{client_id}_{rs['category']}", 'tenant_id': tenant_id, 'client_id': client_id,
                    'category': rs['category'], 'title': rs['title'], 'score': rs['score'],
                    'status': rs['status'], 'client_visible': rs['client_visible']
                }
            })

        # client_tasks
        for t in tester['client_tasks']:
            rows.append({
                'table': 'client_tasks',
                'data': {
                    'id': f"{client_id}_task_{t['title'][:20].replace(' ', '_').lower()}",
                    'tenant_id': tenant_id, 'client_id': client_id,
                    'category': t['category'], 'title': t['title'],
                    'status': t['status'], 'priority': t['priority'],
                    'client_visible': t['client_visible']
                }
            })

        # client_documents
        for d in tester['client_documents']:
            rows.append({
                'table': 'client_documents',
                'data': {
                    'id': f"{client_id}_doc_{d['title'][:20].replace(' ', '_').lower()}",
                    'tenant_id': tenant_id, 'client_id': client_id,
                    'category': d['category'], 'title': d['title'],
                    'status': d['status'], 'client_visible': d['client_visible']
                }
            })

        # credit_workflow_items
        for c in tester['credit_workflow_items']:
            rows.append({
                'table': 'credit_workflow_items',
                'data': {
                    'id': f"{client_id}_credit_{c['title'][:20].replace(' ', '_').lower()}",
                    'tenant_id': tenant_id, 'client_id': client_id,
                    'category': c['category'], 'title': c['title'],
                    'status': c['status'], 'client_visible': c['client_visible']
                }
            })

        # business_profile_requirements
        for b in tester['business_profile_requirements']:
            rows.append({
                'table': 'business_profile_requirements',
                'data': {
                    'id': f"{client_id}_biz_{b['title'][:20].replace(' ', '_').lower()}",
                    'tenant_id': tenant_id, 'client_id': client_id,
                    'category': b['category'], 'title': b['title'],
                    'status': b['status'], 'client_visible': b['client_visible']
                }
            })

        # approved_client_guidance
        for g in tester['approved_client_guidance']:
            rows.append({
                'table': 'approved_client_guidance',
                'data': {
                    'id': f"{client_id}_guidance_{g['title'][:20].replace(' ', '_').lower()}",
                    'tenant_id': tenant_id, 'client_id': client_id,
                    'category': g['category'], 'title': g['title'],
                    'summary': g['summary'], 'status': g['status'],
                    'client_visible': g['client_visible'],
                    'approval_required': g['approval_required']
                }
            })

        # Write rows via Supabase REST API
        success_count = 0
        error_count = 0
        for row in rows:
            try:
                payload = json.dumps(row['data']).encode()
                req = urllib.request.Request(
                    f"{supabase_url}/rest/v1/{row['table']}",
                    data=payload,
                    headers={
                        'Authorization': f'Bearer {service_key}',
                        'Content-Type': 'application/json',
                        'apikey': service_key,
                        'Prefer': 'resolution=merge-duplicates'
                    },
                    method='POST'
                )
                with urllib.request.urlopen(req) as resp:
                    if resp.status in (200, 201):
                        success_count += 1
                    else:
                        error_count += 1
            except Exception as e:
                error_count += 1
                print(f"  ERROR ({row['table']}): {str(e)[:60]}")

        print(f"  Result: {success_count} created, {error_count} errors")

    print("\n=== Complete ===")


def main():
    parser = argparse.ArgumentParser(description="Seed first 3 testers")
    parser.add_argument('--apply', action='store_true', help='Actually write to database')
    parser.add_argument('--dry-run', action='store_true', help='Preview only (default)')
    args = parser.parse_args()

    template = load_template()

    if not args.apply:
        local_testers = []
        if os.path.exists(LOCAL_FILE):
            local_testers = load_local_testers()
        dry_run(template, local_testers)
        return

    # Apply mode — require local file and env vars
    local_testers = load_local_testers()

    supabase_url = os.environ.get('SUPABASE_URL') or os.environ.get('VITE_SUPABASE_URL')
    service_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')

    if not supabase_url or not service_key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        sys.exit(1)

    dry_run(template, local_testers)

    confirm = input("\nType 'YES APPLY' to write to live database: ")
    if confirm != 'YES APPLY':
        print("Aborted.")
        sys.exit(0)

    apply_testers(template, local_testers, supabase_url, service_key)


if __name__ == '__main__':
    main()
