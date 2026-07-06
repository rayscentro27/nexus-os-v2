#!/usr/bin/env python3
"""
Nexus Customer Email Lane — approval-gated email workflow.
Workflow: draft → Ray Review → approve → send via Resend → receipt → delivery log
Never sends without Ray approval.
"""
import json
import os
import sys
from datetime import datetime, timezone

LANE = "customer_email"
APPROVAL_DIR = "reports/approval_packets"
RECEIPT_DIR = "reports/approval_lanes/receipts"
PROVIDER = "resend"

def create_draft(to_email, subject, body, from_name="Nexus"):
    draft_id = f"EMAIL-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
    packet = {
        "item_id": draft_id,
        "lane": LANE,
        "title": f"Customer Email: {subject}",
        "safe_summary": f"Email to {to_email[:3]}*** — Subject: {subject[:50]}...",
        "risk_level": "medium",
        "required_approval": "email_compliance_approval",
        "required_runner": "resend_api_runner",
        "required_env": "RESEND_API_KEY",
        "required_receipt": "email_send_receipt",
        "current_status": "DRAFT",
        "next_action": "Submit for Ray Review via /approve " + draft_id,
        "receipt_path": f"{RECEIPT_DIR}/{draft_id}_receipt.json",
        "dashboard_link": f"/admin/approvals/{draft_id}",
        "workflow": [
            {"step": 1, "action": "draft_created", "status": "complete"},
            {"step": 2, "action": "ray_review", "status": "pending"},
            {"step": 3, "action": "approve_send", "status": "pending"},
            {"step": 4, "action": "send_via_resend", "status": "pending"},
            {"step": 5, "action": "write_receipt", "status": "pending"},
            {"step": 6, "action": "log_delivery", "status": "pending"}
        ],
        "email_data": {
            "to": to_email,
            "subject": subject,
            "body": body,
            "from_name": from_name
        },
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    os.makedirs(APPROVAL_DIR, exist_ok=True)
    with open(f"{APPROVAL_DIR}/{draft_id}.json", "w") as f:
        json.dump(packet, f, indent=2)
    print(json.dumps({"status": "draft_created", "item_id": draft_id, "packet": packet}, indent=2))
    return packet

def approve_and_send(item_id, approved_by="ray"):
    packet_path = f"{APPROVAL_DIR}/{item_id}.json"
    if not os.path.exists(packet_path):
        print(json.dumps({"error": f"Packet {item_id} not found"}))
        return None
    with open(packet_path) as f:
        packet = json.load(f)
    if packet.get("current_status") == "SENT":
        print(json.dumps({"error": "Already sent"}))
        return None
    resend_key = os.environ.get("RESEND_API_KEY")
    if not resend_key:
        packet["current_status"] = "APPROVED_BUT_PROVIDER_ENV_MISSING"
        packet["next_action"] = "Set RESEND_API_KEY env var, then re-run"
        with open(packet_path, "w") as f:
            json.dump(packet, f, indent=2)
        print(json.dumps({"status": "approved_but_env_missing", "item_id": item_id}))
        return packet
    try:
        import requests
        email_data = packet["email_data"]
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
            json={"from": f"{email_data['from_name']} <onboarding@resend.dev>", "to": [email_data["to"]], "subject": email_data["subject"], "html": email_data["body"]},
            timeout=10
        )
        result = resp.json()
        packet["current_status"] = "SENT" if resp.status_code == 200 else "SEND_FAILED"
        packet["send_result"] = result
        packet["sent_at"] = datetime.now(timezone.utc).isoformat()
        receipt = {"item_id": item_id, "lane": LANE, "action": "send", "status": packet["current_status"], "result": result, "timestamp": datetime.now(timezone.utc).isoformat()}
        os.makedirs(RECEIPT_DIR, exist_ok=True)
        with open(f"{RECEIPT_DIR}/{item_id}_receipt.json", "w") as f:
            json.dump(receipt, f, indent=2)
        with open(packet_path, "w") as f:
            json.dump(packet, f, indent=2)
        print(json.dumps({"status": packet["current_status"], "item_id": item_id, "result": result}, indent=2))
    except Exception as e:
        packet["current_status"] = "SEND_FAILED"
        packet["error"] = str(e)
        with open(packet_path, "w") as f:
            json.dump(packet, f, indent=2)
        print(json.dumps({"status": "send_failed", "error": str(e)}))
    return packet

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 nexus_customer_email_lane.py draft <to> <subject> <body>")
        print("  python3 nexus_customer_email_lane.py approve <item_id>")
        print("  python3 nexus_customer_email_lane.py status <item_id>")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "draft":
        to_email = sys.argv[2] if len(sys.argv) > 2 else "test@example.com"
        subject = sys.argv[3] if len(sys.argv) > 3 else "Test Email from Nexus"
        body = sys.argv[4] if len(sys.argv) > 4 else "<p>This is a test email from Nexus Customer Email Lane.</p>"
        create_draft(to_email, subject, body)
    elif cmd == "approve":
        approve_and_send(sys.argv[2])
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
