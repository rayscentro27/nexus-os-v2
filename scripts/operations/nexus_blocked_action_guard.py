#!/usr/bin/env python3
"""
Nexus Blocked Action Guard — validates requests against blocked actions.
Returns allowed/blocked with reason and required approvals.
"""

import json
import os
import sys

GUARD_PATH = "data/operations/nexus_blocked_action_guard.json"
REPORT_PATH = "reports/runtime/nexus_blocked_action_guard_latest.md"

def load_guard():
    try:
        with open(GUARD_PATH) as f:
            return json.load(f)
    except:
        return {"blocked_actions": [], "guard_rules": {}}

def check_action(action_text):
    guard = load_guard()
    text_lower = action_text.lower()

    blocked_keywords = {
        "send_customer_email": ["send email", "email customer", "send customer"],
        "post_to_social_media": ["post to", "publish", "tiktok", "instagram", "facebook post", "social post"],
        "place_trade": ["place trade", "execute trade", "buy", "sell order"],
        "charge_customer": ["charge", "bill customer", "process payment"],
        "submit_credit_dispute": ["submit dispute", "credit dispute", "dispute letter"],
        "submit_grant_application": ["submit grant", "apply for grant", "grant application"],
        "export_sensitive_client_data": ["export client", "client data export", "download client"]
    }

    for blocked_id, keywords in blocked_keywords.items():
        for kw in keywords:
            if kw in text_lower:
                rule = guard.get("guard_rules", {}).get(blocked_id, {})
                return {
                    "allowed": False,
                    "blocked": True,
                    "action": blocked_id,
                    "reason": f"Action '{blocked_id}' is blocked",
                    "required_approval": rule.get("required_approval", "unknown"),
                    "required_runner": rule.get("required_runner", "unknown"),
                    "required_receipt": rule.get("required_receipt", "unknown")
                }

    return {
        "allowed": True,
        "blocked": False,
        "action": "internal_safe",
        "reason": "Action not in blocked list",
        "required_approval": None,
        "required_runner": None,
        "required_receipt": None
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 nexus_blocked_action_guard.py '<action text>'")
        sys.exit(1)

    action_text = sys.argv[1]
    result = check_action(action_text)

    report = f"""# Nexus Blocked Action Guard Check

**Input**: {action_text}
**Result**: {"BLOCKED" if result["blocked"] else "ALLOWED"}

---

| Field | Value |
|-------|-------|
| Allowed | {result["allowed"]} |
| Blocked | {result["blocked"]} |
| Action | {result["action"]} |
| Reason | {result["reason"]} |
| Required Approval | {result["required_approval"] or 'N/A'} |
| Required Runner | {result["required_runner"] or 'N/A'} |
| Required Receipt | {result["required_receipt"] or 'N/A'} |
"""

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        f.write(report)

    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
