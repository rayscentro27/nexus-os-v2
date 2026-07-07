# Router Regression Audit — 2026-07-07

## Starting Commit
`de860b9` — refactor telegram router with draft first gated research

## Root Causes Identified

### 1. "what time is it" misses temporal handler
**File**: `scripts/telegram/nexus_telegram_bridge.py` (process_with_new_router)
**Root Cause**: `format_time_response(understanding)` was passed the `understanding` dict from `message_understanding.py`, which has `intent_family: "temporal"`. But `format_time_response` expects a `detect_temporal_intent` result with `intent: "CURRENT_TIME"`. Since the understanding dict has no `intent` key matching the expected values, it fell through to the default: `"I understand the timeframe but need more context."`.
**Fix**: Call `detect_temporal_intent(full_text.lower().strip())` directly and pass its result to `format_time_response`.

### 2. Alpha Money Moves context overwritten by "Clarify the question"
**File**: `scripts/telegram/nexus_telegram_bridge.py` (_route_to_draft_engine)
**Root Cause**: Active context was saved for ALL intents including `help`, `greeting`, `unknown`, and `fallback`. When "confirm" without a pending action was classified as `help`, it went through the draft engine which generated "Clarify the question" as a placeholder item. This was saved as active context, overwriting the real Alpha Money Moves context.
**Fix**: Added `SAVEABLE_INTENTS` guard — only save active context for actionable intents (money_plan, client_acquisition, business_strategy, opinion, critique, web_research, etc.).

### 3. "confirm" without pending action becomes Hermes guidance
**File**: `scripts/telegram/message_understanding.py` (understand_message)
**Root Cause**: When `_is_confirm` matched but no `pending_action` existed, the intent was set to `"help"`. This routed through the draft engine which generated generic Hermes guidance. The help response was then saved as active context.
**Fix**: Return `intent_family: "pending_action"` even without a pending action, so the router can give a context-aware "no pending action" message. Added explicit handler in `process_with_new_router` for this case.

### 4. "Clarify the question" overwrote active context
**File**: `scripts/telegram/nexus_telegram_bridge.py` (_route_to_draft_engine)
**Root Cause**: The draft engine generates placeholder items for help/greeting intents (e.g., "Clarify the question"). These were saved as active context, replacing real items.
**Fix**: SAVEABLE_INTENTS guard prevents saving context for non-actionable intents.

### 5. "why is number 2 scored that way?" could not find item
**File**: `scripts/telegram/nexus_telegram_bridge.py` (classify_message_intent)
**Root Cause**: The old classifier checked `ACTIVE_CONTEXT_FOLLOWUP` BEFORE `TEMPORAL_INTENT`. The `_detect_followup` function matched "2" in "what time is it" as a number reference, returning `select_item` before temporal could run. This also meant that after "confirm" overwrote context, numbered lookups found "Clarify the question" instead of real items.
**Fix**: Moved `TEMPORAL_INTENT` check before `ACTIVE_CONTEXT_FOLLOWUP` in old classifier. SAVEABLE_INTENTS guard prevents garbage from being saved.

### 6. "turn number 2 into a work order" created from fallback context
**File**: `scripts/telegram/message_understanding.py` (_detect_followup)
**Root Cause**: `_detect_followup` checked number patterns BEFORE work order patterns. "turn number 2 into a work order" matched `select_item` (because of "number 2") instead of `create_work_order`. This routed to `format_score_explanation` instead of `format_work_order_draft`.
**Fix**: Reordered `_detect_followup` to check work order, research deeper, and explain patterns BEFORE number selection.

### 7. "alpha can you do deeper research on this" used raw phrase as topic
**File**: `scripts/telegram/nexus_telegram_bridge.py` (_handle_active_context_followup)
**Root Cause**: When "deeper research on this" was detected as `research_deeper`, the topic was set to the raw message text instead of resolving "this" from active context.
**Fix**: In `research_deeper` handler, use `active_context["topic"]` as the topic. Added implicit context follow-up layer in router for "deeper research on this" patterns.

### 8. "research deeper" used "confirm" as topic
**File**: `scripts/telegram/nexus_telegram_bridge.py` (classify_message_intent)
**Root Cause**: After "confirm" overwrote active context with "Clarify the question", subsequent "research deeper" used that as the topic.
**Fix**: SAVEABLE_INTENTS guard + confirm_no_pending handler prevents garbage context.

## Files Changed

| File | Changes |
|------|---------|
| `scripts/telegram/nexus_telegram_bridge.py` | Temporal routing fix, confirm_no_pending handler, SAVEABLE_INTENTS guard, research_deeper topic resolution, implicit context follow-up layer, work order from active context, old classifier temporal priority, cmd_followup active context priority |
| `scripts/telegram/message_understanding.py` | Confirm without pending returns pending_action intent, _detect_followup reordered (work order/research/explain before number selection) |

## Verification

All 10 regression test commands pass:
1. Hermes Money Plan — generates 5 real GoClear items
2. Alpha Money Opinion — generates 3 real Alpha Outside Opinion items
3. Deeper research on this — resolves "this" to active context topic
4. Confirm — executes pending action
5. Why is number 2 scored — explains real item #2 (7.5/10)
6. Turn number 2 into work order — creates work order from real item #2
7. Research deeper — resolves topic from active context
8. Confirm — executes pending action
9. What time is it — returns "Ray, it is X in Phoenix"
10. /report — returns full system report
