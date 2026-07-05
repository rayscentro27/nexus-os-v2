# Nexus Telegram — Command Contract

**Generated**: 2026-07-05

---

## Commands

| Command | Description | Receipt |
|---------|-------------|---------|
| `/start` | Show help text | No |
| `/help` | Show help text | No |
| `/status` | System status summary | No |
| `/daily` | Daily monitor summary | No |
| `/health` | System health summary | No |
| `/review` | Ray Review queue | No |
| `/approve <id>` | Approve item | Yes |
| `/reject <id> <reason>` | Reject item | Yes |
| `/revise <id> <feedback>` | Request revision | Yes |
| `/request <text>` | Internal work request | Yes |
| `/hermes <message>` | Hermes advisory request | Yes |
| `/alpha <topic-or-url>` | Alpha research intake | Yes |
| `/orders` | Show work orders | No |
| `/recover` | Run recovery check | Yes |
| `/processes` | Show process registry | No |
| `/run <process-id>` | Trigger safe process | Yes |
| `/blocked` | Show blocked actions | No |

## Response Format

All responses are plain text, suitable for Telegram messaging.

## Blocked Commands

Commands that trigger blocked actions return:
```
BLOCKED: This action requires an approved runner and compliance review. Cannot execute from Telegram.
```

## Unknown Commands

Return the help text from `/start`.
