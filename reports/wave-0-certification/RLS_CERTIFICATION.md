# RLS Certification

Date: 2026-07-17

## Command

```bash
python3 scripts/checks/certify_authenticated_rls.py
```

Result:

- Start: 2026-07-17T17:43:50Z
- End: 2026-07-17T17:44:00Z
- Exit code: 0
- Status: PASS
- Checks: 45
- Failures: 0

## Scope

Personas:

- Persona A
- Persona B
- Persona C

Tables checked:

- `client_documents`
- `credit_report_parser_results`
- `credit_bureau_tradelines`
- `credit_canonical_accounts`
- `credit_report_discrepancies`
- `credit_strategy_matches`
- `credit_strategy_client_selections`
- `credit_strategy_evidence_links`
- `credit_strategy_drafts`
- `credit_report_comparison_runs`
- `credit_report_comparison_results`
- `strategy_outcome_observations`
- `credit_readiness_history`
- `credit_strategy_exceptions`

Mutation denial checked:

- Authenticated client mutation into `credit_strategy_versions` denied for Personas A/B/C.

## Browser RLS Evidence

Authenticated Playwright also passed:

- Client cannot access admin routes.
- Admin cannot access client portal as client.
- Persona A browser cannot read unauthorized admin-only table.
- Persona A browser sees only own documents in client workflow suite.
- Persona B cannot read Persona A storage metadata from the authenticated storage probe.

## Limitations

This is a bounded RLS certification harness, not a formal proof of every policy in the database. It confirms the current Wave 0 customer/credit tables and authenticated browser boundaries.

RLS Gate: PASS.
