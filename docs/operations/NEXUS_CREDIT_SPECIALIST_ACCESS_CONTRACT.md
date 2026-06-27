# Nexus Credit Specialist Access Contract

Companion to [NEXUS_CREDIT_SPECIALIST_SUPABASE_ONLY_CONTRACT.md](NEXUS_CREDIT_SPECIALIST_SUPABASE_ONLY_CONTRACT.md).

The Credit Specialist (and the Funding/Business Setup Specialists by the same pattern) operate under
a strict contract enforced in `src/lib/creditSpecialistPolicy.ts` + `src/lib/nexusAIAccessPolicy.ts`:

- **No web tools.** `creditSpecialistHasNoWebTools()` must be true.
- **Approved knowledge only.** `creditSpecialistApprovedKnowledgeOnly()` must be true; knowledge
  must be `approved` and `usable_by_credit_specialist`.
- **Vault adapter only (mock v1).** Client credit/business data is read only through the Client
  Vault adapter; no production connection.
- **Client-facing output approval-gated.** Drafts are internal until Ray approves.

These properties are asserted by `scripts/ai_access/verify_ai_department_access.py` and reported by
`scripts/ai_access/generate_credit_specialist_contract_report.py`.
