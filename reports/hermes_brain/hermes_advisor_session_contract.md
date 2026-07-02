# Hermes Advisor Session Contract

**Date:** 2026-07-02
**Module:** `src/lib/hermesAdvisorSession.ts`
**Status:** Implemented and verified

---

## Purpose

The advisor session manager provides session-scoped review state for Hermes. When a user starts a domain review (e.g., "pull up the business opportunity report"), the session manager creates a scoped context that persists across follow-up turns within the same tenant/session.

This solves the core problem: follow-up questions like "why did it get that score?" or "how can we improve it?" need to know *which item* is being discussed. Without a session, Hermes had no way to resolve "it."

---

## Session Design

### Scope

Sessions are scoped by `scopeKey`, which is constructed from `tenantId:sessionId`. Each user/tenant gets their own session store. Sessions are isolated — actions in one tenant's session do not affect another.

### Lifecycle

1. **Creation** — `startReviewSession(scopeKey, domain, mode)` creates a new session, overwriting any existing session for that scope key
2. **Updates** — `updateSessionSource`, `updateSessionList`, `setSessionFocus`, `setSessionRecommendation`, `setSessionPendingDraft`, `setSessionAdvisoryContext` modify the session in place
3. **Turn advance** — `advanceSessionTurn(scopeKey)` increments the turn counter on each message
4. **Expiry** — Sessions expire after `expiresAfterTurns` (default: 10) turns of inactivity. `getActiveSession` returns `null` for expired sessions and auto-deletes them
5. **Clear** — `clearSession(scopeKey)` immediately removes the session

### Data Model (`NexusSessionContext`)

| Field | Type | Purpose |
|---|---|---|
| `activeDomain` | `string` | The business domain being reviewed |
| `activeMode` | `ReviewMode` | Type of review: business_opportunity_review, approval_review, etc. |
| `activeSource` | `SessionSource` | Where the review data came from (supabase, report, static, page, trace) |
| `activeList` | `SessionItem[]` | The list of items being reviewed, with rank, label, score, evidence |
| `currentFocus` | `SessionFocus` | The specific item currently being discussed |
| `lastRecommendation` | `SessionRecommendation` | Last recommendation made in this session |
| `pendingDraftTarget` | `SessionPendingDraft` | A draft Ray Review or handoff being prepared |
| `lastAdvisoryContext` | `SessionAdvisoryContext` | Advisory context for follow-up questions |
| `turnCount` | `number` | Number of turns since session creation |
| `expiresAfterTurns` | `number` | Maximum turns before session expiry |
| `scopeKey` | `string` | The tenant:session scope key |

### Target Resolution

`resolveTargetFromSession(scopeKey, targetHint)` resolves a user's reference to a specific session item:

1. If `targetHint.label` is provided, search `activeList` for a label match (case-insensitive contains)
2. If `targetHint.rank` is provided, search `activeList` for a rank match
3. If no match, fall back to `currentFocus` (the last item being discussed)
4. If no focus, fall back to the highest-scored item in `activeList`
5. If no list, return `null`

---

## Review Modes

| Mode | Domain | Description |
|---|---|---|
| `business_opportunity_review` | business_opportunities | Reviewing ranked business opportunities |
| `approval_review` | approvals | Reviewing pending approvals or Ray Reviews |
| `client_review` | clients | Reviewing client profiles |
| `monetization_review` | monetization | Reviewing monetization strategies |
| `research_review` | research | Reviewing research sources |
| `system_health_review` | system_health | Reviewing system health status |
| `product_build_planning` | nexus_product_build | Planning Nexus product features |

---

## Integration

- **Pipeline:** `hermesBrainPipeline.ts` calls `startBusinessOpportunityReview`, `explainScore`, `improveOpportunity`, and `draftRayReviewForOpportunity` from `hermesBusinessOpportunityReview.ts`
- **Router:** The intent frame's `advisory_followup` routing is gated on active advisory continuity, which is separate from session state
- **Voice-ready:** Session responses are passed through `renderVoiceReady` for plain-answer extraction

---

## Tests

`tests/hermes_structural_refactor.test.ts` covers:
- Session start returns structured response with activeMode, activeList, voiceReady
- Score explanation resolves the focused item and returns scoring factors
- Improvement suggestions return actionable next steps
- Ray Review draft resolves named targets and creates pendingDraftTarget
- Follow-up questions ("how can we improve it") do not produce fallback clarification

---

## Remaining Weaknesses

1. **In-memory only** — sessions are not persisted; a server restart clears all sessions. A database or Redis-backed session store would be needed for production durability
2. **No concurrent session limit** — a user could theoretically create many sessions without expiry; a maximum active session count would help
3. **Turn counter is message-based** — a user who sends many quick messages could expire a session faster than expected; time-based expiry would be more predictable
4. **Static opportunity data** — the business opportunity list is hardcoded; a live Supabase query with static fallback would provide real data when available
5. **No session persistence across page reloads** — the frontend would need to send the scope key on each message to maintain session continuity
