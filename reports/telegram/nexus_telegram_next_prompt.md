# Next Telegram Prompt (Copyable)

**Generated:** 2026-07-05  
**Status:** Ready to Execute

---

## Complete Prompt for Connecting Telegram to Nexus Hermes and Alpha

Copy the prompt below and paste it into your next session to begin Telegram integration:

---

### BEGIN PROMPT

Connect Telegram to Nexus Hermes and Alpha. Follow these steps in order:

**1. Environment Setup**

Set the following environment variables:
```
TELEGRAM_BOT_TOKEN=<obtained from BotFather>
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook/telegram
TELEGRAM_CHAT_ID=<your personal chat ID>
TELEGRAM_ADMIN_CHAT_ID=<admin chat ID for Ray Review>
```

Verify all variables are loaded before proceeding.

**2. Bot Creation**

1. Message @BotFather on Telegram
2. Send `/newbot`
3. Name: `NexusOSBot`
4. Username: `nexus_os_bot` (or available alternative)
5. Copy the bot token
6. Set token in `TELEGRAM_BOT_TOKEN`

**3. Webhook Configuration**

Register webhook with Telegram API:
```
POST https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook
{
  "url": "https://your-domain.com/webhook/telegram",
  "allowed_updates": ["message", "callback_query"]
}
```

Verify webhook: `GET https://api.telegram.org/bot<YOUR_TOKEN>/getWebhookInfo`

**4. Hermes Message Handling**

Build message handler in `src/services/telegram/bridge.ts`:
- Receive webhook POST
- Parse message: `chat_id`, `text`, `from`, `message_id`
- Route to Hermes based on content:
  - Commands (`/status`, `/help`, `/review`) → Hermes command router
  - Free text → Hermes conversation handler
  - Callback queries → Approval response handler
- Return response through Telegram `sendMessage` API

**5. Alpha Message Handling**

Alpha receives action requests from Hermes:
- Validate request against safety rules
- If action requires approval → send to admin chat with inline keyboard
- If action is pre-approved → execute and return result
- Log all Alpha actions to `alpha_action_log` table

**6. Ray Review Notifications**

Configure notification flow:
- High-priority items → immediate `sendMessage` to admin chat
- Include: item title, summary, approve/reject buttons
- Approve button: callback_data = `approve_<item_id>`
- Reject button: callback_data = `reject_<item_id>`
- Process callback responses in bridge layer

**7. Work Order Status**

Allow status checks via Telegram:
- `/status` → current system health summary
- `/orders` → list of pending work orders
- `/order <id>` → details of specific work order
- All status commands are read-only

**8. Recovery Alerts**

Configure automated alerts:
- System failure → immediate admin notification
- Degraded state → warning notification
- Recovery complete → confirmation notification
- Use `scripts/daily_monitor.sh` output as trigger

**9. Daily Summaries**

Schedule daily summary at 08:00 UTC:
- Overnight activity count
- Pending items requiring attention
- System health status
- Next scheduled actions
- Send via `sendMessage` to admin chat

**10. Safety Gates**

Implement and enforce:
- Command whitelist: only `/status`, `/help`, `/orders`, `/order`, `/review`
- Rate limit: max 30 messages per minute per user
- Approval expiry: 24 hours for all Ray Review items
- No sensitive data in messages (redact API keys, tokens, secrets)
- Read-only mode for Phase 1 (notifications only)
- Sandbox-first: test bot on private channel before production

**11. Testing Checklist**

Before going live:
- [ ] Bot receives messages in sandbox
- [ ] Hermes routes correctly
- [ ] Alpha executes pre-approved actions
- [ ] Ray Review notifications deliver
- [ ] Approval callbacks process correctly
- [ ] Daily summary sends on schedule
- [ ] Recovery alerts trigger on failures
- [ ] Rate limiting works
- [ ] No sensitive data leaks

**12. Deployment**

Phase 1 (Sandbox): Test bot on private channel
Phase 2 (Limited): Production bot with notification-only scope
Phase 3 (Full): Production bot with approval workflow and limited actions

---

### END PROMPT
