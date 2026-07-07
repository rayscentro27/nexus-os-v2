# Active Context Data Wiring Test Results — 2026-07-07

## Unit Tests (26/26 PASS)

| Test | Status |
|------|--------|
| clean_html: bold tags | PASS |
| clean_html: mixed tags + entities | PASS |
| top_index computed as 2 (highest score) | PASS |
| item 2 title preserved | PASS |
| item 2 score preserved (6.3) | PASS |
| select_context_item: number 2 | PASS |
| select_context_item: this (top) | PASS |
| detect_followup_intent: number 2 | PASS |
| detect_followup_intent: why number 2 | PASS |
| detect_followup_intent: research deeper | PASS |
| detect_followup_intent: turn number 2 into work order | PASS |
| format_score_explanation: has title | PASS |
| format_score_explanation: has score 6.3/10 | PASS |
| format_score_explanation: no HTML tags | PASS |
| format_best_option_explanation: has title | PASS |
| format_best_option_explanation: no placeholder A | PASS |
| format_deeper_research: has topic | PASS |
| save_pending_action: saved | PASS |
| handle_confirm_pending: has topic | PASS |
| handle_confirm_pending: pending cleared | PASS |
| format_work_order_draft: has title | PASS |
| format_work_order_draft: no placeholder A | PASS |
| Alpha context: 3 items | PASS |
| Alpha item 2: Offer free 15-min readiness calls | PASS |
| Alpha explain: has title | PASS |
| Alpha work order: has title | PASS |

## Bridge Integration Tests (12/12 PASS)

| Test | Status |
|------|--------|
| classify_message_intent: number 2 → ACTIVE_CONTEXT_FOLLOWUP | PASS |
| classify_message_intent: this → ACTIVE_CONTEXT_FOLLOWUP | PASS |
| classify_message_intent: confirm → ACTIVE_CONTEXT_FOLLOWUP | PASS |
| classify_message_intent: yes → ACTIVE_CONTEXT_FOLLOWUP | PASS |
| classify_message_intent: research deeper → ACTIVE_CONTEXT_FOLLOWUP | PASS |
| classify_message_intent: turn this into a work order → ACTIVE_CONTEXT_FOLLOWUP | PASS |
| classify_message_intent: compare 1 and 2 → ACTIVE_CONTEXT_FOLLOWUP | PASS |
| classify_message_intent: good morning → GREETING | PASS |
| classify_message_intent: hermes what... → HERMES_ADVISORY | PASS |
| classify_message_intent: what time is it → TEMPORAL_INTENT | PASS |
| process_command: /status → contains "Processes:" | PASS |
| process_command: /report → contains "Score:" | PASS |

## Build

- tsc --noEmit: PASS
- vite build: PASS (16.10s)

## Safety Scan

- No .env staged
- No API keys in changed files
- No Supabase service role key
- No Stripe secret
- No Telegram token
- No Brave/Resend/Netlify keys
- No git add . or git add -A
