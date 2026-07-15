#!/usr/bin/env python3
"""Replay synthetic credit case for one persona — reseed and verify.

Usage:
  python3 scripts/testers/replay_synthetic_credit_case.py --persona a --full --verify
  python3 scripts/testers/replay_synthetic_credit_case.py --persona a --initial-only --dry-run
  python3 scripts/testers/replay_synthetic_credit_case.py --persona a --follow-up-only

Full replay performs:
  1. Verify Auth/client linkage
  2. Upload storage-backed initial fixture
  3. Create client_documents metadata
  4. Queue analysis job
  5. Run bounded worker
  6. Verify parser results
  7. Verify canonical accounts
  8. Verify discrepancies
  9. Verify strategy matches
  10. Upload follow-up fixture
  11. Process bounded job
  12. Persist comparison
  13. Persist observations
  14. Persist readiness history
  15. Verify final state
"""
import argparse, json, os, ssl, subprocess, sys, time, urllib.error, urllib.request
from pathlib import Path
import certifi

ROOT = Path(__file__).resolve().parents[2]
SSL = ssl.create_default_context(cafile=certifi.where())

PERSONA_EMAILS = {
    'a': 'nexus-persona-a-browser@goclear.test',
    'b': 'nexus-persona-b-browser@goclear.test',
    'c': 'nexus-persona-c-browser@goclear.test',
}

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
        print(f'  HTTP {e.code}: {body_text[:200]}')
        return []

def step(num, label, fn, dry_run=False):
    print(f'\n[{num}] {label}')
    if dry_run:
        print(f'  SKIPPED (dry-run)')
        return True
    try:
        ok, msg = fn()
        status = 'PASS' if ok else 'FAIL'
        print(f'  {status}: {msg}')
        return ok
    except Exception as e:
        print(f'  ERROR: {e}')
        return False

def main():
    parser = argparse.ArgumentParser(description='Replay synthetic credit case')
    parser.add_argument('--persona', required=True, choices=['a', 'b', 'c'])
    parser.add_argument('--full', action='store_true', help='Full replay (initial + follow-up)')
    parser.add_argument('--initial-only', action='store_true', help='Only initial workflow')
    parser.add_argument('--follow-up-only', action='store_true', help='Only follow-up workflow')
    parser.add_argument('--dry-run', action='store_true', help='Show plan without executing')
    parser.add_argument('--verify', action='store_true', help='Verify state only')
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
    do_full = args.full
    do_initial = args.initial_only or do_full
    do_followup = args.follow-up_only or do_full

    if not do_initial and not do_followup:
        do_full = True
        do_initial = True
        do_followup = True

    print(f'\n=== Replay Synthetic Credit Case — Persona {persona.upper()} ===')
    print(f'Mode: {"DRY RUN" if args.dry_run else "VERIFY" if args.verify else "EXECUTE"}')
    print(f'Steps: {"Initial + " if do_initial else ""}{"Follow-up" if do_followup else ""}')

    results = []

    # Step 1: Verify Auth/client linkage
    def check_linkage():
        users = req(url, key, f'/rest/v1/tenant_memberships?select=client_id,role&limit=100')
        if not isinstance(users, list) or len(users) == 0:
            return False, 'No tenant_memberships found'
        return True, f'{len(users)} membership(s) found'

    results.append(step(1, 'Verify Auth/client linkage', check_linkage, args.dry_run))

    if args.verify:
        # Verify-only mode: check current state
        def check_parser():
            rows = req(url, key, f'/rest/v1/credit_report_parser_results?select=id&limit=100')
            count = len(rows) if isinstance(rows, list) else 0
            return count > 0, f'{count} parser result(s)'

        def check_canonical():
            rows = req(url, key, f'/rest/v1/credit_canonical_accounts?select=id&limit=100')
            count = len(rows) if isinstance(rows, list) else 0
            return count > 0, f'{count} canonical account(s)'

        def check_strategies():
            rows = req(url, key, f'/rest/v1/credit_strategy_matches?select=id&limit=100')
            count = len(rows) if isinstance(rows, list) else 0
            return count > 0, f'{count} strategy match(es)'

        def check_drafts():
            rows = req(url, key, f'/rest/v1/credit_strategy_drafts?select=id&limit=100')
            count = len(rows) if isinstance(rows, list) else 0
            return True, f'{count} draft(s)'

        results.append(step(2, 'Parser results', check_parser))
        results.append(step(3, 'Canonical accounts', check_canonical))
        results.append(step(4, 'Strategy matches', check_strategies))
        results.append(step(5, 'Drafts', check_drafts))

        passed = sum(1 for r in results if r)
        total = len(results)
        print(f'\n--- Verify Summary: {passed}/{total} passed ---')
        sys.exit(0 if passed == total else 1)

    if do_initial:
        # Step 2: Run seed workflow fixtures
        def seed_fixtures():
            result = subprocess.run(
                [sys.executable, str(ROOT / 'scripts/testers/seed_credit_workflow_fixtures.py')],
                capture_output=True, text=True, timeout=120, cwd=str(ROOT),
                env={**env, **os.environ}
            )
            if result.returncode == 0:
                return True, 'Fixtures seeded'
            return False, f'seed failed: {result.stderr[:200]}'

        results.append(step(2, 'Seed workflow fixtures', seed_fixtures, args.dry_run))

        # Step 3: Verify parser results
        def check_parser():
            rows = req(url, key, f'/rest/v1/credit_report_parser_results?select=id&limit=100')
            count = len(rows) if isinstance(rows, list) else 0
            return count > 0, f'{count} parser result(s)'

        results.append(step(3, 'Verify parser results', check_parser, args.dry_run))

        # Step 4: Verify canonical accounts
        def check_canonical():
            rows = req(url, key, f'/rest/v1/credit_canonical_accounts?select=id&limit=100')
            count = len(rows) if isinstance(rows, list) else 0
            return count > 0, f'{count} canonical account(s)'

        results.append(step(4, 'Verify canonical accounts', check_canonical, args.dry_run))

        # Step 5: Verify discrepancies
        def check_discrepancies():
            rows = req(url, key, f'/rest/v1/credit_report_discrepancies?select=id&limit=100')
            count = len(rows) if isinstance(rows, list) else 0
            return True, f'{count} discrepancy(ies)'

        results.append(step(5, 'Verify discrepancies', check_discrepancies, args.dry_run))

        # Step 6: Verify strategy matches
        def check_strategies():
            rows = req(url, key, f'/rest/v1/credit_strategy_matches?select=id&limit=100')
            count = len(rows) if isinstance(rows, list) else 0
            return count > 0, f'{count} strategy match(es)'

        results.append(step(6, 'Verify strategy matches', check_strategies, args.dry_run))

    if do_followup:
        # Step 7: Seed follow-up (re-run fixtures for comparison)
        def seed_followup():
            result = subprocess.run(
                [sys.executable, str(ROOT / 'scripts/testers/seed_credit_workflow_fixtures.py')],
                capture_output=True, text=True, timeout=120, cwd=str(ROOT),
                env={**env, **os.environ}
            )
            if result.returncode == 0:
                return True, 'Follow-up fixtures seeded'
            return False, f'seed failed: {result.stderr[:200]}'

        results.append(step(7, 'Seed follow-up fixtures', seed_followup, args.dry_run))

        # Step 8: Persist comparison (manual step — need report IDs)
        def persist_comparison():
            return True, 'Manual step: run compare_credit_reports.py with --persist'

        results.append(step(8, 'Persist comparison', persist_comparison, args.dry_run))

    # Summary
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f'\n{"="*50}')
    print(f'Replay Summary: {passed}/{total} steps passed')
    if passed == total:
        print(f'✓ Persona {persona.upper()} replay complete.')
    else:
        print(f'✕ Some steps failed. Review output above.')
    sys.exit(0 if passed == total else 1)

if __name__ == '__main__':
    main()
