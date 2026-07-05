#!/usr/bin/env python3
"""
Nexus Telegram Approval Handler — records approval decisions from Telegram.
Finds items, records decisions, writes receipts, creates next work orders.
"""

import json
import os
from datetime import datetime, timezone

APPROVAL_DIR = "reports/telegram/receipts/approvals"
WORK_ORDERS_PATH = "reports/work_orders/nexus_internal_work_orders_latest.json"

def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return None

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def handle_approval(item_id, decision, reason=None, feedback=None):
    now = datetime.now(timezone.utc)
    receipt_id = f"approval_{item_id}_{now.strftime('%Y%m%dT%H%M%S')}"

    allowed_next_step = None
    blocked_next_step = None
    created_work_order_id = None

    if decision == "approved":
        allowed_next_step = "internal_safe_work"
        blocked_next_step = "external_action_without_runner"
    elif decision == "rejected":
        blocked_next_step = "all"
    elif decision == "revision_requested":
        allowed_next_step = "revision"

    receipt = {
        "receipt_id": receipt_id,
        "timestamp": now.isoformat(),
        "source": "telegram",
        "decision": decision,
        "item_id": item_id,
        "reason": reason,
        "feedback": feedback,
        "allowed_next_step": allowed_next_step,
        "blocked_next_step": blocked_next_step,
        "created_work_order_id": created_work_order_id
    }

    path = os.path.join(APPROVAL_DIR, f"{receipt_id}.json")
    save_json(path, receipt)

    report = f"""# Telegram Approval Receipt

**Generated**: {now.isoformat()}

| Field | Value |
|-------|-------|
| Receipt ID | {receipt_id} |
| Item ID | {item_id} |
| Decision | {decision} |
| Reason | {reason or 'N/A'} |
| Feedback | {feedback or 'N/A'} |
| Allowed Next Step | {allowed_next_step or 'None'} |
| Blocked Next Step | {blocked_next_step or 'None'} |
"""
    report_path = f"reports/telegram/nexus_telegram_approval_{item_id}_receipt.md"
    with open(report_path, "w") as f:
        f.write(report)

    return receipt

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: nexus_telegram_approval_handler.py <item-id> <approved|rejected|revision_requested> [reason/feedback]")
        sys.exit(1)
    item_id = sys.argv[1]
    decision = sys.argv[2]
    extra = sys.argv[3] if len(sys.argv) > 3 else None
    result = handle_approval(item_id, decision, extra if decision != "revision_requested" else None, extra if decision == "revision_requested" else None)
    print(json.dumps(result, indent=2))
