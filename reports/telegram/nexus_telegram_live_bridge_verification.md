# Nexus Telegram Live Bridge Verification

**Generated**: 2026-07-05
**Phase**: F + G

## Token Check

| Field | Value |
|-------|-------|
| Bot ID | 8935612290 |
| Bot Username | NexusHermes27bot |
| Bot First Name | Nexus Hermes |
| Token Length | 46 |
| Token Preview | 893561...hXjw |
| Token Valid | YES |
| Rotation Required | YES |

## Chat ID Resolution

| Field | Value |
|-------|-------|
| Method | getUpdates via curl |
| Real Private Chat ID | 1288928049 |
| User | Ray Davis (@rayscentro) |
| Bot ID Mistakenly Used | YES (8935612290) |
| Group Chat | None found |

## Command Tests (15/15 PASS)

| Command | Status | Notes |
|---------|--------|-------|
| /status | PASS | |
| /daily | PASS | |
| /health | PASS | |
| /review | PASS | |
| /approve TEST-001 | PASS | receipt: tg_approval_20260705T222026Z |
| /reject TEST-001 | PASS | receipt: tg_approval_20260705T222027Z |
| /revise TEST-001 | PASS | receipt: tg_approval_20260705T222027Z |
| /request | PASS | work_order: wo_20260705T222025 |
| /hermes | PASS | work_order: wo_20260705T222025 |
| /alpha | PASS | work_order: wo_20260705T222025 |
| /orders | PASS | |
| /recover | PASS | |
| /processes | PASS | |
| /blocked | PASS | |
| /help | PASS | |

## Bridge Modes

| Mode | Status | Notes |
|------|--------|-------|
| --dry-run | PASS | All commands render |
| --test-command | PASS | Individual commands work |
| --once | PASS | Bounded exit, no daemon |

## Outbound Test

| Target | Status | Message ID |
|--------|--------|------------|
| Private (1288928049) | PASS | 4 |

## Bot Menu

17 commands registered via setMyCommands.

## Conclusion

Telegram bridge is fully verified. Token valid, chat resolved, commands work, outbound works. Rotation required.
