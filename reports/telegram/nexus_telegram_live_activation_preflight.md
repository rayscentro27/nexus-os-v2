# Nexus Telegram Live Activation — Preflight

**Generated**: 2026-07-05
**Phase**: A

## Environment

| Field | Value |
|-------|-------|
| Current Commit | 6fe1252 |
| Branch | main |
| Repo | ~/nexus-os-v2 |

## Token Status

| Field | Value |
|-------|-------|
| TELEGRAM_BOT_TOKEN | present, length=46, preview=893561...hXjw |
| TELEGRAM_ADMIN_CHAT_ID | present, value=[8935612290] (BOT_ID - WRONG) |
| TELEGRAM_ALLOWED_CHAT_IDS | present, value=[8935612290,8730287596] |
| TELEGRAM_MODE | present, value=[TELEGRAM_OPERATOR] |
| TELEGRAM_GROUP_CHAT_ID | NOT SET |

## Warning

TOKEN_ROTATION_REQUIRED — The token was exposed during setup. After verification, Ray must revoke and replace both tokens.

## Preflight Status

READY_FOR_ACTIVATION — token present, env vars loaded, curl-only approach confirmed.
