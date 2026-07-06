# Nexus Telegram — Away Mode Status

**Generated**: 2026-07-05
**Phase**: E

## Status: TELEGRAM_READY_BUT_TOKEN_ROTATION_REQUIRED

## Current State

| Field | Value |
|-------|-------|
| Token | ROTATION_REQUIRED (exposed during setup) |
| Bot | NexusHermes27bot |
| Private Chat ID | 1288928049 |
| Bridge | VERIFIED (dry-run + once) |
| Commands | 15/15 PASS |
| launchd | NOT_LOADED (secrets in plist) |

## What Ray Must Do After Returning

```bash
# 1. Revoke old token in BotFather
# 2. Generate fresh token
# 3. Export new token:
export TELEGRAM_BOT_TOKEN="NEW_TOKEN"
export TELEGRAM_ADMIN_CHAT_ID="1288928049"
export TELEGRAM_ALLOWED_CHAT_IDS="1288928049"
export TELEGRAM_MODE="TELEGRAM_OPERATOR"

# 4. Verify:
curl -sS "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe"
python3 scripts/telegram/nexus_telegram_bridge.py --dry-run
python3 scripts/telegram/nexus_telegram_bridge.py --once

# 5. Load Telegram launchd:
launchctl load ~/Library/LaunchAgents/com.raymonddavis.nexus.telegram.plist
```

## While Ray Is Away

- Telegram bridge is NOT running (no fresh token)
- All other Nexus systems continue running via launchd
- No Telegram commands available until token rotation
- All approval-gated workflows wait for Ray's return
