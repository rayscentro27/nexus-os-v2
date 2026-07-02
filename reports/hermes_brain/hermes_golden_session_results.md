# Hermes Golden Session Results

**Date:** 2026-07-02
**Status:** All 693 tests passing across 26 test files

---

## Test Suite Summary

| Test File | Tests | Status |
|---|---|---|
| `hermes_structural_refactor.test.ts` | 36 | ✅ All passing |
| `hermes_master_contracts.test.ts` | 20 | ✅ All passing |
| `hermes_production_polish.test.ts` | 29 | ✅ All passing |
| `hermes_brain_pipeline.test.ts` | 34 | ✅ All passing |
| `hermes_conversational_routing_gaps.test.ts` | 20 | ✅ All passing |
| `hermes_topic_boundary.test.ts` | 43 | ✅ All passing |
| `hermes_advisory_continuity_product_routing.test.ts` | 22 | ✅ All passing |
| `hermes_intent_router.test.ts` | 64 | ✅ All passing |
| `hermes_section_status.test.ts` | 111 | ✅ All passing |
| `hermes_model_routing.test.ts` | 40 | ✅ All passing |
| Other test files (16) | 274 | ✅ All passing |
| **Total** | **693** | **✅ All passing** |

---

## Structural Refactor Test Coverage

### Intent Frame Classification (10 cases)
- `good morning` → greeting / general_conversation
- `where did you get that answer from` → trace_question / trace
- `how is the system health` → status_question / system_health
- `do i have any approvals that are pending` → record_lookup / approvals
- `do we have any clients` → record_lookup / clients
- `pull up the business opportunity report` → domain_review / business_opportunities
- `create a Ray Review card for that` → approval_action_draft / approvals
- `what can you do` → brain_capability_status / general_conversation
- `can you see what is on this page` → page_context / current_page
- `what was the score on the soccer game last night` → external_current_info / external_info

### Safety Disposition (2 cases)
- `publish the report now` → blocked
- `create a Ray Review card for that` → approval_required

### Follow-up and Target Detection (3 cases)
- `how can we improve it` → isFollowup = true
- `create a Ray Review card for the $97 Credit & Funding Readiness Review` → named_offer with label containing "$97"
- `what is the top business opportunity` → ranked_item with rank = 1

### Source Authority Contract (3 cases)
- Business opportunities domain has `live_supabase` and `static_context` in levels
- Clients domain has `live_supabase` but NOT `static_context`
- Source label for `live_supabase` contains "live Supabase"

### Advisor Session Business Opportunity Review (5 cases)
- Pull up report starts session with activeMode = business_opportunity_review, activeList with items, voiceReady
- "why did it get that score" after session → action = explain_score, response contains "score"
- "how can we improve it" after session → action = improve, response matches /improve|strengthen|enhance/
- Named Ray Review draft → response contains "$97 Credit & Funding Readiness Review" and "not been saved"
- "how can we improve it" after session → no fallback clarification

### Client Source Attribution (1 case)
- `do we have any clients` → route = client_records, source mentions client_profiles, no "not verified" blocker

### Trace/Decision Process (2 cases)
- `what part of your decision process did you use` → route = trace_source_meta
- `was that live or local` → route = trace_source_meta

### Voice-Ready Response (2 cases)
- System health → voiceReady.plainAnswer length > 20
- Business opportunity review → voiceReady.plainAnswer non-empty

### Preserved Behaviors (8 cases)
- Live approvals Supabase lookup
- Selection memory for number references
- Specialist agent inventory
- Page context route
- System health route
- Research status route
- Safety gate
- Tesla Model 3 as new-topic boundary

---

## Before/After Behavioral Changes

### Advisory Follow-up Routing

| Message | Before | After |
|---|---|---|
| "how can we improve it" (no session) | fallback_clarification | fallback_clarification (unchanged) |
| "how can we improve it" (with session) | fallback_clarification | advisory_followup → improvement suggestion |
| "why did it get that score" (with session) | fallback_clarification | advisory_followup → score explanation |
| "what should we monetize first" (no session) | local_reasoning | local_reasoning (unchanged) |

### Named Target Routing

| Message | Before | After |
|---|---|---|
| "create a Ray Review card for the $97 Credit & Funding Readiness Review" | approval_action_prepare (generic) | approval_action_prepare (with named_offer target) |
| "create a Ray Review card for that" (with session) | approval_action_prepare | approval_action_prepare (with session item resolution) |

### Safety Gate

| Message | Before | After |
|---|---|---|
| "Send an email to all clients" | fallback_clarification (missed safety) | safety_gate (caught by fixed risky regex) |

### Trace Question Priority

| Message | Before | After |
|---|---|---|
| "why did you use local fallback" | source (generic) | source_reason (specific) |
| "was that live or local" | source (generic) | source (unchanged) |

---

## Safety Confirmation

### No Scheduler Activation
- No test or code path activates any scheduler
- All scheduling routes produce `approval_required` action policy
- No `cron`, `setInterval`, or scheduler API calls exist in the new code

### No Publishing
- `publish` is in the blocked safety list; "publish the report now" routes to safety_gate
- No content publishing, social media posting, or email sending exists

### No Email Sends
- "Send an email to all clients" routes to safety_gate
- No email API calls or SMTP configuration exists in the new code

### No Charges
- No payment processing, Stripe, or billing API calls exist in the new code
- No financial transaction code exists in the new modules

### No Destructive DB Writes
- All Supabase interactions are read-only (SELECT queries)
- No INSERT, UPDATE, DELETE, or TRUNCATE operations exist in the new code
- No schema migrations or table modifications exist

### No Approval Bypass
- All draft actions route with `actionPolicy: 'approval_required'`
- Ray Review drafts are conversation-only; they are not saved or submitted
- No code path bypasses the approval gate

### No Secrets Exposed
- No API keys, tokens, or credentials are hardcoded in the new modules
- All external configuration comes from environment variables
- No secrets appear in test files or documentation

### No Paid API Execution
- No OpenAI, Anthropic, or other paid LLM API calls exist in the new modules
- The `modelPolicy: 'forbidden'` is set for all intent-frame routes
- No `fetch` calls to external paid services exist

### No Production Data Mutation
- All new modules are read-only or session-state-only
- Session state is in-memory (Map); no database writes
- No file system writes exist in the new modules

---

## Remaining Limitations

1. **In-memory sessions** — not persisted across server restarts
2. **Pattern-based classifier** — novel phrasings produce `unknown` intent
3. **Static opportunity data** — hardcoded list, not live Supabase query
4. **No TTS optimization** — voice-ready extracts but does not rewrite for speech
5. **English-only** — all patterns and extraction are English-only
6. **No concurrent session limit** — unlimited sessions per scope key
7. **Turn-based expiry** — not time-based; rapid messages expire faster
