# Nexus Telegram — launchd Rotation Status

**Generated**: 2026-07-05
**Phase**: F

## Status: READY_BUT_TOKEN_ROTATION_REQUIRED

## Current Telegram Plist

| Field | Value |
|-------|-------|
| Label | com.raymonddavis.nexus.telegram |
| Location | ~/Library/LaunchAgents/com.raymonddavis.nexus.telegram.plist |
| Loaded | NO (not loaded by this activation) |
| Contains Secrets | YES — bot tokens, OpenRouter key, Hermes gateway key |
| Safe to Load | NO — secrets must be rotated first |
| Classification | UNSAFE_SECRETS_EXPOSED |

## Secrets Found in Plist

- NEXUS_ONE_BOT_TOKEN (old bot)
- TELEGRAM_INBOUND_BOT_TOKEN
- TELEGRAM_OPS_BOT_TOKEN
- TELEGRAM_REPORTS_BOT_TOKEN
- OPENROUTER_API_KEY
- HERMES_GATEWAY_KEY

## What Ray Must Do After Token Rotation

```bash
# 1. Revoke old token in BotFather
# 2. Generate fresh token
# 3. Update plist EnvironmentVariables with new token
# 4. Load the plist:
launchctl load ~/Library/LaunchAgents/com.raymonddavis.nexus.telegram.plist

# 5. Verify:
launchctl list | grep telegram
```

## Telegram Operator Status

| Field | Value |
|-------|-------|
| Token | ROTATION_REQUIRED |
| Bot | NexusHermes27bot |
| Private Chat ID | 1288928049 |
| Bridge | VERIFIED (dry-run + once) |
| Commands | 15/15 PASS |
| launchd | NOT_LOADED (secrets in plist) |
