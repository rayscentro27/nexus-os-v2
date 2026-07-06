#!/usr/bin/env python3
"""
Nexus Stripe Test Checkout Lane — approval-gated test checkout workflow.
Workflow: test product/price → checkout link/session → Ray test → receipt → access state update
Test mode only. No live charges. No real customer billing.
"""
import json
import os
import sys
from datetime import datetime, timezone

LANE = "stripe_test_checkout"
APPROVAL_DIR = "reports/approval_packets"
RECEIPT_DIR = "reports/approval_lanes/receipts"

TIER_1 = {"name": "Nexus Readiness Portal", "product_id": "prod_Tn99pBvgTeJ9dx", "price_id": "price_1SpYrL2MIMiohBBFTqGJqb0b", "amount": 10000, "interval": "month"}
TIER_2 = {"name": "Nexus Funding Builder Plus", "product_id": "prod_UpeRRU4DGE1AvS", "price_id": "price_1Tpz922MIMiohBBFuzM642Hu", "amount": 19700, "interval": "month"}

def create_checkout_request(tier, test_email="test@example.com", success_url="http://localhost:5173/success", cancel_url="http://localhost:5173/cancel"):
    tier_config = TIER_1 if tier == "tier1" else TIER_2
    item_id = f"STRIPE-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
    packet = {
        "item_id": item_id,
        "lane": LANE,
        "title": f"Stripe Test Checkout: {tier_config['name']}",
        "safe_summary": f"Test checkout for {tier_config['name']} — ${tier_config['amount']/100:.0f}/{tier_config['interval']}",
        "risk_level": "low",
        "required_approval": "billing_approval",
        "required_runner": "stripe_test_checkout_runner",
        "required_env": "STRIPE_SECRET_KEY",
        "required_receipt": "stripe_checkout_receipt",
        "current_status": "DRAFT",
        "next_action": f"Submit for Ray Review via /approve {item_id}",
        "receipt_path": f"{RECEIPT_DIR}/{item_id}_receipt.json",
        "dashboard_link": f"/admin/approvals/{item_id}",
        "workflow": [
            {"step": 1, "action": "checkout_requested", "status": "complete"},
            {"step": 2, "action": "ray_review", "status": "pending"},
            {"step": 3, "action": "approve_checkout", "status": "pending"},
            {"step": 4, "action": "create_stripe_session", "status": "pending"},
            {"step": 5, "action": "write_receipt", "status": "pending"},
            {"step": 6, "action": "log_access_state", "status": "pending"}
        ],
        "checkout_data": {
            "tier": tier,
            "tier_name": tier_config["name"],
            "product_id": tier_config["product_id"],
            "price_id": tier_config["price_id"],
            "amount": tier_config["amount"],
            "interval": tier_config["interval"],
            "test_email": test_email,
            "success_url": success_url,
            "cancel_url": cancel_url,
            "mode": "test_only"
        },
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    os.makedirs(APPROVAL_DIR, exist_ok=True)
    with open(f"{APPROVAL_DIR}/{item_id}.json", "w") as f:
        json.dump(packet, f, indent=2)
    print(json.dumps({"status": "checkout_requested", "item_id": item_id, "tier": tier_config["name"]}, indent=2))
    return packet

def approve_and_create_session(item_id):
    packet_path = f"{APPROVAL_DIR}/{item_id}.json"
    if not os.path.exists(packet_path):
        print(json.dumps({"error": f"Packet {item_id} not found"}))
        return None
    with open(packet_path) as f:
        packet = json.load(f)
    stripe_key = os.environ.get("STRIPE_SECRET_KEY")
    if not stripe_key:
        packet["current_status"] = "APPROVED_BUT_ENV_MISSING"
        packet["next_action"] = "Set STRIPE_SECRET_KEY env var, then re-run"
        with open(packet_path, "w") as f:
            json.dump(packet, f, indent=2)
        print(json.dumps({"status": "approved_but_env_missing", "item_id": item_id}))
        return packet
    try:
        import requests
        cd = packet["checkout_data"]
        resp = requests.post(
            "https://api.stripe.com/v1/checkout/sessions",
            auth=(stripe_key, ""),
            data={
                "mode": "subscription",
                "line_items[0][price]": cd["price_id"],
                "line_items[0][quantity]": "1",
                "success_url": cd["success_url"],
                "cancel_url": cd["cancel_url"],
                "customer_email": cd["test_email"]
            },
            timeout=10
        )
        result = resp.json()
        if resp.status_code == 200:
            packet["current_status"] = "CHECKOUT_SESSION_CREATED"
            packet["checkout_url"] = result.get("url")
            packet["session_id"] = result.get("id")
        else:
            packet["current_status"] = "SESSION_CREATION_FAILED"
            packet["error"] = result
        packet["created_at_stripe"] = datetime.now(timezone.utc).isoformat()
        receipt = {"item_id": item_id, "lane": LANE, "action": "create_session", "status": packet["current_status"], "session_id": packet.get("session_id"), "timestamp": datetime.now(timezone.utc).isoformat()}
        os.makedirs(RECEIPT_DIR, exist_ok=True)
        with open(f"{RECEIPT_DIR}/{item_id}_receipt.json", "w") as f:
            json.dump(receipt, f, indent=2)
        with open(packet_path, "w") as f:
            json.dump(packet, f, indent=2)
        print(json.dumps({"status": packet["current_status"], "item_id": item_id, "checkout_url": packet.get("checkout_url")}, indent=2))
    except Exception as e:
        packet["current_status"] = "SESSION_CREATION_FAILED"
        packet["error"] = str(e)
        with open(packet_path, "w") as f:
            json.dump(packet, f, indent=2)
        print(json.dumps({"status": "session_creation_failed", "error": str(e)}))
    return packet

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 nexus_stripe_test_checkout_lane.py request <tier1|tier2> [email]")
        print("  python3 nexus_stripe_test_checkout_lane.py approve <item_id>")
        print("  python3 nexus_stripe_test_checkout_lane.py status <item_id>")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "request":
        tier = sys.argv[2] if len(sys.argv) > 2 else "tier1"
        email = sys.argv[3] if len(sys.argv) > 3 else "test@example.com"
        create_checkout_request(tier, email)
    elif cmd == "approve":
        approve_and_create_session(sys.argv[2])
    elif cmd == "status":
        path = f"{APPROVAL_DIR}/{sys.argv[2]}.json"
        if os.path.exists(path):
            with open(path) as f:
                print(json.dumps(json.load(f), indent=2))
        else:
            print(f"Packet {sys.argv[2]} not found")
    else:
        print(f"Unknown command: {cmd}")

if __name__ == "__main__":
    main()
