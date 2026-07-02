# Hermes Intent Frame and Source Authority — Structural Refactor Result

**Date:** 2026-07-02
**Status:** Implemented and verified — 693 tests passing
**Commit:** pending

---

## Root Cause Fixed

The Hermes Brain used keyword-first route matching. Every message was scanned through a chain of regex patterns in `detectPromptKind` and `routeHermesPriority` until one matched. This had three structural weaknesses:

1. **No unified intent representation.** The same message could produce different intents depending on which regex fired first. "How can we improve it" matched `advisory_followup` in the prompt-kind detector but had no structured representation of *what* to improve or *which domain* the improvement targeted.

2. **No source authority contract.** When Hermes answered a question, the user had no structured way to know which source level was used (live Supabase, latest report, static context, etc.). The source was embedded in ad-hoc text strings like `"Source checked: static Nexus offer context"` — not a first-class contract.

3. **No session-scoped review state.** When a user said "pull up the business opportunity report," Hermes returned a flat text response. Follow-up questions like "why did it get that score?" or "how can we improve it?" fell through to fallback clarification because there was no session to remember *which* opportunity was being discussed.

## Current Routing Weakness Found

The intent frame classifier is pattern-based, not LLM-based. It classifies intent, domain, target, action, safety disposition, and follow-up type from regex patterns. This means:

- Novel phrasings that don't match any pattern produce `intent: 'unknown'` and `domain: 'unknown'`, which cause the intent frame to have no routing influence.
- The classifier cannot infer implicit context. If a user says "what about the second one?" without prior list context, the intent frame detects `active_session_item` but cannot resolve which list item it refers to — only the session manager can do that.
- The `advisory_followup` intent is only useful when advisory continuity is active. Without it, the intent frame's `advisory_followup` detection is inert.

These are known limitations, not regressions. The intent frame *enhances* routing when context is available; it does not replace the existing keyword router.

---

## Intent Frame Design

### Types (`hermesIntentFrame.ts`)

The `HermesIntentFrame` interface contains:

| Field | Type | Purpose |
|---|---|---|
| `intent` | `IntentType` | High-level intent: greeting, trace_question, domain_review, advisory_followup, approval_action_draft, etc. |
| `domain` | `IntentDomain` | Business domain: business_opportunities, clients, credit_funding, etc. |
| `target` | `IntentTarget` | What the user is referring to: ranked_item, named_offer, active_session_item, page, etc. |
| `action` | `IntentAction` | What the user wants done: review, improve, explain_score, draft_ray_review, etc. |
| `sourceNeed` | `SourceNeed` | What data source the answer requires: live_records_required, report_preferred, local_trace, etc. |
| `safetyDisposition` | `SafetyDisposition` | Whether the message triggers safety: safe, approval_required, blocked |
| `isFollowup` | `boolean` | Whether this is a follow-up to a prior turn |
| `followupType` | `FollowupType` | What kind of follow-up: selection, advisory, trace, domain_review |
| `confidence` | `number` | Classifier confidence (0-1) |
| `signals` | `string[]` | Diagnostic signals for trace/debug |

### Classification (`hermesIntentClassifier.ts`)

The `buildIntentFrame(raw)` function runs 6 detection stages in order:

1. **Safety disposition** — detects blocked/approval-required actions (publish, send, create Ray Review)
2. **Intent type** — classifies the high-level intent from regex patterns
3. **Domain** — maps intent + message to a business domain
4. **Target** — detects what the user is referring to (named offer, ranked item, session item)
5. **Action** — determines what the user wants done (review, improve, explain, draft)
6. **Follow-up** — detects if this is a follow-up and what kind

### Routing Integration (`hermesPriorityRouter.ts`)

The intent frame is passed to `routeHermesPriority` as an optional parameter. When present, the router checks intent frame signals *before* the keyword chain:

- `domain_review` + `business_opportunities` → routes to `explicit_domain_retrieval`
- `approval_action_draft` + named_offer target → routes to `approval_action_prepare`
- `advisory_followup` + active advisory continuity → routes to `advisory_followup`

These intent-frame routes are *additive* — they fire early when context is available, but the full keyword chain still handles all other cases.

### Pipeline Integration (`hermesBrainPipeline.ts`)

The pipeline builds the intent frame at the start of `handleHermesMessage`, passes it to the router, and uses it for post-route session handling:

- After `executeRoute`, the pipeline checks `intentFrame.intent + intentFrame.action` to route to session-based handlers (explain_score, improve, Ray Review draft)
- The intent frame is included in the `BrainPipelineResponse` for downstream consumers

---

## Target Resolution Behavior

The intent frame's `detectTarget` function resolves user references in this priority:

1. **Named offers with dollar amounts** — `$97 Credit & Funding Readiness Review` detected with 0.9 confidence
2. **Named offers without dollar amounts** — `Credit Readiness Review` detected with 0.85 confidence
3. **Ranked items** — `top`, `first`, `second`, `number 3` detected with rank and 0.8 confidence
4. **Active session items** — `it`, `that`, `this`, `that one` detected with 0.7 confidence
5. **Page/report context** — `this page`, `that report` detected based on domain with 0.6 confidence

Target resolution is a two-stage process:
- **Intent frame** detects the *type* and *label* of the reference (e.g., `ranked_item` with rank=1)
- **Session manager** (`resolveTargetFromSession`) resolves the reference against the active session's item list

This separation means the intent frame works without sessions (for routing), but full target resolution requires an active session.

---

## Tests Added

`tests/hermes_structural_refactor.test.ts` — 36 tests covering:

- **Intent Frame classification** (10 cases): greeting, trace, status, record lookup, domain review, approval draft, capability, page context, external info, safety dispositions, follow-up detection, named targets, ranked targets
- **Source Authority contract** (3 cases): business opportunities levels, clients levels, source labels
- **Advisor Session business opportunity review** (5 cases): session start, score explanation, improvement suggestions, Ray Review draft, session context continuity
- **Client source attribution** (1 case): no contradictory blocker on 0-row success
- **Trace/decision process routing** (2 cases): trace questions, "was that live or local"
- **Voice-ready response contract** (2 cases): system health voice output, business opportunity voice output
- **Preserved behaviors** (8 cases): approvals lookup, selection memory, specialist agents, page context, system health, research status, safety gate, Tesla Model 3 boundary

---

## Before/After Examples

### Before: "how can we improve it" after pulling up business opportunities

**Before:**
```
Route: fallback_clarification
Response: "I can answer generally, but I need to know what plan or idea you mean."
```

**After:**
```
Route: advisory_followup
Intent: advisory_followup | Action: improve
Response: "To strengthen the $97 Credit & Funding Readiness Review, we should: document the scoring rubric; capture supporting evidence per opportunity; validate against live pipeline data; test with five manual prospects..."
Session: active with currentFocus on $97 Credit & Funding Readiness Review
```

### Before: "create a Ray Review card for the $97 Credit & Funding Readiness Review"

**Before:**
```
Route: approval_action_prepare (via keyword match only)
Response: Generic approval draft text without named target resolution
```

**After:**
```
Route: approval_action_prepare (via intent frame named_offer detection)
Intent: approval_action_draft | Target: named_offer "$97 Credit & Funding Readiness Review"
Response: "Draft Ray Review request prepared for **$97 Credit & Funding Readiness Review**..."
Session: pendingDraftTarget set with label, domain, action
```

### Before: "why did it get that score" after session

**Before:**
```
Route: fallback_clarification
Response: "I can answer generally, but I need to know what plan or idea you mean."
```

**After:**
```
Route: advisory_followup
Intent: advisory_followup | Action: explain_score
Response: "The $97 Credit & Funding Readiness Review is ranked at position 1. The score is based on: lowest barrier to entry; clearest value proposition; natural gateway to upsell; easiest to deliver at scale..."
```

---

## Remaining Limitations

1. **Classifier is pattern-based** — novel phrasings produce `unknown` intent; an LLM-backed classifier could improve coverage
2. **Session scope is in-memory** — sessions are not persisted across server restarts; a database-backed session store would be needed for production durability
3. **Target resolution requires session context** — "it" and "that one" only resolve when a session with an active list exists; without a session, they produce `active_session_item` with no resolution
4. **The intent frame does not replace the keyword router** — it enhances it; both systems run for every message
5. **Voice-ready response is a structural extraction** — it does not rewrite for voice; a TTS-optimized rewrite layer would be needed for true voice output
