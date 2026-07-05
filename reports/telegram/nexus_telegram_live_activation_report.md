# Nexus Telegram — Live Activation Report

**Generated**: 2026-07-05
**Starting Commit**: 658b1ec
**Ending Commit**: 6fe1252

---

## Summary

| Field | Value |
|-------|-------|
| Token Status | VALID, ROTATION_REQUIRED |
| Bot Username | NexusHermes27bot |
| Bot ID | 8935612290 |
| Real Private Chat ID | 1288928049 |
| Bot ID Mistaken as Chat ID | Yes, corrected via getUpdates |
| Group Chat | None found |
| Private Outbound | PASS |
| Command Tests | 15/15 PASS |
| Bridge Dry-Run | PASS |
| Bridge --once | PASS (bounded exit) |
| Active Runner --once | PASS (17 processes, 17 receipts) |
| Daily Monitor | PASS |
| Recovery Check | PASS |
| Bot Menu | 17 commands registered |
| Telegram Final Status | TELEGRAM_OPERATOR_ACTIVE_ROTATION_REQUIRED |
| Active OS Score | 76 → 83 |

---

## Phases Completed

| Phase | Status | Notes |
|-------|--------|-------|
| A: Preflight | PASS | Token present, env loaded |
| B: Token Check | PASS | getMe ok=true, bot verified |
| C: Chat ID Resolution | PASS | Real chat ID 1288928049 resolved from getUpdates |
| D: Outbound Test | PASS | Message sent to private chat |
| E: Bot Menu | PASS | 17 commands registered |
| F: Bridge Verification | PASS | 15/15 commands pass |
| G: Bridge Once | PASS | Bounded exit |
| H: Active Runner | PASS | 17 processes, 17 receipts |
| I: Status Update | PASS | Scorecard and registry updated |
| J: Rotation Instructions | PASS | Full instructions created |
| K: Build + Safety | PASS | Build passes, no secrets committed |
| L: Commit + Push | PASS | Pushed to origin/main |

---

## Receipts Created

| Receipt | Path |
|---------|------|
| getMe | reports/telegram/receipts/live_activation/telegram_getme_latest.json |
| Chat ID Resolution | reports/telegram/receipts/live_activation/telegram_chat_id_resolution_latest.json |
| Private Outbound | reports/telegram/receipts/live_activation/telegram_private_outbound_latest.json |
| Set Commands | reports/telegram/receipts/live_activation/telegram_set_commands_latest.json |
| Bridge Verification | reports/telegram/receipts/live_activation/nexus_bridge_command_verification_latest.json |
| Bridge Once | reports/telegram/receipts/live_activation/telegram_bridge_once_latest.json |

---

## Token Rotation Requirement

The current token was exposed during setup. After this activation is verified, Ray must:

1. Revoke exposed token in BotFather
2. Generate fresh token
3. Set new env vars
4. Verify with curl getMe + bridge --dry-run + bridge --once
5. Confirm Telegram message arrives

See: reports/telegram/nexus_telegram_token_rotation_required.md
