# Hermes State Arbiter Implementation

Date: 2026-07-02

## Outcome

Hermes now resolves the conversational move and winning context before route execution. The existing domain router remains for compatibility, but it can no longer let an active session override safety explanations, provenance, response-depth changes, recommendation explanations, timeline recaps, casual turns, or explicit new domains.

## Layers implemented

1. `hermesConversationMoveClassifier.ts` classifies new domain, provenance, safety explanation, previous answer, recommendation, session navigation/continuation, active-target action, timeline, response depth, advisor, casual, and fallback moves.
2. `hermesConversationArbiter.ts` returns one `ResolvedConversationState` containing winning context, domain, target, action, response mode, source preference, stale-session disposition, clarification state, and decision reason.
3. `hermesDecisionState.ts` stores scoped last answer, last safety decision, last recommendation, and response mode.
4. `hermesActionResolver.ts` resolves targets in the required order: explicit target/rank, selected UI item, last recommendation, active focus, then last-answer target.
5. `hermesResponseModeRenderer.ts` enforces CEO, audit, trace, and casual output rules.

## Behavior changes

- `why did you block that` reads `lastSafetyDecision` and explains the external-action/approval boundary.
- Recommendation explanations beat stale report sessions.
- Active sessions win only for explicit navigation or mode-specific continuations.
- Report `next` and `previous` update focus; consecutive `next` calls no longer repeat the same item.
- Business opportunity blockers and risks use active focus and include source classification.
- Ray Review target actions return an explicit conversation-only draft with source, proposed decision, next action, and not-saved/not-submitted/not-executed proof.
- Timeline questions route to activity recap and report missing evidence plainly.
- Clear chat clears scoped decision and advisor-session memory in addition to prior memory lanes.

## Source consolidation

`cleanRecordSourceSummary()` produces `success`, `partial_success`, `empty_success`, `failed`, or `fallback_used`. Client evidence is limited to `client_profiles`; approvals/task requests are labeled adjacent context and excluded from client counts.

## Compatibility boundary

The work preserves existing route IDs and the existing router/handler ecosystem. Arbiter decisions override only when a conversational state has higher authority. This limits migration risk while consolidating the missing middle layers.

## Verification

- Focused state-arbiter and compatibility suites: 111/111 passed during implementation.
- Final focused state-arbiter suite: 10/10 passed.
- Full `npm test`: 719/719 passed across 27 files.
- `npm run build`: passed; the existing large-chunk warning remains non-fatal.
