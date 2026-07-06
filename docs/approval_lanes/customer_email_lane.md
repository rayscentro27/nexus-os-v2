# Customer Email Lane

**Status**: CUSTOMER_EMAIL_APPROVAL_GATED_READY

## Workflow

1. Draft email (Nexus creates approval packet)
2. Ray Review (via Telegram /review)
3. Approve (via Telegram /approve EMAIL-XXX)
4. Send via Resend (requires RESEND_API_KEY)
5. Write receipt
6. Log delivery

## Commands

```bash
# Create draft
python3 scripts/approval_lanes/nexus_customer_email_lane.py draft <to> <subject> <body>

# Approve and send
python3 scripts/approval_lanes/nexus_customer_email_lane.py approve <item_id>

# Check status
python3 scripts/approval_lanes/nexus_customer_email_lane.py status <item_id>
```

## Requirements

- RESEND_API_KEY env var for live sending
- Ray approval for every email
- No sensitive client data in Telegram summaries
