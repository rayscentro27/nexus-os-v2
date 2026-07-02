# Hermes Brain Production Polish Result

## Summary

Applied a targeted production polish patch that fixes 8 intent families and renderer contract gaps found in live testing without undoing the master refactor.

## 1. Root Causes Fixed

### 1.1 Casual/Common Conversation Expansion
**Root cause:** `isCasualCommonQuestion` was too narrow. Normal human-experience, preference, and sports knowledge prompts fell into Nexus fallback.

**Fix:** Broadened detection patterns to include:
- Sports/team knowledge questions (`do you know any of the football teams`)
- Preference follow-ups (`give me a preference`)
- Typo-tolerant phrases (`todayt`)
- Food/drink questions (`did you drink your coffee today`)
- "Do you like" questions (`do you like sports`)

### 1.2 Page/UI Awareness Contract
**Root cause:** Page context detection regex was too narrow. "What color is the page" and "what page are we on" fell into fallback.

**Fix:** Expanded page context regex to handle color questions, page identity questions, and added honest capability disclosure for visual/DOM access.

### 1.3 Specialist Agent Inventory Route
**Root cause:** No dedicated route for specialist agent inventory questions. Domain reasoning was confused with inventory/status lookup.

**Fix:** Added `specialist_agent_inventory` route with:
- Detection for `[domain] specialist agent` patterns
- Registry of known specialist domains
- Honest "not registered" status for unregistered specialists
- Clear distinction between Nexus context and live specialist agents

### 1.4 System Health Phrase Normalization
**Root cause:** Some natural variants (`what is nexus health`, `how healthy is nexus`) routed to process/report inventory instead of system_health.

**Fix:** Expanded system health detection to include all natural variants and normalized them to the system_health renderer.

### 1.5 Client Record Verification-State Fix
**Root cause:** When client_profiles read succeeded with 0 rows, the contract showed contradictory "not verified" blocker.

**Fix:** Updated `renderRecordContract` to:
- Omit blocker when read succeeds with 0 rows
- Label adjacent context separately from client records
- Use "partial" status when some tables succeed and others fail

### 1.6 External/Current Info Fallback
**Root cause:** Sports scores and current news questions fell into Nexus fallback.

**Fix:** Added `external_current_info` route with honest capability disclosure and entity clarification requests.

### 1.7 Provenance/Source Wording Improvement
**Root cause:** Casual answer provenance said "local Nexus context" for common knowledge.

**Fix:** Updated provenance labels:
- Casual/common answers → "common knowledge and local reasoning"
- Fallback answers → "unresolved routing fallback, not verified Nexus data"
- External info answers → "external information request — no live external lookup available"

## 2. Generalized Route/Contract Changes

All fixes are pattern-based and generalize beyond exact production prompts:
- Sports detection works for any sport/team/league
- Preference detection works for any category (car, food, music, movie)
- Specialist inventory works for any domain
- System health works for any natural phrasing
- Client records handle any table success/failure combination
- External info works for sports, news, weather, and market data

## 3. Files Changed

### Source Files
- `src/lib/hermesCommonConversation.ts` — Expanded casual detection and answer functions
- `src/lib/hermesPromptKind.ts` — Added specialist_agent_inventory and external_current_info prompt kinds
- `src/lib/hermesPriorityRouter.ts` — Added specialist_agent_inventory and external_current_info routes
- `src/lib/hermesBrainPipeline.ts` — Added handlers for new routes, fixed source labeling
- `src/lib/hermesOperationalContracts.ts` — Added specialist agent inventory contract, fixed client records contract
- `src/lib/hermesPageContextStatus.ts` — Enhanced page context answers with honest capability disclosure
- `src/lib/hermesTraceQuestionHandler.ts` — Fixed provenance labels

### Test Files
- `tests/hermes_production_polish.test.ts` — 29 new tests for all production polish fixes
- `tests/hermes_brain_pipeline.test.ts` — Updated casual source expectation

## 4. Before/After Prompt Examples

| Prompt | Before | After |
|--------|--------|-------|
| `do you know any of the football teams` | fallback_clarification | casual_common |
| `did you drink your coffee today` | fallback_clarification | casual_common |
| `did you drink your coffee todayt` | fallback_clarification | casual_common |
| `what is your favorite car` | fallback_clarification | casual_common |
| `give me a preference` | fallback_clarification | casual_common |
| `do you like sports` | fallback_clarification | casual_common |
| `can you see what is on this page` | fallback_clarification | page_context_status |
| `what color is the nexus admin page` | fallback_clarification | page_context_status |
| `what page are we on` | fallback_clarification | page_context_status |
| `do we have a credit specialist agent` | local_reasoning | specialist_agent_inventory |
| `do we have a funding specialist agent` | local_reasoning | specialist_agent_inventory |
| `do we have research specialist` | local_reasoning | specialist_agent_inventory |
| `what is our system health` | degraded | system_health_report |
| `what was the score on the soccer game last night` | fallback_clarification | external_current_info |

## 5. Tests Added

### Exact Prompt Tests (14)
- All required exact prompts from the production polish spec

### Variant Tests (10)
- `is there a grant specialist agent`
- `who handles credit repair`
- `is the research specialist live`
- `what is nexus health`
- `how healthy is nexus`
- `is nexus healthy`
- `do you drink coffee`
- `what teams do you know`
- `what is your preferred car`
- `what page am I viewing`

### Banned Phrase Checks
All prompts verified to not contain:
- "I need one more detail: what specific outcome or record do you want help with?"
- "I can reason from the allowed"
- "I need a concrete decision"

## 6. Tests Run

- Focused production polish tests: 29/29 passed
- Full test suite: 657/657 passed
- Production build: passed

## 7. Build Result

✅ TypeScript compilation: passed
✅ Vite build: passed
✅ All 657 tests: passed

## 8. Safety Confirmation

- No schedulers activated
- No content published
- No emails sent
- No customers charged
- No destructive database writes
- No approvals bypassed
- No secrets exposed
- No paid APIs run

## 9. Remaining Limitations

- External info queries cannot provide real-time data (no live sports/news/weather feeds)
- Specialist agent registry is build-time; live agents require Supabase or config updates
- Page context requires UI to pass metadata; visual/DOM inspection not available from chat

## 10. Next Action

Commit and push the production polish patch.
