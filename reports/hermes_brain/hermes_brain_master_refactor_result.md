# Hermes Brain Master Refactor Result

Date: 2026-07-02

## Root cause confirmed

The audit diagnosis was correct: omitted natural-language intent variants fell through to broad domain/fallback handlers, while renderer text described source permission instead of operational evidence. Module-global unscoped memory then made otherwise-correct continuity unsafe across chat contexts.

## Architecture changes

- Added explicit prompt-kind detection ahead of broad domain routing.
- Added dedicated system health, research engine, approval/client record, specialist handoff, and evidence/provenance response contracts.
- Replaced generic `local_status` policy prose with a source/freshness/blocker status fallback.
- Added per-table Supabase success/error and `verified`/`partial`/`unverified` state.
- Separated static opportunity item provenance from live inventory results.
- Scoped conversation, selection, advisory, fallback, and routing trace memory by tenant/session.
- Connected visible clear-chat to brain-memory reset.
- Added the table-driven master prompt regression suite and boundary scenarios.

## Before and after

| Prompt | Before | After |
|---|---|---|
| `how is the system health` | Generic local evidence permission | Status, reports/evidence, blockers, freshness limits, next safe action |
| `is the research engine working` | `local_status` policy sentence | Configuration state, last report/run, unverified live boundaries, blockers, next action |
| `do we have any clients` | Could ask for a client/decision | Attempts `client_profiles`; returns count or exact auth/config/RLS blocker |
| Natural provenance wording | Could reach fallback | Last route/intent, sources, live reads, assumptions, confidence, certainty improvement |
| `prepare specialist handoff` | Generic fallback/action target | Dedicated lane/context/missing-fields/draft-status contract |
| Partial Supabase read | Any success could imply live completeness | Explicit partial verification and per-table blocker |

## Safety

No scheduler was activated. No content was published, email sent, customer charged, live trade placed, deployment performed, destructive database operation run, secret exposed, or approval gate bypassed. All action outputs remain blocked or conversation-only drafts.

## Verification

- Targeted high-risk compatibility run: 105/105 passed.
- Full repository Vitest run: 24 files, 628/628 tests passed.
- Production build: passed (`tsc --noEmit && vite build`); existing large-chunk warning remains non-fatal.
- Documentation/code whitespace check: passed.
- Authenticated browser/Supabase verification: not available in this local pass; answers expose this as a verification blocker.

Commit and push identifiers are reported in the final handoff after the release gate.
