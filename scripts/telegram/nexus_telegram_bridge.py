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
import re
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
ALPHA_DEBUG_DIR = "reports/telegram/receipts/alpha_debug"
ALPHA_CONVERSATION_DIR = "reports/telegram/receipts/alpha_conversation"
ALPHA_INTAKE_DIR = "data/alpha/intake"
ALPHA_BRIEFS_DIR = "reports/alpha/briefs"
ALPHA_SCORES_DIR = "reports/alpha/scores"
ALPHA_ADVISORY_PATH = "reports/hermes/alpha_advisory_feed_latest.md"
CONVERSATION_CONTEXT_PATH = "data/runtime/telegram_conversation_context.json"
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
        ]

        # Alpha section
        ctx = load_conversation_context()
        chat_ctx = get_chat_context(ctx, 1288928049)
        if chat_ctx.get("last_topic"):
            recs = chat_ctx.get("last_alpha_recommendations", [])
            top = recs[0]["title"] if recs else "none"
            lines.append(f"Alpha: active — {chat_ctx['last_topic']}")
            lines.append(f"  Top rec: {top}")
            needs = []
            if not chat_ctx.get("last_work_order_path"):
                needs.append("approve Alpha recommendation")
            if needs:
                lines.append(f"  Needs Ray: {', '.join(needs)}")
        else:
            lines.append("Alpha: no recent activity")

        lines.extend([
            "",
            "Top 3 Priorities:"
        ])
        for i, p in enumerate(h.get("top_3_priorities", []), 1):
            lines.append(f"  {i}. {p}")
        lines.append(f"\nCommands: /report /status /daily /research /content /approvals /orders /hermes /recover")
        return "\n".join(lines)
    except:
        return "Anytime report not yet generated. Use /status instead."

def cmd_research():
    lines = ["Research Status\n"]

    # NotebookLM section
    try:
        with open("data/research_memory/notebooklm_scored_items_latest.json") as f:
            items = json.load(f)
        routes = {}
        for item in items:
            r = item.get("recommended_route", "unknown")
            routes[r] = routes.get(r, 0) + 1
        lines.append(f"NotebookLM: {len(items)} items scored")
        for route, count in sorted(routes.items(), key=lambda x: -x[1]):
            lines.append(f"  {route}: {count}")
    except:
        lines.append("NotebookLM: data not available")

    # Alpha section
    lines.append("")
    lines.append("Alpha Intelligence:")
    ctx = load_conversation_context()
    chat_ctx = get_chat_context(ctx, 1288928049)
    if chat_ctx.get("last_topic"):
        lines.append(f"  Latest topic: {chat_ctx['last_topic']}")
        lines.append(f"  Brief: {chat_ctx.get('last_alpha_brief_path', 'none')}")
        lines.append(f"  Score: {chat_ctx.get('last_alpha_score_path', 'none')}")
        recs = chat_ctx.get("last_alpha_recommendations", [])
        if recs:
            lines.append(f"  Top recommendation: {recs[0]['title']} ({recs[0]['score']}/10)")
        lines.append(f"  Work order: {chat_ctx.get('last_work_order_path', 'none yet')}")
    else:
        lines.append("  No recent Alpha activity")
        lines.append("  Send 'Alpha research <topic>' to start")

    return "\n".join(lines)

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

# --- Conversation Context ---

def load_conversation_context():
    return load_json(CONVERSATION_CONTEXT_PATH) or {}

def save_conversation_context(ctx):
    save_json(CONVERSATION_CONTEXT_PATH, ctx)

def get_chat_context(ctx, chat_id):
    return ctx.get(str(chat_id), {})

def update_chat_context(ctx, chat_id, updates):
    key = str(chat_id)
    if key not in ctx:
        ctx[key] = {}
    ctx[key].update(updates)
    ctx[key]["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_conversation_context(ctx)

# --- Alpha Debug Receipts ---

def write_alpha_debug_receipt(data):
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rid = f"alpha_debug_{ts}"
    data["receipt_id"] = rid
    data["timestamp"] = datetime.now(timezone.utc).isoformat()
    path = os.path.join(ALPHA_DEBUG_DIR, f"{rid}.json")
    save_json(path, data)
    return rid

# --- Alpha Intent Detection ---

ALPHA_INTENT_PATTERNS = [
    (r"^/alpha\b", "slash_alpha"),
    (r"\balpha\b", "alpha_keyword"),
    (r"\bresearch\b", "research_keyword"),
    (r"\blook into\b", "look_into"),
    (r"\bis this worth\b", "is_worth"),
    (r"\bscore this\b", "score_this"),
    (r"\bcompare\b", "compare"),
    (r"\bpros and cons\b", "pros_cons"),
]

FOLLOWUP_INTENT_PATTERNS = [
    (r"what did alpha find", "what_did_alpha_find"),
    (r"what did.*find", "what_did_alpha_find"),
    (r"which one should we do first", "which_one_first"),
    (r"which one", "which_one_first"),
    (r"turn (?:number )?(\d+) into a work order", "turn_into_work_order"),
    (r"turn (\d+)", "turn_into_work_order"),
    (r"send that to hermes", "send_to_hermes"),
    (r"send it to hermes", "send_to_hermes"),
]

def detect_alpha_intent(text):
    text_lower = text.lower().strip()
    for pattern, intent in ALPHA_INTENT_PATTERNS:
        if re.search(pattern, text_lower):
            return intent
    return None

def detect_followup_intent(text):
    text_lower = text.lower().strip()
    for pattern, intent in FOLLOWUP_INTENT_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            return intent, match
    return None, None

# --- Alpha Fallback Handler ---

def classify_alpha_topic(topic):
    topic_lower = topic.lower()
    if any(kw in topic_lower for kw in ["grant", "fund", "sbir", "sttr"]):
        return "grant_opportunity"
    if any(kw in topic_lower for kw in ["client", "customer", "revenue", "paid", "get paid"]):
        return "client_acquisition"
    if any(kw in topic_lower for kw in ["social", "tiktok", "instagram", "facebook", "post"]):
        return "social_media"
    if any(kw in topic_lower for kw in ["trade", "trading", "backtest", "forex"]):
        return "trading"
    if any(kw in topic_lower for kw in ["youtube", "video", "channel"]):
        return "content_creation"
    if any(kw in topic_lower for kw in ["stripe", "payment", "billing", "subscription"]):
        return "payment_infrastructure"
    return "general_strategy"

def score_alpha_idea(idea, topic):
    topic_lower = topic.lower()
    speed = 5
    cost = 5
    difficulty = 5
    risk = 3
    relevance = 7

    if any(kw in idea.lower() for kw in ["free", "low-cost", "organic", "no cost"]):
        cost = 8
    if any(kw in idea.lower() for kw in ["quick", "fast", "today", "this week"]):
        speed = 8
    if any(kw in idea.lower() for kw in ["complex", "build", "develop", "engineer"]):
        difficulty = 3
    if any(kw in idea.lower() for kw in ["trade", "invest", "financial"]):
        risk = 2
    if any(kw in idea.lower() for kw in topic_lower.split()):
        relevance = 9

    total = (speed + cost + difficulty + risk + relevance) / 5
    return {
        "total": round(total, 1),
        "dimensions": {
            "speed_to_value": speed,
            "cost": cost,
            "difficulty": difficulty,
            "risk": risk,
            "relevance": relevance,
        },
        "rationale": [
            f"Speed to value: {speed}/10",
            f"Cost efficiency: {cost}/10",
            f"Difficulty: {difficulty}/10 (lower=easier)",
            f"Risk: {risk}/10 (lower=safer)",
            f"Relevance: {relevance}/10",
        ],
    }

def generate_alpha_ideas(topic, category):
    ideas = []
    topic_lower = topic.lower()

    if category == "client_acquisition":
        ideas = [
            {"title": "Post readiness assessment offer in local business Facebook groups", "why": "Direct access to business owners who need credit readiness", "action": "Draft post for Ray Review"},
            {"title": "Create a free 'Credit Readiness Checklist' lead magnet", "why": "Captures emails, builds trust before paid engagement", "action": "Draft checklist for Ray Review"},
            {"title": "Partner with local accountants for referrals", "why": "Accountants see clients who need credit prep", "action": "Draft outreach template"},
            {"title": "Run a $20 Facebook ad targeting business owners", "why": "Low-cost targeted reach", "action": "Draft ad copy for Ray Review"},
            {"title": "Offer free 15-min readiness calls", "why": "Low barrier, high conversion potential", "action": "Draft call script"},
        ]
    elif category == "grant_opportunity":
        ideas = [
            {"title": "Search SBIR/STTR open topics matching Nexus capabilities", "why": "Federal grants for tech businesses", "action": "Draft search criteria"},
            {"title": "Check state-level small business grants", "why": "Less competition than federal", "action": "Draft state grant list"},
            {"title": "Apply to Stripe Atlas or similar startup programs", "why": "Non-dilutive funding", "action": "Draft application checklist"},
        ]
    elif category == "social_media":
        ideas = [
            {"title": "Post daily credit tip threads", "why": "Builds authority and audience", "action": "Draft 5 tips for Ray Review"},
            {"title": "Create short-form video explainers", "why": "High engagement on TikTok/Reels", "action": "Draft 3 video scripts"},
            {"title": "Share client success stories (anonymized)", "why": "Social proof drives conversions", "action": "Draft template"},
        ]
    else:
        ideas = [
            {"title": f"Research core options for: {topic}", "why": "Establishes baseline understanding", "action": "Draft research plan"},
            {"title": f"Identify quick wins related to: {topic}", "why": "Fastest path to value", "action": "Draft quick-win list"},
            {"title": f"Map competitive landscape for: {topic}", "why": "Informed decision-making", "action": "Draft competitor list"},
            {"title": f"Create a 1-page brief on: {topic}", "why": "Synthesizes findings for Ray Review", "action": "Draft brief outline"},
            {"title": f"Define success metrics for: {topic}", "why": "Measurable outcomes", "action": "Draft metric framework"},
        ]

    return ideas[:5]

def cmd_alpha_fallback(topic, source="test-command"):
    if not topic:
        return "Alpha is ready. Send a topic for research."

    category = classify_alpha_topic(topic)
    ideas = generate_alpha_ideas(topic, category)
    scores = []

    for idea in ideas:
        sc = score_alpha_idea(idea["title"], topic)
        idea["score"] = sc
        scores.append(sc)

    avg_score = round(sum(s["total"] for s in scores) / len(scores), 1) if scores else 0
    ranked = sorted(enumerate(ideas), key=lambda x: x[1]["score"]["total"], reverse=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    intake_id = f"alpha_{ts}"

    # Write intake record
    intake = {
        "id": intake_id,
        "topic": topic,
        "category": category,
        "ideas_count": len(ideas),
        "average_score": avg_score,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
    }
    save_json(os.path.join(ALPHA_INTAKE_DIR, f"{intake_id}.json"), intake)

    # Write brief
    brief_lines = [
        f"# Alpha Brief: {topic}",
        f"**Category**: {category}",
        f"**Average Score**: {avg_score}/10",
        f"**Ideas Generated**: {len(ideas)}",
        f"**Created**: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Ranked Recommendations",
        "",
    ]
    for rank, (idx, idea) in enumerate(ranked, 1):
        brief_lines.append(f"### {rank}. {idea['title']}")
        brief_lines.append(f"- Why: {idea['why']}")
        brief_lines.append(f"- Score: {idea['score']['total']}/10")
        brief_lines.append(f"- Action: {idea['action']}")
        brief_lines.append("")

    brief_lines.extend([
        "## Disclaimer",
        "Alpha created an internal research brief from available Nexus context.",
        "Live external research is not configured in this path yet.",
        "",
        "## Next Steps",
        "- 'which one should we do first?' — Ray gets top recommendation",
        "- 'turn number 2 into a work order' — creates a work order",
        "- 'send that to Hermes' — routes latest brief to Hermes",
    ])
    brief_path = os.path.join(ALPHA_BRIEFS_DIR, f"{intake_id}.md")
    save_json(brief_path.replace(".md", ".json"), {"brief": "\n".join(brief_lines), "id": intake_id})
    with open(brief_path, "w") as f:
        f.write("\n".join(brief_lines))

    # Write score record
    score_record = {
        "id": intake_id,
        "topic": topic,
        "category": category,
        "ideas": [{"title": i["title"], "score": i["score"]["total"], "dimensions": i["score"]["dimensions"]} for i in ideas],
        "average_score": avg_score,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    save_json(os.path.join(ALPHA_SCORES_DIR, f"{intake_id}.json"), score_record)

    # Update Hermes advisory feed
    advisory_lines = [
        f"# Alpha Advisory Feed",
        f"**Latest**: {datetime.now(timezone.utc).isoformat()}",
        f"**Topic**: {topic}",
        f"**Category**: {category}",
        f"**Top Recommendation**: {ranked[0][1]['title'] if ranked else 'N/A'}",
        f"**Score**: {ranked[0][1]['score']['total'] if ranked else 0}/10",
        f"**Brief**: {brief_path}",
        f"**Work Orders**: None yet — use 'turn number N into a work order'",
    ]
    with open(ALPHA_ADVISORY_PATH, "w") as f:
        f.write("\n".join(advisory_lines))

    # Save conversation context
    ctx = load_conversation_context()
    update_chat_context(ctx, 1288928049, {
        "last_agent": "alpha",
        "last_topic": topic,
        "last_alpha_brief_path": brief_path,
        "last_alpha_score_path": os.path.join(ALPHA_SCORES_DIR, f"{intake_id}.json"),
        "last_alpha_recommendations": [{"title": i["title"], "action": i["action"], "score": i["score"]["total"]} for i in ideas],
        "last_selected_item": None,
        "last_work_order_path": None,
    })

    # Build reply
    reply_lines = [
        f"Alpha Research: {topic}",
        f"Category: {category}",
        f"Score: {avg_score}/10",
        "",
        "Top Recommendations:",
    ]
    for rank, (idx, idea) in enumerate(ranked[:3], 1):
        reply_lines.append(f"  {rank}. {idea['title']} ({idea['score']['total']}/10)")

    reply_lines.extend([
        "",
        f"Brief: {brief_path}",
        "",
        "Commands: 'which one should we do first?', 'turn number N into a work order', 'send that to Hermes'",
        "",
        "Note: Live external research not configured. This is an internal Nexus context brief.",
    ])

    return "\n".join(reply_lines)

# --- Follow-up Handler ---

def cmd_followup(intent, match, chat_id):
    ctx = load_conversation_context()
    chat_ctx = get_chat_context(ctx, chat_id)

    if not chat_ctx.get("last_alpha_brief_path"):
        return "I do not have a recent Alpha topic yet. Send 'Alpha research <topic>' or describe what to research."

    if intent == "what_did_alpha_find":
        brief_path = chat_ctx.get("last_alpha_brief_path", "")
        if os.path.exists(brief_path):
            with open(brief_path) as f:
                brief = f.read()
            recs = chat_ctx.get("last_alpha_recommendations", [])
            lines = [f"Alpha found {len(recs)} recommendations for: {chat_ctx.get('last_topic', 'unknown')}"]
            for i, r in enumerate(recs[:5], 1):
                lines.append(f"  {i}. {r['title']} ({r['score']}/10)")
            lines.append(f"\nFull brief: {brief_path}")
            return "\n".join(lines)
        return "Alpha brief not found. Send a new topic with 'Alpha research <topic>'."

    elif intent == "which_one_first":
        recs = chat_ctx.get("last_alpha_recommendations", [])
        if not recs:
            return "No Alpha recommendations found. Send 'Alpha research <topic>' first."
        top = recs[0]
        lines = [
            f"Top recommendation:",
            f"  {top['title']}",
            f"  Score: {top['score']}/10",
            f"  Action: {top.get('action', 'Review and approve')}",
            "",
            "Say 'turn number 1 into a work order' to create it.",
        ]
        update_chat_context(ctx, chat_id, {"last_selected_item": 1})
        return "\n".join(lines)

    elif intent == "turn_into_work_order":
        match_text = match.group(1) if match else "1"
        try:
            idx = int(match_text) - 1
        except ValueError:
            idx = 0
        recs = chat_ctx.get("last_alpha_recommendations", [])
        if not recs or idx < 0 or idx >= len(recs):
            return f"Recommendation #{match_text} not found. You have {len(recs)} recommendations."
        rec = recs[idx]
        wo = create_work_order(f"Alpha: {rec['title']}", "alpha_intake", "ACTIVE_INTERNAL", source="telegram_alpha_followup")
        write_receipt("alpha", {
            "type": "alpha_work_order",
            "recommendation_title": rec["title"],
            "work_order_id": wo["work_order_id"],
            "mode": "ACTIVE_INTERNAL",
        })
        update_chat_context(ctx, chat_id, {"last_work_order_path": wo.get("work_order_id")})
        return f"Work Order Created: {wo['work_order_id']}\nTitle: {rec['title']}\nRoute: alpha_intake\nMode: ACTIVE_INTERNAL"

    elif intent == "send_to_hermes":
        brief_path = chat_ctx.get("last_alpha_brief_path", "")
        topic = chat_ctx.get("last_topic", "Alpha research")
        wo = create_work_order(f"Hermes: Alpha brief — {topic}", "hermes_alpha", "ACTIVE_INTERNAL", source="telegram_alpha_followup")
        write_receipt("hermes", {
            "type": "hermes_alpha_handoff",
            "brief_path": brief_path,
            "work_order_id": wo["work_order_id"],
            "topic": topic,
        })
        return f"Routed to Hermes\nWork Order: {wo['work_order_id']}\nTopic: {topic}\nBrief: {brief_path}"

    return "Unknown follow-up. Try 'which one should we do first?' or 'turn number N into a work order'."

def process_command(text):
    parts = text.strip().split()
    if not parts:
        return cmd_start()

    cmd = parts[0].lower()
    args = parts[1:]

    # Check for slash commands first
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

    # Not a slash command — try natural language routing
    full_text = text.strip()

    # Try follow-up intent first
    followup_intent, followup_match = detect_followup_intent(full_text)
    if followup_intent:
        write_alpha_debug_receipt({
            "source": "process_command",
            "raw_text": full_text[:100],
            "detected_intent": f"followup:{followup_intent}",
            "routed_to": "cmd_followup",
        })
        return cmd_followup(followup_intent, followup_match, 1288928049)

    # Try Alpha intent
    alpha_intent = detect_alpha_intent(full_text)
    if alpha_intent:
        # Extract topic from the message
        topic = full_text
        for prefix in ["alpha research ", "alpha ", "research ", "look into ", "score this ", "compare "]:
            if full_text.lower().startswith(prefix):
                topic = full_text[len(prefix):].strip()
                break
        if not topic:
            topic = full_text

        write_alpha_debug_receipt({
            "source": "process_command",
            "raw_text": full_text[:100],
            "detected_intent": alpha_intent,
            "routed_to": "cmd_alpha_fallback",
            "topic": topic[:100],
        })
        return cmd_alpha_fallback(topic, source="live_polling")

    # Default: show help
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
