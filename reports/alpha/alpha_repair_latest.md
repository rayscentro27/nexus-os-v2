# Alpha Repair Report

**Date**: 2026-07-06

---

## What Was Fixed

### 1. Natural Language Alpha Routing
- Added `detect_alpha_intent()` to identify Alpha-related plain-language messages
- Patterns: "alpha", "research", "look into", "is this worth", "score this", "compare", "pros and cons"
- Messages starting with these patterns route to `cmd_alpha_fallback()`

### 2. Alpha Fallback Handler
- Added `cmd_alpha_fallback(topic, source)` that:
  - Classifies topic into category (client_acquisition, grant_opportunity, social_media, trading, etc.)
  - Generates 3-5 deterministic ideas based on category
  - Scores each idea on 5 dimensions (speed, cost, difficulty, risk, relevance)
  - Writes intake record to `data/alpha/intake/`
  - Writes brief to `reports/alpha/briefs/`
  - Writes score to `reports/alpha/scores/`
  - Updates Hermes advisory feed at `reports/hermes/alpha_advisory_feed_latest.md`
  - Saves conversation context for follow-ups
  - Returns concise Telegram reply with top 3 recommendations

### 3. Conversation Context
- Created `data/runtime/telegram_conversation_context.json`
- Stores per-chat: last_agent, last_topic, last_alpha_brief_path, last_alpha_score_path, last_alpha_recommendations, last_selected_item, last_work_order_path
- Updated after each Alpha interaction

### 4. Follow-up Handler
- Added `cmd_followup(intent, match, chat_id)` that handles:
  - "what did Alpha find?" — summarizes latest brief
  - "which one should we do first?" — shows top recommendation
  - "turn number N into a work order" — creates work order from recommendation
  - "send that to Hermes" — routes brief to Hermes

### 5. Updated /research
- Now includes Alpha section: latest topic, brief path, score path, top recommendation, work order

### 6. Updated /report
- Now includes Alpha section: latest topic, top recommendation, whether Ray needs to approve

### 7. Debug Receipts
- Alpha routing attempts write receipts to `reports/telegram/receipts/alpha_debug/`
- Includes: timestamp, source, raw_text (safe), detected_intent, routed_to, handler_called, reply_length

## What Was NOT Changed

- `/report`, `/status`, `/research`, `/content`, `/approvals`, `/hermes`, `/approve`, `/reject`, `/revise` — all unchanged
- Live polling — unchanged
- Duplicate prevention — unchanged
- Authorization filtering — unchanged
- Telegram API layer — unchanged

## Security

- No tokens committed
- No PII in receipts
- External actions remain approval-gated
- Only chat ID 1288928049 is authorized
