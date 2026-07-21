# Nexus 3 Dual Agent Data Boundaries

Generated: 2026-07-21

## Nexus Hermes

Nexus Hermes may use governed server-side tools for authorized internal summaries, report metadata, client aggregates, approvals, department status, revenue status, repo intelligence status, provenance, and draft-only work.

OpenRouter receives only safe identity/context, bounded recent conversation, tool schemas, and safe tool-result summaries. Supabase credentials remain server-side.

## Hermes Alpha

Hermes Alpha has no Supabase access, no service-role access, no client PII, no client documents, and no execution authority.

Alpha backend context is limited to:

- Alpha identity;
- safe static Nexus summary;
- bounded recent conversation history;
- optional public research summaries when enabled separately.

Alpha must refuse live internal Nexus facts unless Ray supplies a safe summary.

## Secrets

Provider keys remain backend-only. No `VITE_` provider key is introduced.

## Deployment

No Netlify frontend deployment was performed in this correction because Nexus Hermes failed the holdout gate.
