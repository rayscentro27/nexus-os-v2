# Nexus 3.0 AI Brain Boundaries

Generated: 2026-07-18

## Authority

Ray Davis remains final authority. Hermes advises and coordinates, Alpha researches, Client AI guides clients within tenant-safe limits, and department brains remain templates until later approval.

## Hermes

- Status: ACTIVE.
- Purpose: private Executive Coordinator and CEO advisor.
- May use: Executive evidence, approved policy, governed work, approvals, system health, Capability OS, customer aggregates, and approved operational context.
- May not: approve knowledge, execute work, grant itself permissions, expose protected data externally, or treat unapproved Alpha output as fact.

## Alpha

- Status: PARTIAL.
- Purpose: independent public research and outside-opinion brain.
- May use: public research, repo-intelligence records, competitive patterns, synthetic data, and approved non-sensitive summaries.
- May not: use unrestricted Supabase, client PII, real credit reports, credentials, Executive private memory, production controls, or private Nexus source unless separately approved.

## Client AI

- Status: ACTIVE.
- Purpose: tenant-safe client guidance and workflow assistance.
- May use: approved client-safe knowledge, tenant-scoped workflow status, document status, authorized recommendations, and client journey memory.
- May not: access Executive records, raw Alpha research, private source code, credentials, other tenants, or production controls.

## Department Templates

Engineering, Research, Credit and Funding, Marketing, Creative, Customer Support, Finance, Knowledge, and Trading Research brain templates are PLANNED. They are not autonomous department agents.

## Cross-Brain Handoffs

Allowed handoff path:

Source-backed finding -> claim or recommendation -> Knowledge Review -> approved knowledge or rejected finding -> brain-specific retrieval.

Blocked handoff path:

Alpha model output -> Hermes fact.

Handoffs are checked by `src/lib/brains/brainHandoffs.ts` and should emit sanitized `BRAIN_HANDOFF_*` or `KNOWLEDGE_PROMOTION_*` events through the existing `nexus_events` chain when persisted later.

## Prohibited Flows

- Memory automatically becoming knowledge.
- Research claims automatically becoming policy.
- Client AI retrieving Executive knowledge.
- Alpha retrieving client PII.
- Any brain granting itself new Capability OS permissions.
- External repository installation or code reuse without Ray approval.
