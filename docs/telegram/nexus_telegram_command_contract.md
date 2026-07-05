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
| `/lanes` | Show approval-gated lanes | No |
| `/blocked` | Show approval-gated actions | No |

## Response Format

All responses are plain text, suitable for Telegram messaging.

## Approval-Gated Commands

Commands that trigger approval-gated actions return:
```
APPROVAL_GATED: This action requires Ray approval before execution.
Lane: [lane name]
Status: [status]
Use /approve [id] to approve, /reject [id] to reject, /revise [id] for feedback.
```

## Unknown Commands

Return the help text from `/start`.
