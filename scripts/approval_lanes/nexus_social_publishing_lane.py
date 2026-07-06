#!/usr/bin/env python3
"""
Nexus Social Publishing Lane — approval-gated social workflow.
Workflow: create content → Ray Review → approve → publish → receipt → performance log
Never publishes without approval.
"""
import json
import os
import sys
from datetime import datetime, timezone

LANE = "social_publishing"
APPROVAL_DIR = "reports/approval_packets"
RECEIPT_DIR = "reports/approval_lanes/receipts"
SUPPORTED_PLATFORMS = ["facebook", "instagram"]
PENDING_PLATFORMS = ["tiktok", "youtube", "x", "linkedin"]

def create_content(platform, content_type, caption, media_path=None):
    item_id = f"SOCIAL-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
    platform_status = "supported" if platform.lower() in SUPPORTED_PLATFORMS else "pending"
    packet = {
        "item_id": item_id,
        "lane": LANE,
        "title": f"Social Post: {platform} {content_type}",
        "safe_summary": f"{platform.title()} {content_type} — Caption: {caption[:80]}...",
        "risk_level": "medium",
        "required_approval": "social_publish_approval",
        "required_runner": f"{platform}_publish_runner",
        "required_env": f"{platform.upper()}_ACCESS_TOKEN",
        "required_receipt": "social_publish_receipt",
        "current_status": "DRAFT",
        "next_action": f"Submit for Ray Review via /approve {item_id}",
        "receipt_path": f"{RECEIPT_DIR}/{item_id}_receipt.json",
        "dashboard_link": f"/admin/approvals/{item_id}",
        "workflow": [
            {"step": 1, "action": "content_created", "status": "complete"},
            {"step": 2, "action": "ray_review", "status": "pending"},
            {"step": 3, "action": "approve_publish", "status": "pending"},
            {"step": 4, "action": f"publish_to_{platform}", "status": "pending"},
            {"step": 5, "action": "write_receipt", "status": "pending"},
            {"step": 6, "action": "log_performance", "status": "pending"}
        ],
        "revision_memory": [],
        "content_data": {
            "platform": platform,
            "content_type": content_type,
            "caption": caption,
            "media_path": media_path,
            "platform_status": platform_status
        },
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    os.makedirs(APPROVAL_DIR, exist_ok=True)
    with open(f"{APPROVAL_DIR}/{item_id}.json", "w") as f:
        json.dump(packet, f, indent=2)
    print(json.dumps({"status": "content_created", "item_id": item_id, "platform": platform, "platform_status": platform_status}, indent=2))
    return packet

def approve_and_publish(item_id, approved_by="ray"):
    packet_path = f"{APPROVAL_DIR}/{item_id}.json"
    if not os.path.exists(packet_path):
        print(json.dumps({"error": f"Packet {item_id} not found"}))
        return None
    with open(packet_path) as f:
        packet = json.load(f)
    platform = packet["content_data"]["platform"]
    env_key = f"{platform.upper()}_ACCESS_TOKEN"
    access_token = os.environ.get(env_key)
    if not access_token:
        packet["current_status"] = "APPROVED_BUT_PROVIDER_ENV_MISSING"
        packet["next_action"] = f"Set {env_key} env var, then re-run"
        with open(packet_path, "w") as f:
            json.dump(packet, f, indent=2)
        print(json.dumps({"status": "approved_but_env_missing", "item_id": item_id, "required_env": env_key}))
        return packet
    packet["current_status"] = "APPROVED_BUT_PUBLISH_NOT_IMPLEMENTED"
    packet["next_action"] = f"Implement {platform} publish API call, then re-run"
    packet["published_at"] = datetime.now(timezone.utc).isoformat()
    with open(packet_path, "w") as f:
        json.dump(packet, f, indent=2)
    receipt = {"item_id": item_id, "lane": LANE, "action": "approve", "status": "approved", "timestamp": datetime.now(timezone.utc).isoformat()}
    os.makedirs(RECEIPT_DIR, exist_ok=True)
    with open(f"{RECEIPT_DIR}/{item_id}_receipt.json", "w") as f:
        json.dump(receipt, f, indent=2)
    print(json.dumps({"status": "approved_ready_to_publish", "item_id": item_id, "platform": platform}, indent=2))
    return packet

def add_revision(item_id, feedback):
    packet_path = f"{APPROVAL_DIR}/{item_id}.json"
    if not os.path.exists(packet_path):
        print(json.dumps({"error": f"Packet {item_id} not found"}))
        return None
    with open(packet_path) as f:
        packet = json.load(f)
    revision = {"feedback": feedback, "timestamp": datetime.now(timezone.utc).isoformat()}
    packet.setdefault("revision_memory", []).append(revision)
    packet["current_status"] = "REVISION_REQUESTED"
    packet["next_action"] = f"Revise content based on: {feedback}"
    with open(packet_path, "w") as f:
        json.dump(packet, f, indent=2)
    print(json.dumps({"status": "revision_requested", "item_id": item_id, "feedback": feedback}, indent=2))
    return packet

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 nexus_social_publishing_lane.py create <platform> <type> <caption> [media_path]")
        print("  python3 nexus_social_publishing_lane.py approve <item_id>")
        print("  python3 nexus_social_publishing_lane.py revise <item_id> <feedback>")
        print("  python3 nexus_social_publishing_lane.py status <item_id>")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "create":
        platform = sys.argv[2] if len(sys.argv) > 2 else "facebook"
        content_type = sys.argv[3] if len(sys.argv) > 3 else "image"
        caption = sys.argv[4] if len(sys.argv) > 4 else "Test post from Nexus"
        media = sys.argv[5] if len(sys.argv) > 5 else None
        create_content(platform, content_type, caption, media)
    elif cmd == "approve":
        approve_and_publish(sys.argv[2])
    elif cmd == "revise":
        add_revision(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "needs improvement")
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
