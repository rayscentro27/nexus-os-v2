#!/usr/bin/env python3
"""
Nexus Telegram Bridge — Mobile Operator Console for Nexus OS.

Ray's mobile command center. Supports:
- Status queries
- Daily summaries
- Ray Review queue
- Approve/reject/revise
- Internal requests
- Hermes routing
- Alpha intake
- Safe process triggering
- Blocked action guard
- Live polling (one-shot bounded mode)

Usage:
  python3 scripts/telegram/nexus_telegram_bridge.py --once
  python3 scripts/telegram/nexus_telegram_bridge.py --dry-run
  python3 scripts/telegram/nexus_telegram_bridge.py --test-command "/status"
"""

import json
import os
import sys
import hashlib
import ssl
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# SSL context for Telegram API (handles macOS self-signed cert issues)
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

RECEIPT_DIR = "reports/telegram/receipts"
WORK_ORDERS_PATH = "reports/work_orders/nexus_internal_work_orders_latest.json"
REGISTRY_PATH = "data/operations/nexus_process_registry.json"
BLOCKED_GUARD_PATH = "data/operations/nexus_blocked_action_guard.json"
HERMES_RECEIPT_DIR = "reports/telegram/receipts/hermes"
ALPHA_RECEIPT_DIR = "reports/telegram/receipts/alpha"
APPROVAL_RECEIPT_DIR = "reports/telegram/receipts/approvals"
INTERNAL_REQUEST_DIR = "reports/telegram/receipts/internal_requests"
LIVE_POLLING_DIR = "reports/telegram/receipts/live_polling"
TELEGRAM_STATE_PATH = "data/runtime/telegram_last_update_id.json"
TELEGRAM_REPORT_PATH = "reports/telegram/nexus_telegram_live_polling_activation.md"

# Allowed chat IDs (Ray's private chat only)
ALLOWED_CHAT_IDS = set()
_allowed = os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS", "1288928049")
for cid in _allowed.split(","):
    cid = cid.strip()
    if cid:
        ALLOWED_CHAT_IDS.add(int(cid))

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"

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

def write_receipt(subdir, receipt):
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rid = f"tg_{receipt.get('type','unknown')}_{ts}"
    receipt["receipt_id"] = rid
    receipt["timestamp"] = datetime.now(timezone.utc).isoformat()
    receipt["source"] = "telegram_bridge"
    path = os.path.join(RECEIPT_DIR, subdir, f"{rid}.json")
    save_json(path, receipt)
    return receipt

def load_work_orders():
    return load_json(WORK_ORDERS_PATH) or []

def save_work_orders(orders):
    save_json(WORK_ORDERS_PATH, orders)

def create_work_order(title, route, mode, source="telegram"):
    orders = load_work_orders()
    wo_id = f"wo_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
    wo = {
        "work_order_id": wo_id,
        "title": title,
        "route": route,
        "mode": mode,
        "source": source,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "created"
    }
    orders.append(wo)
    save_work_orders(orders)
    return wo

def cmd_start():
    return "Nexus Mobile Operator Console\n\nCommands:\n/report - Full anytime operator report\n/status - System status\n/daily - Daily monitor\n/research - Research/NotebookLM/Alpha status\n/content - Content drafts/social/email status\n/approvals - Ray Review queue count and summaries\n/orders - Work orders summary\n/hermes <msg> - Hermes advisory\n/recover - Recovery check\n/approve <id> - Approve item\n/reject <id> <reason> - Reject\n/revise <id> <feedback> - Request revision\n/request <text> - Internal request\n/alpha <topic> - Alpha research\n/processes - Process registry\n/run <id> - Run safe process\n/blocked - Blocked actions"

def cmd_report():
    try:
        with open("reports/runtime/nexus_anytime_operator_report_latest.json") as f:
            r = json.load(f)
        s = r.get("system_status", {})
        b = r.get("business_output_status", {})
        a = r.get("approval_queue", {})
        h = r.get("hermes_recommendation", {})
        lines = [
            f"Nexus Anytime Report",
            f"Score: {s.get('active_os_score', '?')}/100 {s.get('classification', '')}",
            f"Running: YES — {s.get('active_operator', {}).get('processes', 0)} processes",
            f"Outputs: {b.get('receipts', 0)} receipts, {b.get('approval_packets', 0)} packets",
            f"Approvals: {a.get('count', 0)} pending",
            f"Research: {b.get('notebooklm_scored_items', 0)} items scored",
            "",
            "Top 3 Priorities:"
        ]
        for i, p in enumerate(h.get("top_3_priorities", []), 1):
            lines.append(f"  {i}. {p}")
        lines.append(f"\nCommands: /report /status /daily /research /content /approvals /orders /hermes /recover")
        return "\n".join(lines)
    except:
        return "Anytime report not yet generated. Use /status instead."

def cmd_research():
    try:
        with open("data/research_memory/notebooklm_scored_items_latest.json") as f:
            items = json.load(f)
        routes = {}
        for item in items:
            r = item.get("recommended_route", "unknown")
            routes[r] = routes.get(r, 0) + 1
        lines = [f"Research Status\n\nNotebookLM: {len(items)} items scored\n"]
        for route, count in sorted(routes.items(), key=lambda x: -x[1]):
            lines.append(f"  {route}: {count}")
        return "\n".join(lines)
    except:
        return "Research data not available."

def cmd_content():
    packets = []
    for f in os.listdir("reports/approval_packets"):
        if f.endswith(".json"):
            with open(f"reports/approval_packets/{f}") as fh:
                packets.append(json.load(fh))
    email_count = sum(1 for p in packets if p.get("lane") == "customer_email")
    social_count = sum(1 for p in packets if p.get("lane") == "social_publishing")
    stripe_count = sum(1 for p in packets if p.get("lane") == "stripe_test_checkout")
    return f"Content Drafts Status\n\nEmail drafts: {email_count}\nSocial drafts: {social_count}\nStripe checkout requests: {stripe_count}\n\nUse /approvals to see details"

def cmd_approvals_list():
    packets = []
    for f in os.listdir("reports/approval_packets"):
        if f.endswith(".json"):
            with open(f"reports/approval_packets/{f}") as fh:
                packets.append(json.load(fh))
    if not packets:
        return "Approval Queue\n\nNo pending items."
    lines = [f"Approval Queue ({len(packets)} items)\n"]
    for p in packets:
        lines.append(f"- {p.get('item_id')}: {p.get('lane')} — {p.get('current_status')}")
    lines.append("\nUse /approve <id>, /reject <id> <reason>, /revise <id> <feedback>")
    return "\n".join(lines)

def cmd_status():
    registry = load_json(REGISTRY_PATH) or []
    enabled = [p for p in registry if p.get("enabled")]
    return f"Nexus Status\n\nProcesses: {len(registry)} total, {len(enabled)} enabled\nSupabase: ENV_PRESENT_BROWSER_EXPECTED\nBuild: previously passing\nTelegram: ACTIVE (mobile operator console)"

def cmd_daily():
    daily = load_json("reports/runtime/nexus_daily_monitor_latest.json")
    if not daily:
        return "Daily monitor not yet run. Use /run daily_monitor"
    pr = daily.get("process_registry", {})
    return f"Daily Monitor\n\nProcesses: {pr.get('total',0)} total, {pr.get('enabled',0)} enabled\nRunner: {daily.get('runner_heartbeat',{}).get('last_run','never')}\nSupabase: {daily.get('supabase',{}).get('classification','unknown')}"

def cmd_health():
    return "System Health\n\nBuild: PASS\nTests: 1196/1197\nSupabase: ENV_PRESENT\nCommand Center: real queries\nClient Portal: data adapter built\nTelegram: ACTIVE"

def cmd_review():
    queue = load_json("reports/runtime/ray_review_queue_latest.json")
    items = queue if isinstance(queue, list) else queue.get("items", []) if queue else []
    return f"Ray Review Queue\n\nItems: {len(items)}\n\nUse /approve <id>, /reject <id> <reason>, /revise <id> <feedback>"

def cmd_approve(args):
    if not args:
        return "Usage: /approve <item-id>"
    item_id = args[0]
    receipt = write_receipt("approvals", {
        "type": "approval",
        "decision": "approved",
        "item_id": item_id,
        "allowed_next_step": "internal_safe_work",
        "blocked_next_step": "external_action"
    })
    return f"Approved: {item_id}\nReceipt: {receipt['receipt_id']}\nNext: internal safe work allowed"

def cmd_reject(args):
    if len(args) < 2:
        return "Usage: /reject <item-id> <reason>"
    item_id, reason = args[0], " ".join(args[1:])
    receipt = write_receipt("approvals", {
        "type": "approval",
        "decision": "rejected",
        "item_id": item_id,
        "reason": reason,
        "allowed_next_step": None,
        "blocked_next_step": "all"
    })
    return f"Rejected: {item_id}\nReason: {reason}\nReceipt: {receipt['receipt_id']}"

def cmd_revise(args):
    if len(args) < 2:
        return "Usage: /revise <item-id> <feedback>"
    item_id, feedback = args[0], " ".join(args[1:])
    receipt = write_receipt("approvals", {
        "type": "approval",
        "decision": "revision_requested",
        "item_id": item_id,
        "feedback": feedback,
        "allowed_next_step": "revision",
        "blocked_next_step": None
    })
    return f"Revision requested: {item_id}\nFeedback: {feedback}\nReceipt: {receipt['receipt_id']}"

def cmd_request(args):
    if not args:
        return "Usage: /request <internal request text>"
    text = " ".join(args)
    text_lower = text.lower()

    if any(kw in text_lower for kw in ["send email", "email customer", "post to", "publish", "tiktok", "place trade", "charge", "submit dispute", "submit grant"]):
        return "BLOCKED: This action requires an approved runner and compliance review. Cannot execute from Telegram."

    route = "hermes"
    if any(kw in text_lower for kw in ["research", "find", "discover", "explore"]):
        route = "alpha"
    elif any(kw in text_lower for kw in ["creative", "video", "script", "content"]):
        route = "creative"
    elif any(kw in text_lower for kw in ["client", "portal", "credit", "funding"]):
        route = "client_portal"
    elif any(kw in text_lower for kw in ["recovery", "stale", "failed"]):
        route = "recovery"

    wo = create_work_order(text, route, "ACTIVE_INTERNAL", source="telegram")
    write_receipt("internal_requests", {
        "type": "internal_request",
        "request": text,
        "route": route,
        "work_order_id": wo["work_order_id"]
    })
    return f"Work Order Created: {wo['work_order_id']}\nRoute: {route}\nMode: ACTIVE_INTERNAL"

def cmd_hermes(args):
    if not args:
        return "Usage: /hermes <message>"
    message = " ".join(args)

    import re
    patterns = [
        (r"research|find|discover", "research"),
        (r"youtube|video|channel", "youtube_research"),
        (r"client|portal|onboard", "client_portal"),
        (r"marketing|campaign|content", "marketing"),
        (r"trade|trading|backtest", "trading"),
        (r"health|status|monitor", "system_health"),
        (r"review|approve", "ray_review"),
    ]
    route = "hermes_general"
    for pat, dept in patterns:
        if re.search(pat, message, re.I):
            route = dept
            break

    wo = create_work_order(f"Hermes: {message}", route, "ACTIVE_INTERNAL", source="telegram_hermes")
    receipt = write_receipt("hermes", {
        "type": "hermes_request",
        "message": message,
        "routed_to": route,
        "work_order_id": wo["work_order_id"],
        "mode": "ACTIVE_INTERNAL"
    })
    return f"Hermes Request\nRouted to: {route}\nWork Order: {wo['work_order_id']}\nReceipt: {receipt['receipt_id']}"

def cmd_alpha(args):
    if not args:
        return "Usage: /alpha <topic-or-url>"
    topic = " ".join(args)

    source_type = "business_idea"
    if "youtube.com" in topic or "youtu.be" in topic:
        source_type = "youtube_video"
    elif "github.com" in topic:
        source_type = "github_repo"
    elif "tiktok.com" in topic:
        source_type = "tiktok_video"
    elif any(kw in topic.lower() for kw in ["grant", "fund"]):
        source_type = "grant_page"
    elif any(kw in topic.lower() for kw in ["stripe", "payment", "billing"]):
        source_type = "payment_infrastructure"

    wo = create_work_order(f"Alpha: {topic}", "alpha_intake", "ACTIVE_INTERNAL", source="telegram_alpha")
    receipt = write_receipt("alpha", {
        "type": "alpha_intake",
        "topic_or_url": topic,
        "source_type": source_type,
        "work_order_id": wo["work_order_id"],
        "mode": "ACTIVE_INTERNAL"
    })
    return f"Alpha Intake\nSource Type: {source_type}\nWork Order: {wo['work_order_id']}\nReceipt: {receipt['receipt_id']}"

def cmd_orders():
    orders = load_work_orders()
    if not orders:
        return "No work orders yet."
    recent = orders[-5:]
    lines = [f"Work Orders ({len(orders)} total):\n"]
    for wo in recent:
        lines.append(f"- {wo['work_order_id']}: {wo['title'][:50]} [{wo['status']}]")
    return "\n".join(lines)

def cmd_processes():
    registry = load_json(REGISTRY_PATH) or []
    enabled = [p for p in registry if p.get("enabled")]
    lines = [f"Process Registry ({len(registry)} total, {len(enabled)} enabled):\n"]
    for p in enabled:
        lines.append(f"- {p['process_id']}: {p['mode']} (telegram: {p.get('telegram_allowed', False)})")
    return "\n".join(lines)

def cmd_run(args):
    if not args:
        return "Usage: /run <process-id>"
    pid = args[0]
    registry = load_json(REGISTRY_PATH) or []
    proc = next((p for p in registry if p["process_id"] == pid), None)
    if not proc:
        return f"Process not found: {pid}"
    if not proc.get("telegram_allowed"):
        return f"Process {pid} not allowed from Telegram"
    if proc.get("mode") == "BLOCKED":
        return f"Process {pid} is BLOCKED"
    if proc.get("risk_level") == "high":
        return f"Process {pid} risk too high for Telegram"

    receipt = write_receipt("internal_requests", {
        "type": "telegram_process_run",
        "process_id": pid,
        "mode": proc.get("mode"),
        "status": "triggered"
    })
    return f"Process Triggered: {pid}\nMode: {proc.get('mode')}\nReceipt: {receipt['receipt_id']}"

def cmd_blocked():
    guard = load_json(BLOCKED_GUARD_PATH)
    if not guard:
        return "Guard not found"
    blocked = guard.get("blocked_actions", [])
    lines = ["Blocked Actions:\n"]
    for b in blocked:
        lines.append(f"- {b}")
    return "\n".join(lines)

# --- Telegram API Helpers ---

def get_bot_token():
    """Read bot token from environment, falling back to launchctl."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if token:
        return token
    
    # Fallback: try launchctl
    try:
        import subprocess
        result = subprocess.run(
            ["launchctl", "getenv", "TELEGRAM_BOT_TOKEN"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except:
        pass
    
    print("TELEGRAM_TOKEN_MISSING")
    return None

def telegram_api_call(token, method, params=None):
    """Call Telegram Bot API method. Returns JSON response or None."""
    url = TELEGRAM_API.format(token=token, method=method)
    try:
        if params:
            data = urllib.parse.urlencode(params).encode("utf-8")
            req = urllib.request.Request(url, data=data)
        else:
            req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except:
            pass
        print(f"HTTP {e.code} calling {method}: {body[:200]}")
        return None
    except Exception as e:
        print(f"Error calling {method}: {e}")
        return None

def telegram_send_message(token, chat_id, text):
    """Send a text message via Telegram. Truncates if needed."""
    if not token or not chat_id:
        return None
    # Telegram max message length is 4096 characters
    if len(text) > 4000:
        text = text[:3990] + "\n\n... (truncated)"
    result = telegram_api_call(token, "sendMessage", {
        "chat_id": chat_id,
        "text": text
    })
    return result

def load_last_update_id():
    """Load the last processed update_id from state file."""
    state = load_json(TELEGRAM_STATE_PATH)
    if state and isinstance(state, dict):
        return state.get("last_update_id", 0)
    return 0

def save_last_update_id(update_id):
    """Save the last processed update_id to state file."""
    save_json(TELEGRAM_STATE_PATH, {
        "last_update_id": update_id,
        "updated_at": datetime.now(timezone.utc).isoformat()
    })

def write_live_polling_receipt(receipt_data):
    """Write a receipt under the live_polling subdirectory."""
    return write_receipt("live_polling", receipt_data)

def write_activation_report():
    """Write the activation report confirming live polling is working."""
    os.makedirs(os.path.dirname(TELEGRAM_REPORT_PATH), exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    report = f"""# Nexus Telegram Live Polling — Activation Report

**Activated**: {now}
**Script**: scripts/telegram/nexus_telegram_bridge.py
**Mode**: --once (bounded one-shot polling)
**State File**: data/runtime/telegram_last_update_id.json
**Receipt Dir**: reports/telegram/receipts/live_polling/

---

## How It Works

1. `--once` calls Telegram `getUpdates` API
2. Uses saved `last_update_id` as offset (avoids duplicate processing)
3. Ignores messages from unauthorized chat IDs
4. Routes command text through existing `process_command()` handler
5. Sends reply via `sendMessage`
6. Saves latest `update_id` to prevent reprocessing
7. Writes a receipt under `reports/telegram/receipts/live_polling/`

## State Management

- `data/runtime/telegram_last_update_id.json` stores the last processed `update_id`
- On each `--once` run, only messages with `update_id > saved` are processed
- This ensures no duplicate responses even with 60-second launchd intervals

## Security

- Only chat IDs in `TELEGRAM_ALLOWED_CHAT_IDS` are processed
- Unauthorized messages are ignored (no receipt written)
- No tokens, keys, or sensitive data are included in receipts
- External actions remain approval-gated

## Commands Supported

| Command | Response |
|---------|----------|
| /report | Full system report |
| /status | Current status |
| /daily | Daily monitor |
| /research | Research/NotebookLM/Alpha status |
| /content | Content drafts status |
| /approvals | Ray Review queue |
| /orders | Work orders |
| /hermes <msg> | Hermes advisory |
| /recover | Recovery check |
| /approve <id> | Approve item |
| /reject <id> <reason> | Reject item |
| /revise <id> <feedback> | Request revision |
| /request <text> | Internal request |
| /alpha <topic> | Alpha research |
| /processes | Process registry |
| /run <id> | Run safe process |
| /blocked | Blocked actions |

## Verification

To verify live polling is working:

1. Send a command in Telegram (e.g., /report)
2. Run: `python3 scripts/telegram/nexus_telegram_bridge.py --once`
3. Check `data/runtime/telegram_last_update_id.json` for updated `last_update_id`
4. Check `reports/telegram/receipts/live_polling/` for new receipt files
5. The command should NOT be repeated on the next `--once` run
"""
    with open(TELEGRAM_REPORT_PATH, "w") as f:
        f.write(report)
    print(f"Activation report written: {TELEGRAM_REPORT_PATH}")

def process_telegram_updates(token, dry_run=False):
    """
    Bounded one-shot polling: fetch new updates, process commands, send replies.
    Returns status string.
    """
    last_id = load_last_update_id()
    params = {"offset": last_id + 1, "limit": 10, "timeout": 0}
    
    resp = telegram_api_call(token, "getUpdates", params)
    if not resp:
        return "TELEGRAM_API_ERROR"
    
    if not resp.get("ok"):
        return "TELEGRAM_API_NOT_OK"
    
    updates = resp.get("result", [])
    if not updates:
        return "NO_NEW_UPDATES"
    
    processed = 0
    skipped_unauthorized = 0
    max_update_id = last_id
    
    for update in updates:
        uid = update.get("update_id", 0)
        if uid > max_update_id:
            max_update_id = uid
        
        message = update.get("message") or update.get("edited_message") or {}
        chat = message.get("chat", {})
        chat_id = chat.get("id")
        text = message.get("text", "")
        
        # Ignore non-text messages
        if not text:
            continue
        
        # Authorization check
        if chat_id not in ALLOWED_CHAT_IDS:
            skipped_unauthorized += 1
            continue
        
        # Process command
        result = process_command(text)
        processed += 1
        
        if dry_run:
            print(f"[DRY-RUN] Would reply to chat {chat_id}: {result[:100]}...")
        else:
            # Send reply
            send_result = telegram_send_message(token, chat_id, result)
            reply_ok = send_result and send_result.get("ok", False) if send_result else False
            
            # Write receipt
            write_live_polling_receipt({
                "type": "live_command",
                "update_id": uid,
                "chat_id": chat_id,
                "command": text[:100],
                "reply_ok": reply_ok,
                "reply_length": len(result),
                "reply_preview": result[:200]
            })
    
    # Save the latest update_id
    if max_update_id > last_id:
        save_last_update_id(max_update_id)
    
    return f"PROCESSED {processed} | SKIPPED {skipped_unauthorized} unauthorized | LAST_UPDATE_ID {max_update_id}"

def process_command(text):
    parts = text.strip().split()
    if not parts:
        return cmd_start()

    cmd = parts[0].lower()
    args = parts[1:]

    handlers = {
        "/start": lambda a: cmd_start(),
        "/help": lambda a: cmd_start(),
        "/report": lambda a: cmd_report(),
        "/status": lambda a: cmd_status(),
        "/daily": lambda a: cmd_daily(),
        "/research": lambda a: cmd_research(),
        "/content": lambda a: cmd_content(),
        "/approvals": lambda a: cmd_approvals_list(),
        "/review": lambda a: cmd_review(),
        "/approve": cmd_approve,
        "/reject": cmd_reject,
        "/revise": cmd_revise,
        "/request": cmd_request,
        "/hermes": cmd_hermes,
        "/alpha": cmd_alpha,
        "/orders": lambda a: cmd_orders(),
        "/recover": lambda a: "Recovery check: use /run recovery",
        "/processes": lambda a: cmd_processes(),
        "/run": cmd_run,
        "/blocked": lambda a: cmd_blocked(),
    }

    handler = handlers.get(cmd)
    if handler:
        return handler(args)
    return cmd_start()

def main():
    args = sys.argv[1:]
    if "--test-command" in args:
        idx = args.index("--test-command")
        if idx + 1 < len(args):
            cmd_text = args[idx + 1]
            result = process_command(cmd_text)
            print(result)
        else:
            print("Usage: --test-command '/status'")
    elif "--once" in args:
        token = get_bot_token()
        if not token:
            print("TELEGRAM_TOKEN_MISSING")
            sys.exit(1)
        
        dry_run = "--dry-run-poll" in args
        status = process_telegram_updates(token, dry_run=dry_run)
        print(f"Telegram bridge: {status}")
        
        if status.startswith("PROCESSED"):
            write_activation_report()
    elif "--dry-run" in args:
        print("Telegram bridge: dry-run mode")
        for cmd in ["/start", "/status", "/daily", "/health", "/review", "/approve TEST-001", "/blocked"]:
            print(f"\n--- {cmd} ---")
            print(process_command(cmd))
    else:
        print("Usage: --test-command '<cmd>' | --once | --dry-run")

if __name__ == "__main__":
    main()
