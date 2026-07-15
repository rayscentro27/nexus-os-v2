#!/usr/bin/env python3
"""Seed credit workflow test fixtures for E2E certification.
Creates parser results, canonical accounts, discrepancies, strategy matches,
and strategy recommendations for Personas A, B, C via the Supabase admin API.
Idempotent — skips rows that already exist."""
import json, os, ssl, sys, time, uuid, urllib.error, urllib.request
from pathlib import Path
import certifi

ROOT = Path(__file__).resolve().parents[2]
SSL = ssl.create_default_context(cafile=certifi.where())
PERSONAS = {
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

def req(url, key, path, method='GET', body=None, headers=None):
    h = {'apikey': key, 'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    h.update(headers or {})
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url.rstrip('/') + path, data=data, headers=h, method=method)
    resp = urllib.request.urlopen(r, context=SSL, timeout=45)
    raw = resp.read()
    return json.loads(raw) if raw else []

def find_existing(url, key, table, filters):
    from urllib.parse import quote
    parts = []
    for k, v in filters.items():
        sv = str(v)
        # URL-encode the value but preserve the PostgREST operator prefix
        if '=' in sv:
            op, val = sv.split('=', 1)
            parts.append(f'{k}={op}{quote(val, safe="")}')
        else:
            parts.append(f'{k}={quote(sv, safe="")}')
    qs = '&'.join(parts)
    return req(url, key, f'/rest/v1/{table}?{qs}&limit=1')

def upsert_row(url, key, table, row):
    """Insert or update on conflict (id). Returns the row id."""
    try:
        result = req(url, key, f'/rest/v1/{table}', method='POST', body=row,
                     headers={'Prefer': 'resolution=merge-duplicates,return=representation'})
        return result[0].get('id') if result else row.get('id')
    except urllib.error.HTTPError:
        return row.get('id')

def main():
    env = {**envfile(ROOT / '.env'), **os.environ}
    url = env.get('SUPABASE_URL') or env.get('VITE_SUPABASE_URL')
    key = env.get('SUPABASE_SERVICE_ROLE_KEY')
    if not url or not key:
        print('FAIL: server-side Supabase credentials unavailable')
        return 1

    users = req(url, key, '/auth/v1/admin/users?per_page=1000').get('users', [])
    stats = {'created': 0, 'reused': 0}

    for persona_key, email in PERSONAS.items():
        user = next((u for u in users if u.get('email', '').lower() == email), None)
        if not user:
            print(f'WARN: persona {persona_key} auth user not found, skipping')
            continue
        user_id = user['id']

        memberships = req(url, key, f'/rest/v1/tenant_memberships?user_id=eq.{user_id}&select=tenant_id,client_id&limit=1')
        if not memberships:
            print(f'WARN: persona {persona_key} has no tenant_memberships, skipping')
            continue
        tenant_id = memberships[0]['tenant_id']
        client_id = memberships[0]['client_id']

        # 1. Ensure credit report document
        doc_title = f'synthetic_persona_{persona_key}_three_bureau_report_v3.pdf'
        existing_docs = find_existing(url, key, 'client_documents',
            {'tenant_id': f'eq.{tenant_id}', 'client_id': f'eq.{client_id}', 'title': f'eq.{doc_title}'})
        if existing_docs:
            doc_id = existing_docs[0]['id']
            stats['reused'] += 1
        else:
            doc_id = str(uuid.uuid4())
            req(url, key, '/rest/v1/client_documents', method='POST', body={
                'id': doc_id, 'tenant_id': tenant_id, 'client_id': client_id,
                'category': 'credit_report', 'title': doc_title,
                'summary': f'E2E workflow certification fixture for persona {persona_key}',
                'status': 'uploaded', 'priority': 'normal', 'risk_level': 'low',
                'automation_level': 'automatic_analysis_queue',
                'client_visible': True, 'approval_required': False,
                'goclear_review_status': 'not_required',
                'source': 'client_portal_upload', 'source_concept': 'workflow_certification',
                'recommended_next_action': 'Analysis queues automatically after upload',
            })
            stats['created'] += 1

        # 2. Parser result
        parser_id = str(uuid.uuid4())
        upsert_row(url, key, 'credit_report_parser_results', {
            'id': parser_id, 'tenant_id': tenant_id, 'client_id': client_id,
            'document_id': doc_id, 'source_file_name': doc_title,
            'parser_version': 'e2e-synthetic-v1', 'extraction_mode': 'structured',
            'extraction_success': True, 'text_length': 5000, 'confidence': 'high',
            'bureaus_detected': json.dumps(['experian', 'equifax', 'transunion']),
            'accounts': json.dumps([{'name': f'Synthetic {persona_key.upper()} Card', 'type': 'revolving'}]),
            'inquiries': json.dumps([]), 'status': 'reviewed',
            'needs_specialist_review': False,
        })

        # 3. Canonical account
        canonical_id = str(uuid.uuid4())
        furnisher = 'Chase' if persona_key == 'a' else ('Capital One' if persona_key == 'b' else 'Discover')
        last4 = f'{ord(persona_key) - ord("a") + 1}234'
        upsert_row(url, key, 'credit_canonical_accounts', {
            'id': canonical_id, 'tenant_id': tenant_id, 'client_id': client_id,
            'document_id': doc_id, 'parser_result_id': parser_id,
            'normalized_creditor_label': furnisher,
            'normalized_account_type': 'revolving',
            'canonical_status': 'current',
            'match_confidence': 0.85 if persona_key != 'b' else 0.40,
            'match_tier': 'high_confidence' if persona_key != 'b' else 'ambiguous',
            'match_reasons': json.dumps(['exact_name_and_last4']),
            'conflict_reasons': json.dumps([]),
            'review_requirement': 'not_required',
            'threshold_version': 'v1', 'matching_engine_version': 'e2e-v1',
        })

        # 4. Discrepancy
        disc_id = str(uuid.uuid4())
        if persona_key == 'a':
            disc_type, bureau_vals, diff_summary = 'balance_mismatch', \
                json.dumps({'experian': {'balance': 2500}, 'equifax': {'balance': 2800}, 'transunion': {'balance': 2500}}), \
                'Balance differs across bureaus: Experian $2,500 vs Equifax $2,800 vs TransUnion $2,500'
        elif persona_key == 'b':
            disc_type, bureau_vals, diff_summary = 'status_mismatch', \
                json.dumps({'experian': {'status': 'current'}, 'equifax': {'status': 'collections'}, 'transunion': {'status': 'current'}}), \
                'Status differs: Experian current vs Equifax shows collections'
        else:
            disc_type, bureau_vals, diff_summary = 'duplicate_possible', \
                json.dumps({'experian': {'account': 'Discover It #1234'}, 'equifax': {'account': 'Discover It #1234'}, 'transunion': {'account': 'Discover It #5678'}}), \
                'Possible duplicate: same furnisher with different last-4 digits'

        upsert_row(url, key, 'credit_report_discrepancies', {
            'id': disc_id, 'tenant_id': tenant_id, 'client_id': client_id,
            'document_id': doc_id, 'parser_result_id': parser_id,
            'canonical_account_id': canonical_id,
            'discrepancy_type': disc_type,
            'involved_tradeline_ids': json.dumps([]),
            'bureau_values': bureau_vals,
            'confidence': 'high' if persona_key != 'b' else 'low',
            'severity': 'medium' if persona_key == 'a' else ('high' if persona_key == 'b' else 'low'),
            'detection_rule': f'e2e_synthetic_{disc_type}',
            'ruleset_version': 'research-to-clyde-v1',
            'explanation': f'Synthetic cross-bureau discrepancy for persona {persona_key}',
            'status': 'detected',
        })

        # 5. Strategy match
        strategy_id = 'cross_bureau_balance_review' if persona_key == 'a' else \
            ('cross_bureau_status_review' if persona_key == 'b' else 'purchased_debt_documentation')
        upsert_row(url, key, 'credit_strategy_matches', {
            'tenant_id': tenant_id, 'client_id': client_id,
            'report_id': doc_id, 'canonical_account_id': str(canonical_id),
            'discrepancy_id': str(disc_id), 'strategy_id': strategy_id,
            'strategy_version': 1,
            'match_score': 85 if persona_key != 'b' else 40,
            'match_reasons': json.dumps(['objective_discrepancy', 'approved_reusable_strategy']),
            'exclusion_reasons': json.dumps([]) if persona_key != 'b' else json.dumps(['low_confidence']),
            'status': 'presented', 'ruleset_version': 'research-to-clyde-v1',
            'client_visible': True,
        })

        # 6. Strategy recommendation (what the client portal reads)
        if persona_key == 'a':
            primary_strategy = 'Cross-Bureau Balance Review'
            questions = ['Is the Equifax balance of $2,800 correct, or should it match the other bureaus?']
            evidence = ['Recent credit report pages', 'Account statements showing correct balance']
        elif persona_key == 'b':
            primary_strategy = 'Cross-Bureau Status Review'
            questions = ['Do you recognize the collections status on Equifax?']
            evidence = ['Account status documentation', 'Payment history records']
        else:
            primary_strategy = 'Purchased Debt Documentation Review'
            questions = ['Do you have documentation showing only one account exists?']
            evidence = ['Account statements from Discover', 'Original creditor records']

        # Flatten bureau values for UI rendering: {bureau: displayValue}
        raw_bv = json.loads(bureau_vals)
        flat_bv = {}
        for b, v in raw_bv.items():
            if isinstance(v, dict):
                flat_bv[b] = f"${v.get('balance', v.get('status', v.get('account', '')))}" if 'balance' in v else v.get('status', v.get('account', str(v)))
            else:
                flat_bv[b] = str(v)

        payload = {
            'primaryStrategy': primary_strategy,
            'rationale': 'The structured discrepancy matches this approved strategy.',
            'requiredEvidence': evidence,
            'clientConfirmationQuestions': questions,
            'availableTools': ['evidence_checklist', 'dispute_letter'],
            'discrepancy': {
                'differenceSummary': diff_summary,
                'bureauValues': flat_bv,
                'accountReference': f'****{last4}',
                'accountNumberMasked': f'****{last4}',
                'fundingImpact': 'May affect Credit Profile and Tier 1 readiness.',
            },
            'documentId': doc_id,
        }
        upsert_row(url, key, 'credit_strategy_recommendations', {
            'tenant_id': tenant_id, 'client_id': client_id,
            'document_id': doc_id, 'canonical_account_id': str(canonical_id),
            'discrepancy_id': str(disc_id), 'strategy_id': strategy_id,
            'strategy_version': 1, 'status': 'generated',
            'client_visible': True, 'confidence': 'high' if persona_key != 'b' else 'low',
            'payload': json.dumps(payload),
        })

        print(f'OK: persona {persona_key} — tenant={tenant_id} client={client_id} doc={doc_id}')

    print(f'Done. Created: {stats["created"]}, Reused: {stats["reused"]}')
    return 0

if __name__ == '__main__':
    sys.exit(main())
