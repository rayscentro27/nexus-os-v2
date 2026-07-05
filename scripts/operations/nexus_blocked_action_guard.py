#!/usr/bin/env python3
"""
Nexus Action Guard — validates requests against approval-gated actions.
Returns allowed/approval_gated/blocked with reason and required approvals.

Operating Model:
- ACTIVE_INTERNAL: Nexus auto-monitors, researches, scores, drafts, prepares, routes
- TELEGRAM_OPERATOR: Ray approves/rejects/revises via Telegram
- APPROVAL_GATED_LIVE: External actions execute only after Ray approval + guard + receipt
- BLOCKED_AUTONOMOUS_EXECUTION: Requires direct Ray intervention
"""

import json
import os
import sys

GUARD_PATH = "data/operations/nexus_blocked_action_guard.json"
LANES_PATH = "data/operations/nexus_approval_gated_lanes.json"
REPORT_PATH = "reports/runtime/nexus_blocked_action_guard_latest.md"

def load_guard():
    try:
        with open(GUARD_PATH) as f:
            return json.load(f)
    except:
        return {"approval_gated_actions": [], "active_internal_capabilities": [], "telegram_capabilities": []}

def load_lanes():
    try:
        with open(LANES_PATH) as f:
            return json.load(f)
    except:
        return {"lanes": {}}

def check_action(action_text):
    guard = load_guard()
    lanes = load_lanes()
    text_lower = action_text.lower()

    # Check approval-gated actions
    action_keywords = {
        "send_customer_email": ["send email", "email customer", "send customer"],
        "post_to_social_media": ["post to", "publish", "tiktok", "instagram", "facebook post", "social post"],
        "place_trade": ["place trade", "execute trade", "buy order", "sell order"],
        "charge_customer": ["charge", "bill customer", "process payment"],
        "submit_credit_dispute": ["submit dispute", "credit dispute", "dispute letter"],
        "submit_grant_application": ["submit grant", "apply for grant", "grant application"],
        "export_sensitive_client_data": ["export client", "client data export", "download client"],
        "send_sms": ["send sms", "text message", "send text"],
        "make_phone_calls": ["make call", "phone call", "call customer"],
        "submit_legal_documents": ["submit legal", "legal filing", "court documents"]
    }

    for gated_action in guard.get("approval_gated_actions", []):
        action_id = gated_action.get("action", "")
        keywords = action_keywords.get(action_id, [])
        for kw in keywords:
            if kw in text_lower:
                status = gated_action.get("status", "APPROVAL_GATED_LIVE_PENDING")
                return {
                    "allowed": True,
                    "approval_gated": True,
                    "blocked": False,
                    "action": action_id,
                    "status": status,
                    "lane": gated_action.get("lane", "unknown"),
                    "reason": f"Action '{action_id}' is approval-gated ({status}). Ray must approve before execution.",
                    "required_approval": gated_action.get("required_approval", "unknown"),
                    "required_runner": gated_action.get("required_runner", "unknown"),
                    "required_receipt": gated_action.get("required_receipt", "unknown"),
                    "workflow": gated_action.get("workflow", []),
                    "telegram_role": gated_action.get("telegram_role", "approve/reject"),
                    "sensitive_data_rule": gated_action.get("sensitive_data_rule", "show summary only")
                }

    # Check infrastructure blocks
    infra_keywords = ["modify production database", "restart production", "deploy to production"]
    for kw in infra_keywords:
        if kw in text_lower:
            return {
                "allowed": False,
                "approval_gated": False,
                "blocked": True,
                "action": "infrastructure",
                "status": "BLOCKED_AUTONOMOUS_EXECUTION",
                "reason": "Infrastructure changes require direct Ray intervention, not just Telegram approval",
                "required_approval": "direct_ray_intervention",
                "required_runner": None,
                "required_receipt": None,
                "workflow": [],
                "telegram_role": "request_only",
                "sensitive_data_rule": "N/A"
            }

    return {
        "allowed": True,
        "approval_gated": False,
        "blocked": False,
        "action": "active_internal",
        "status": "ACTIVE_INTERNAL",
        "reason": "Action is safe for internal execution. Nexus can monitor, research, score, draft, prepare, route, create work orders, generate approval packets, write receipts.",
        "required_approval": None,
        "required_runner": None,
        "required_receipt": None,
        "workflow": [],
        "telegram_role": None,
        "sensitive_data_rule": None
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 nexus_blocked_action_guard.py '<action text>'")
        print("\nOperating Model:")
        print("  ACTIVE_INTERNAL: auto-monitor, research, score, draft, prepare, route")
        print("  TELEGRAM_OPERATOR: Ray approves/rejects/revises via Telegram")
        print("  APPROVAL_GATED_LIVE: external actions after Ray approval + guard + receipt")
        print("  BLOCKED_AUTONOMOUS_EXECUTION: requires direct Ray intervention")
        sys.exit(1)

    action_text = sys.argv[1]
    result = check_action(action_text)

    report = f"""# Nexus Action Guard Check

**Input**: {action_text}
**Result**: {"APPROVAL_GATED (" + result["status"] + ")" if result.get("approval_gated") else "BLOCKED" if result["blocked"] else "ALLOWED (" + result["status"] + ")"}

---

## Operating Model

| Mode | Description |
|------|-------------|
| ACTIVE_INTERNAL | Nexus auto-monitors, researches, scores, drafts, prepares, routes, creates work orders, generates approval packets, writes receipts |
| TELEGRAM_OPERATOR | Ray reviews approval packets, approves, rejects, revises, sends internal requests, triggers safe processes |
| APPROVAL_GATED_LIVE | External actions execute only after Ray approval + guard + receipt + compliance |
| BLOCKED_AUTONOMOUS_EXECUTION | Requires direct Ray intervention |

---

## Guard Result

| Field | Value |
|-------|-------|
| Allowed | {result["allowed"]} |
| Approval Gated | {result.get("approval_gated", False)} |
| Blocked | {result["blocked"]} |
| Action | {result["action"]} |
| Status | {result.get("status", "N/A")} |
| Lane | {result.get("lane", "N/A")} |
| Reason | {result["reason"]} |
| Required Approval | {result["required_approval"] or 'N/A'} |
| Required Runner | {result["required_runner"] or 'N/A'} |
| Required Receipt | {result["required_receipt"] or 'N/A'} |
| Telegram Role | {result.get("telegram_role", "N/A")} |
| Sensitive Data Rule | {result.get("sensitive_data_rule", "N/A")} |
"""

    if result.get("workflow"):
        report += "\n## Required Workflow\n\n"
        report += "| Step | Action | Mode | Auto |\n"
        report += "|------|--------|------|------|\n"
        for i, step in enumerate(result["workflow"], 1):
            if isinstance(step, dict):
                report += f"| {step.get('step', i)} | {step.get('action', step)} | {step.get('mode', 'N/A')} | {step.get('auto', 'N/A')} |\n"
            else:
                report += f"| {i} | {step} | N/A | N/A |\n"

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        f.write(report)

    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
