# Nexus Telegram — Mobile Operator Console Contract

**Generated**: 2026-07-05

---

## Purpose

Telegram is Ray's mobile operator console for Nexus OS. It is NOT just a notification layer.

Ray may be on the road or out of town. Telegram may become 80% of how he communicates with Nexus.

## Capabilities

### Ray MUST be able to:
- ✅ Approve items from Telegram
- ✅ Reject items from Telegram
- ✅ Request revisions from Telegram
- ✅ Send internal work requests through Telegram
- ✅ Send Hermes advisory requests through Telegram
- ✅ Send Alpha research/intake requests through Telegram
- ✅ Review Ray Review queue from Telegram
- ✅ Create work orders from Telegram
- ✅ Trigger safe internal processes from Telegram
- ✅ Receive daily summaries and system alerts from Telegram
- ✅ Keep Nexus running while Ray is away

### Ray MUST NOT be able to:
- ❌ Send customer emails (needs approved runner)
- ❌ Post to social media (needs approved runner)
- ❌ Place trades (needs approved runner)
- ❌ Charge customers (needs approved runner)
- ❌ Submit credit disputes (needs compliance runner)
- ❌ Submit grant applications (needs compliance runner)
- ❌ Access sensitive client data (needs access control)

## Receipt Model

Every Telegram mutation writes a receipt:
- `receipt_id`: unique ID
- `timestamp`: ISO 8601
- `source`: telegram
- `type`: approval/rejection/revision/internal_request/hermes/alpha/process_run
- `decision`: approved/rejected/revision_requested
- `work_order_id`: if work order created
- `report_path`: path to receipt file

## Receipt Paths

- Approvals: `reports/telegram/receipts/approvals/`
- Internal Requests: `reports/telegram/receipts/internal_requests/`
- Hermes: `reports/telegram/receipts/hermes/`
- Alpha: `reports/telegram/receipts/alpha/`
