# Nexus Approved Knowledge Model

Source: `src/config/nexusApprovedKnowledge.ts`.

## Statuses

`draft → needs_review → approved` (or `retired` / `blocked`).

## Fields

`topic, category, source_type, source_url, source_summary, extracted_rule, compliance_notes,
approval_status, approved_by, approved_at, usable_by_credit_specialist, usable_by_client_chat,
retired_reason`.

## Rules

- Researcher AI may create only `draft`/proposed knowledge.
- The Credit Specialist may use an entry only when `approval_status === 'approved'` AND
  `usable_by_credit_specialist === true` (`isUsableByCreditSpecialist`).
- The Client Chat AI may use an entry only when approved AND `usable_by_client_chat === true`.
- Unapproved knowledge is never used for client recommendations.

This implements the audit/knowledge flow referenced by the AI access controls and the Credit
Specialist Supabase-only contract.
