# Hermes Alpha Telegram Connection Plan

**Generated:** 2026-07-05  
**Status:** Architecture Defined — Implementation Pending

---

## Architecture Diagram

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Telegram   │────▶│   Bridge     │────▶│    Hermes    │
│   Bot API    │◀────│   Layer      │◀────│   Router     │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                                         ┌────────▼───────┐
                                         │     Alpha      │
                                         │   Executor     │
                                         └────────┬───────┘
                                                  │
                                         ┌────────▼───────┐
                                         │   Ray Review   │
                                         │   Gate         │
                                         └────────────────┘
```

## Connection Sequence

### Phase 1: Bot Setup
1. Create bot via BotFather → obtain token
2. Set `TELEGRAM_BOT_TOKEN` in environment
3. Register webhook URL with Telegram API
4. Verify webhook is receiving updates

### Phase 2: Hermes Integration
1. Build message parser (extract command, text, metadata)
2. Route messages to Hermes router based on content type
3. Hermes determines appropriate response/action
4. Response sent back through bridge to Telegram

### Phase 3: Alpha Integration
1. Alpha receives action requests from Hermes
2. Alpha validates request against safety rules
3. If approved: execute and return result
4. If Ray Review required: send approval request to admin chat

### Phase 4: Notification System
1. High-priority alerts → immediate admin notification
2. Daily summaries → scheduled message at 08:00 UTC
3. Recovery alerts → triggered on system state changes

## Message Flow

### User → Hermes
```
User sends message to bot
  → Bridge layer receives webhook
  → Parses message content
  → Routes to Hermes
  → Hermes processes and responds
  → Bridge sends response to Telegram
```

### Ray Review Request
```
Alpha generates action requiring approval
  → Sends approval request to admin chat
  → Admin responds with approve/reject
  → Bridge processes response
  → Alpha executes or discards action
```

### Daily Summary
```
Scheduler triggers at 08:00 UTC
  → Collects overnight activity data
  → Formats summary message
  → Sends to admin chat via bridge
```

## Safety Gates

| Gate | Rule | Action on Failure |
|------|------|-------------------|
| Message validation | Reject malformed messages | Log and ignore |
| Command whitelist | Only approved commands | Reject with error |
| Rate limiting | Max 30 messages/min | Throttle with warning |
| Approval required | Actions need Ray Review | Queue for admin |
| Data sensitivity | No secrets in messages | Redact and alert |
| Time-based expiry | Approvals expire in 24h | Auto-reject and notify |

## Next Actions

1. Create Telegram bot and obtain token
2. Build bridge layer (webhook handler)
3. Implement Hermes message router
4. Implement Alpha action executor
5. Build Ray Review approval flow
6. Configure daily summary scheduler
7. Test in sandbox environment
8. Deploy to production after validation
