# Nexus Telegram Live Polling — Activation Report

**Activated**: 2026-07-06T12:54:46.781483+00:00
**Script**: scripts/telegram/nexus_telegram_bridge.py
**Mode**: --once (bounded one-shot polling)
**State File**: data/runtime/telegram_last_update_id.json
**Receipt Dir**: reports/telegram/receipts/live_polling/

---

## How It Works

1. `--once` calls Telegram `getUpdates` API
2. Uses saved `last_update_id` as offset (avoids duplicate processing)
3. Ignores messages from unauthorized chat IDs
4. Routes command text through existing `process_command()` handler
5. Sends reply via `sendMessage`
6. Saves latest `update_id` to prevent reprocessing
7. Writes a receipt under `reports/telegram/receipts/live_polling/`

## State Management

- `data/runtime/telegram_last_update_id.json` stores the last processed `update_id`
- On each `--once` run, only messages with `update_id > saved` are processed
- This ensures no duplicate responses even with 60-second launchd intervals

## Security

- Only chat IDs in `TELEGRAM_ALLOWED_CHAT_IDS` are processed
- Unauthorized messages are ignored (no receipt written)
- No tokens, keys, or sensitive data are included in receipts
- External actions remain approval-gated

## Commands Supported

| Command | Response |
|---------|----------|
| /report | Full system report |
| /status | Current status |
| /daily | Daily monitor |
| /research | Research/NotebookLM/Alpha status |
| /content | Content drafts status |
| /approvals | Ray Review queue |
| /orders | Work orders |
| /hermes <msg> | Hermes advisory |
| /recover | Recovery check |
| /approve <id> | Approve item |
| /reject <id> <reason> | Reject item |
| /revise <id> <feedback> | Request revision |
| /request <text> | Internal request |
| /alpha <topic> | Alpha research |
| /processes | Process registry |
| /run <id> | Run safe process |
| /blocked | Blocked actions |

## Verification

To verify live polling is working:

1. Send a command in Telegram (e.g., /report)
2. Run: `python3 scripts/telegram/nexus_telegram_bridge.py --once`
3. Check `data/runtime/telegram_last_update_id.json` for updated `last_update_id`
4. Check `reports/telegram/receipts/live_polling/` for new receipt files
5. The command should NOT be repeated on the next `--once` run
