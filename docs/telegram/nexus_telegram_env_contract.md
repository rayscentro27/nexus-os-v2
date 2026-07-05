# Nexus Telegram — Environment Contract

**Generated**: 2026-07-05

---

## Required Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `TELEGRAM_BOT_TOKEN` | YES | Bot authentication token from @BotFather |
| `TELEGRAM_ADMIN_CHAT_ID` | YES | Ray's Telegram chat ID for admin commands |

## Optional Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `TELEGRAM_ALLOWED_CHAT_IDS` | RECOMMENDED | Comma-separated list of allowed chat IDs |
| `TELEGRAM_MODE` | OPTIONAL | `polling` or `webhook` (default: polling) |
| `TELEGRAM_WEBHOOK_URL` | OPTIONAL | Webhook URL for production |
| `TELEGRAM_ENABLE_POLLING` | OPTIONAL | `true` to enable polling |
| `TELEGRAM_DRY_RUN` | OPTIONAL | `true` to run in dry-run mode |

## Classification

- If `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ADMIN_CHAT_ID` present: **TELEGRAM_OPERATOR_READY**
- If only `TELEGRAM_BOT_TOKEN` present: **TELEGRAM_PARTIAL_READY**
- If neither present: **TELEGRAM_ENV_MISSING_OPERATOR_READY** (bridge still works in mock/test mode)

## Security Rules

- Never print token values in logs or reports
- Never commit `.env` files
- Token is masked in all receipts and reports
- Chat IDs are validated against allowed list
- No service role usage from Telegram
- No sensitive client data in messages
