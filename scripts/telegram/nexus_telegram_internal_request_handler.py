#!/usr/bin/env python3
"""
Nexus Telegram Internal Request Handler — creates work orders from Telegram requests.
Classifies route, assigns mode, writes receipt.
"""

import json
import os
from datetime import datetime, timezone

WORK_ORDERS_PATH = "reports/work_orders/nexus_internal_work_orders_latest.json"
REQUEST_DIR = "reports/telegram/receipts/internal_requests"

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

def classify_route(text):
    t = text.lower()
    if any(kw in t for kw in ["research", "find", "discover", "explore"]):
        return "alpha"
    if any(kw in t for kw in ["creative", "video", "script", "content", "draft"]):
        return "creative"
    if any(kw in t for kw in ["client", "portal", "credit", "funding", "onboard"]):
        return "client_portal"
    if any(kw in t for kw in ["recovery", "stale", "failed", "fix"]):
        return "recovery"
    if any(kw in t for kw in ["marketing", "post", "social", "seo"]):
        return "marketing"
    if any(kw in t for kw in ["health", "status", "monitor"]):
        return "operations"
    return "hermes"

def create_request(request_text):
    now = datetime.now(timezone.utc)
    wo_id = f"wo_tg_{now.strftime('%Y%m%dT%H%M%S')}"
    route = classify_route(request_text)

    blocked_keywords = ["send email", "email customer", "post to", "publish", "tiktok", "place trade", "charge", "submit dispute", "submit grant"]
    is_blocked = any(kw in request_text.lower() for kw in blocked_keywords)
    mode = "BLOCKED" if is_blocked else "ACTIVE_INTERNAL"

    wo = {
        "work_order_id": wo_id,
        "title": request_text,
        "route": route,
        "mode": mode,
        "source": "telegram_internal_request",
        "created_at": now.isoformat(),
        "status": "blocked" if is_blocked else "created"
    }

    orders = load_json(WORK_ORDERS_PATH) or []
    orders.append(wo)
    save_json(WORK_ORDERS_PATH, orders)

    receipt = {
        "receipt_id": f"req_{wo_id}",
        "timestamp": now.isoformat(),
        "source": "telegram",
        "type": "internal_request",
        "request": request_text,
        "route": route,
        "mode": mode,
        "work_order_id": wo_id,
        "blocked": is_blocked
    }
    receipt_path = os.path.join(REQUEST_DIR, f"{receipt['receipt_id']}.json")
    save_json(receipt_path, receipt)

    return wo, receipt

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: nexus_telegram_internal_request_handler.py '<request text>'")
        sys.exit(1)
    wo, receipt = create_request(sys.argv[1])
    print(json.dumps({"work_order": wo, "receipt": receipt}, indent=2))
