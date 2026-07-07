# Active Context Data Wiring Audit — 2026-07-07

## Root Cause

Placeholder A/B/test values appeared in Telegram follow-up responses because:

1. **Hermes web search context save** used `advisory.get("results", [])` — a key that doesn't exist in the advisory dict. The actual key is `advisory.get("findings", [])`. This meant the context save silently produced empty items, and the test data (A/B) from development leaked into production.

2. **Alpha research context save** created a SINGLE item with `title=(extra or "research")[:80]` and the whole response as summary. It did not parse the individual ranked recommendations from the score record. So "number 2" after Alpha research returned "I could not find that item" because only index 1 existed.

3. **`top_index` hardcoded to 1** instead of being computed from the highest-scored item. This meant "why is that the best option" always explained item 1.

4. **No pending action system** for "research deeper" → "confirm" flow. The "confirm" word fell through to generic fallback.

5. **HTML tags** from Brave search snippets appeared in Telegram display and context summaries (e.g., `<strong>myFICO</strong>`).

## Files Changed

| File | Change |
|------|--------|
| `scripts/telegram/active_context.py` | Rewritten: added `clean_html`, `compute_top_index`, `save_pending_action`, `load_pending_action`, `clear_pending_action`, `handle_confirm_pending`. Fixed `format_score_explanation` with real item format. Fixed `format_best_option_explanation` to handle non-top items. Fixed `format_work_order_draft` with meaningful titles. Fixed `format_deeper_research` to save pending action. |
| `scripts/telegram/nexus_telegram_bridge.py` | Fixed Hermes context save to use `advisory.get("findings", [])` with individual finding scores. Fixed Alpha context save to load score record and parse individual recommendations. Added confirm/yes/go ahead routing. Added `compute_top_index` and `clean_html` imports. Added HTML cleaning to Hermes display. |
| `reports/telegram/active_context_data_wiring_audit_latest.md` | This file |
| `reports/telegram/active_context_data_wiring_test_results_latest.md` | Test results |

## What Was Wrong

### Hermes Web Search
- **Before**: `advisory.get("results", [])` — key doesn't exist, items always empty
- **After**: `advisory.get("findings", [])` — correct key, each finding has individual score

### Alpha Research
- **Before**: Single item with `title=topic[:80]`, `score=6` (hardcoded)
- **After**: Loads score record, creates item per recommendation with actual scores

### top_index
- **Before**: Always 1
- **After**: `compute_top_index(items)` — index of highest-scored item

### Score Explanation
- **Before**: Generic "Why it scored well" with no context
- **After**: "Why it scored this way:" with positive/weakness breakdown, next step

### Best Option Explanation
- **Before**: Always "the highest among N options" even for non-top items
- **After**: "the top recommendation" for top items, "stands out" for non-top items

### Work Order Draft
- **Before**: `title=f"Hermes: {topic[:80]}"` — generic
- **After**: `title=f"Review {item_title[:60]} for GoClear"` — specific to selected item

### Research Deeper + Confirm
- **Before**: "confirm" fell through to generic fallback
- **After**: Saves pending action, "confirm" loads and processes it

### HTML Cleaning
- **Before**: Raw `<strong>`, `<em>`, `&amp;` in Telegram display
- **After**: `clean_html()` strips tags and decodes entities
