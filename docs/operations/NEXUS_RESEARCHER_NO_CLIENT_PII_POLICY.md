# Nexus Researcher AI — No Client PII Policy

Source: `src/config/researcherAIAccessContract.ts`.

## Researcher AI may

Browse public sources; research credit laws/concepts, business credit rules, funding rules, and
affiliate programs; create PROPOSED/draft knowledge records; create source summaries.

## Researcher AI must NOT

Access client records, credit reports, SmartCredit imports, bank statements, client letters, or
funding documents; generate client-specific recommendations.

## Knowledge flow

Researcher AI output is always `proposed`/`draft`. It must be reviewed and approved (status
`approved`, `usable_by_credit_specialist = true`) before the Credit Specialist may use it. See
[NEXUS_APPROVED_KNOWLEDGE_MODEL.md](NEXUS_APPROVED_KNOWLEDGE_MODEL.md).

Verify: `python3 scripts/ai_access/verify_ai_department_access.py --dry-run --json`.
