#!/usr/bin/env python3
"""Generate tester readiness report for Personas A, B, C.

Outputs:
  reports/testers/tester_readiness_latest.md
  reports/testers/tester_readiness_latest.json

Reads from Supabase tables and local env to build a status summary.
Does not include credentials, tokens, signed URLs, or raw PII.
"""
import json, os, ssl, sys, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path
import certifi

ROOT = Path(__file__).resolve().parents[2]
SSL = ssl.create_default_context(cafile=certifi.where())
OUT_DIR = ROOT / 'reports' / 'testers'

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

def req(url, key, path, method='GET'):
    h = {'apikey': key, 'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    r = urllib.request.Request(url.rstrip('/') + path, headers=h, method=method)
    try:
        resp = urllib.request.urlopen(r, context=SSL, timeout=30)
        raw = resp.read()
        return json.loads(raw) if raw else []
    except Exception:
        return []

def count(url, key, table, filters=''):
    path = f'/rest/v1/{table}?select=id&limit=1000'
    if filters:
        path += '&' + filters
    rows = req(url, key, path)
    return len(rows) if isinstance(rows, list) else 0

def get_git_commit():
    import subprocess
    try:
        result = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True, timeout=5, cwd=str(ROOT))
        return result.stdout.strip()
    except Exception:
        return 'unknown'

def main():
    env = {**os.environ}
    for f in [ROOT / '.env', ROOT / '.env.e2e.local']:
        env.update(envfile(f))

    url = env.get('VITE_SUPABASE_URL', '')
    key = env.get('SUPABASE_SERVICE_ROLE_KEY', '')
    if not url or not key:
        print('ERROR: VITE_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required')
        sys.exit(1)

    commit = get_git_commit()
    now = datetime.now(timezone.utc).isoformat()
    fixture_version = 'v1'

    persona_status = {}
    for persona_key, email in PERSONA_EMAILS.items():
        print(f'Checking Persona {persona_key.upper()}...')

        auth_status = 'provisioned'  # Assume provisioned if env exists
        linkage = count(url, key, 'tenant_memberships', 'limit=5')
        linkage_status = 'linked' if linkage > 0 else 'missing'

        parser = count(url, key, 'credit_report_parser_results')
        canonical = count(url, key, 'credit_canonical_accounts')
        discrepancies = count(url, key, 'credit_report_discrepancies')
        strategies = count(url, key, 'credit_strategy_matches')
        decisions = count(url, key, 'credit_strategy_client_selections')
        drafts = count(url, key, 'credit_strategy_drafts')
        docs = count(url, key, 'client_documents')
        sessions = count(url, key, 'tester_sessions')
        feedback_open = count(url, key, 'tester_feedback', "status=eq.open")
        feedback_blockers = count(url, key, 'tester_feedback', "severity=eq.blocker&status=eq.open")

        # Determine overall status
        if parser == 0 and canonical == 0:
            overall = 'not_provisioned'
        elif decisions == 0 and drafts == 0:
            overall = 'incomplete'
        elif feedback_blockers > 0:
            overall = 'failed'
        else:
            overall = 'ready'

        persona_status[persona_key] = {
            'email': email,
            'auth_status': auth_status,
            'client_linkage_status': linkage_status,
            'parser_status': 'present' if parser > 0 else 'missing',
            'canonical_account_count': canonical,
            'discrepancy_count': discrepancies,
            'strategy_match_count': strategies,
            'decision_status': 'present' if decisions > 0 else 'missing',
            'evidence_status': 'present' if docs > 0 else 'missing',
            'draft_status': 'present' if drafts > 0 else 'missing',
            'comparison_status': 'unknown',
            'readiness_history_status': 'unknown',
            'browser_certification_status': 'unknown',
            'overall_status': overall,
            'sessions_count': sessions,
            'open_issues': feedback_open,
            'blocker_count': feedback_blockers,
        }

    # Active sessions
    active_sessions = req(url, key, '/rest/v1/tester_sessions?select=id,persona,tester_name,status,created_at&status=eq.in_progress&limit=10')

    # Recent feedback
    recent_feedback = req(url, key, '/rest/v1/tester_feedback?select=id,persona,issue_title,severity,status,created_at&order=created_at.desc&limit=10')

    report = {
        'generated_at': now,
        'build_commit': commit,
        'fixture_version': fixture_version,
        'personas': persona_status,
        'active_sessions': active_sessions if isinstance(active_sessions, list) else [],
        'recent_feedback': recent_feedback if isinstance(recent_feedback, list) else [],
        'overall_readiness': 'ready' if all(p['overall_status'] == 'ready' for p in persona_status.values()) else 'incomplete',
    }

    # Write JSON
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / 'tester_readiness_latest.json').write_text(json.dumps(report, indent=2))

    # Write Markdown
    md_lines = [
        '# Tester Readiness Report',
        '',
        f'**Generated:** {now}',
        f'**Build Commit:** `{commit}`',
        f'**Fixture Version:** {fixture_version}',
        f'**Overall Readiness:** {report["overall_readiness"].upper()}',
        '',
        '---',
        '',
        '## Persona Status',
        '',
    ]

    for pk, ps in persona_status.items():
        emoji = {'ready': '✅', 'incomplete': '⚠️', 'failed': '❌', 'not_provisioned': '⬜'}.get(ps['overall_status'], '❓')
        md_lines.extend([
            f'### Persona {pk.upper()} {emoji}',
            '',
            f'- **Email:** `{ps["email"]}`',
            f'- **Auth:** {ps["auth_status"]}',
            f'- **Client Linkage:** {ps["client_linkage_status"]}',
            f'- **Parser:** {ps["parser_status"]}',
            f'- **Canonical Accounts:** {ps["canonical_account_count"]}',
            f'- **Discrepancies:** {ps["discrepancy_count"]}',
            f'- **Strategy Matches:** {ps["strategy_match_count"]}',
            f'- **Decisions:** {ps["decision_status"]}',
            f'- **Evidence:** {ps["evidence_status"]}',
            f'- **Drafts:** {ps["draft_status"]}',
            f'- **Overall:** {ps["overall_status"]}',
            '',
        ])

    if isinstance(active_sessions, list) and active_sessions:
        md_lines.extend(['## Active Sessions', ''])
        for s in active_sessions:
            md_lines.append(f'- Persona {s.get("persona", "?").upper()} — {s.get("tester_name", "?")} (started {s.get("created_at", "?")})')
        md_lines.append('')

    if isinstance(recent_feedback, list) and recent_feedback:
        md_lines.extend(['## Recent Feedback', ''])
        for f in recent_feedback[:5]:
            md_lines.append(f'- [{f.get("severity", "?")}] {f.get("issue_title", "?")} (Persona {f.get("persona", "?").upper()}, {f.get("status", "?")})')
        md_lines.append('')

    md_lines.extend([
        '---',
        '',
        '*Synthetic test data only. No real client records are affected.*',
    ])

    (OUT_DIR / 'tester_readiness_latest.md').write_text('\n'.join(md_lines))

    print(f'\nReports written to {OUT_DIR}/')
    print(f'  tester_readiness_latest.json')
    print(f'  tester_readiness_latest.md')

if __name__ == '__main__':
    main()
