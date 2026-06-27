# Nexus Credit Specialist Supabase-Only Contract

The Credit Specialist AI is Supabase-only. Source: `src/config/creditSpecialistAccessContract.ts`,
`src/lib/creditSpecialistPolicy.ts`. See also
[NEXUS_CREDIT_SPECIALIST_ACCESS_CONTRACT.md](NEXUS_CREDIT_SPECIALIST_ACCESS_CONTRACT.md).

## May use

Approved credit knowledge, approved dispute rules, approved funding-readiness rules, approved
compliance language, mock client credit report data (via Client Vault adapter), mock client business
setup data (via adapter), client workflow tasks (via adapter), client action plan drafts.

## Must NOT use

Internet, web browsing, YouTube, unapproved research, external AI on client data, the raw/production
Client Vault connection, production SmartCredit files.

## Knowledge gate

`creditSpecialistMayUseKnowledge(k)` returns true only when `k.approval_status === 'approved'` AND
`k.usable_by_credit_specialist === true`. Researcher AI can only create proposed/draft knowledge.

Verify: `python3 scripts/ai_access/generate_credit_specialist_contract_report.py --dry-run --json`.
