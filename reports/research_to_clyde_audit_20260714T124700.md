# Research-to-Clyde Repository Audit

- Starting commit: `717f4bf40e133fdad31ad7a01db4a075330e794d`
- Branch/repository: `main`, `/Users/raymonddavis/nexus-os-v2`
- Existing research intake is the approved Nexus Research adapter plus `credit_strategy_sources` / `credit_strategy_claims`; it must remain canonical. Alpha has a separate local discovery inbox and produces sanitized artifacts only.
- Existing strategy architecture: 25 controlled catalog definitions, evidence scoring, bounded source ingestion/research queue, deterministic matcher, Clyde card builder, tool matrix, recommendations, append-only decisions, tool requests, and outcomes.
- Existing credit architecture: original bureau tradelines, canonical accounts, match decisions, discrepancies, system reviews, bounded analysis jobs, and sanitized workflow events.
- Existing approval architecture: active-admin RLS plus approval statuses on definitions. Existing v1 definitions lacked immutable version rows and detailed approval audit fields.
- Existing client architecture: `WorldClassClientPortal` loads client-visible recommendations and renders Clyde Strategy Cards; choices are persisted in Supabase. Evidence used the Documents Vault but was not linked to a strategy selection.
- Existing draft architecture: gated dispute previews and DocuPost safeguards. It lacked a reusable prohibited-wording validator for all strategy outputs.
- Existing security boundaries: Alpha has no Supabase/client access; frontend has no service-role key; client recommendation reads require tenant membership and `client_visible`; DocuPost requires explicit approval.

## Gaps found

Immutable governed strategy versions, source provenance scores, separate detailed claim flags, match exclusion reasons, current selection plus immutable revision history, evidence links, safe drafts, research-specific exceptions, and research-to-client audit events were incomplete. The prior Alpha guard failure was a stale test allowlist, while the URL-review server validation also needed explicit SSRF/credential/protocol protection.

## Additive plan

Extend existing source/claim/definition tables; add version, match, selection/history, evidence-link, safe-draft, exception, and audit tables; retain existing recommendations/decisions/tool requests for compatibility. Reuse the existing adapter, bounded queue, Documents Vault, client portal, admin workbench, canonical discrepancies, and exception policy. Do not duplicate the research inbox, credit parser, canonical model, letter workflow, or mail system.
