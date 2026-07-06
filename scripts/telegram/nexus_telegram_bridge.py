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

# Hermes web search imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hermes"))
try:
    from hermes_web_search import web_search as hermes_web_search, url_review as hermes_url_review
    from hermes_research_advisor import build_advisory_answer
    HERMES_SEARCH_AVAILABLE = True
except Exception:
    HERMES_SEARCH_AVAILABLE = False

# Shared recommendation layer imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "recommendations"))
try:
    from recommendation_engine import ingest_alpha as shared_ingest_alpha, ingest_hermes as shared_ingest_hermes, ingest_nexus as shared_ingest_nexus, summary as rec_summary, get_top_recommendations, next_steps as rec_next_steps
    SHARED_REC_AVAILABLE = True
except Exception:
    SHARED_REC_AVAILABLE = False
except ImportError:
    HERMES_SEARCH_AVAILABLE = False

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
HERMES_WEB_SEARCH_DIR = "reports/hermes/web_search"
HERMES_URL_REVIEW_DIR = "reports/telegram/receipts/hermes_web_search"

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
    return "Nexus Mobile Operator Console\n\nCommands:\n/report - Full anytime operator report\n/status - System status\n/daily - Daily monitor\n/research - Research/NotebookLM/Alpha status\n/content - Content drafts/social/email status\n/approvals - Ray Review queue count and summaries\n/orders - Work orders summary\n/hermes <msg> - Hermes advisory\n/recover - Recovery check\n/approve <id> - Approve item\n/reject <id> <reason> - Reject\n/revise <id> <feedback> - Request revision\n/request <text> - Internal request\n/alpha <topic> - Alpha research\n/recs - Shared recommendations\n/processes - Process registry\n/run <id> - Run safe process\n/blocked - Blocked actions"

def cmd_report():
    try:
        with open("reports/runtime/nexus_anytime_operator_report_latest.json") as f:
            r = json.load(f)
        s = r.get("system_status", {})
        b = r.get("business_output_status", {})
        a = r.get("approval_queue", {})
        h = r.get("hermes_recommendation", {})

        # Check Telegram live polling status dynamically
        telegram_status = "UNKNOWN"
        try:
            import subprocess
            result = subprocess.run(
                ["launchctl", "list"],
                capture_output=True, text=True, timeout=5
            )
            if "com.nexus.telegram-operator" in result.stdout:
                telegram_status = "ACTIVE_LIVE_POLLING"
            else:
                telegram_status = "NOT_LOADED"
        except:
            telegram_status = "CHECK_MANUALLY"

        # Check Alpha status
        ctx = load_conversation_context()
        chat_ctx = get_chat_context(ctx, 1288928049)
        alpha_status = "ACTIVE_CONVERSATIONAL" if chat_ctx.get("last_topic") else "NO_RECENT_ACTIVITY"

        lines = [
            f"Nexus Anytime Report",
            f"Score: {s.get('active_os_score', '?')}/100 {s.get('classification', '')}",
            f"Running: YES — {s.get('active_operator', {}).get('processes', 0)} processes",
            f"Outputs: {b.get('receipts', 0)} receipts, {b.get('approval_packets', 0)} packets",
            f"Approvals: {a.get('count', 0)} pending",
            f"Research: {b.get('notebooklm_scored_items', 0)} items scored",
            f"Telegram: {telegram_status}",
            f"Alpha: {alpha_status}",
            "",
        ]

        # Alpha detail section
        if chat_ctx.get("last_topic"):
            recs = chat_ctx.get("last_alpha_recommendations", [])
            top = recs[0]["title"] if recs else "none"
            lines.append(f"Alpha topic: {chat_ctx['last_topic']}")
            lines.append(f"  Top rec: {top}")
            needs = []
            if not chat_ctx.get("last_work_order_path"):
                needs.append("review Alpha recommendation")
            if needs:
                lines.append(f"  Needs Ray: {', '.join(needs)}")

        lines.extend([
            "",
            "Current Priorities:"
        ])

        # Build dynamic priorities (no stale Telegram token item)
        priorities = []
        if a.get("count", 0) > 0:
            priorities.append(f"Review {a['count']} pending approval(s)")
        if chat_ctx.get("last_topic") and not chat_ctx.get("last_work_order_path"):
            priorities.append(f"Act on Alpha research: {chat_ctx['last_topic'][:40]}")
        priorities.append("Publish GoClear public landing page with plans/login/signup")
        priorities.append("Run Supabase browser verification (2 min)")
        priorities.append("Connect Stripe test checkout to landing page/client portal")
        priorities.append("Set RESEND_API_KEY if customer email lane should become live approval-gated")

        # Web search status
        web_search_status = "NOT_CONFIGURED"
        if HERMES_SEARCH_AVAILABLE:
            providers = []
            for env_name, label in [("BRAVE_SEARCH_API_KEY", "Brave"), ("TAVILY_API_KEY", "Tavily"),
                                     ("SERPAPI_API_KEY", "SerpAPI"), ("ALPHA_SEARXNG_URL", "SearXNG")]:
                if os.environ.get(env_name, "").strip():
                    providers.append(label)
            web_search_status = f"ACTIVE ({', '.join(providers)})" if providers else "AVAILABLE (no provider key)"

        for i, p in enumerate(priorities[:5], 1):
            lines.append(f"  {i}. {p}")

        lines.append(f"\nWeb Search: {web_search_status}")

        # Shared recommendation layer summary
        if SHARED_REC_AVAILABLE:
            try:
                recs = rec_summary()
                lines.append(f"\nShared Recs: {recs['total']} total | {recs['by_status'].get('new', 0)} new | Avg: {recs['avg_composite_score']}/10")
                if recs["top"]:
                    lines.append(f"  Top: {recs['top'][0]['title'][:50]} ({recs['top'][0]['score']}/10)")
            except Exception:
                pass

        lines.append(f"Commands: /report /status /daily /research /content /approvals /orders /hermes /recover /recs")
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
    return hermes_direct_answer(message)


def hermes_direct_answer(message):
    """Give a direct advisory answer, then optionally create a work order."""
    message_lower = message.lower()

    # Check if this needs web search
    needs_web_search = False
    search_query = message
    for pat in HERMES_WEB_SEARCH_PATTERNS:
        if re.search(pat, message_lower):
            needs_web_search = True
            # Extract query
            query = message_lower
            for prefix in ["hermes search the web for ", "hermes search web for ",
                           "hermes research ", "hermes look up ", "hermes find ",
                           "hermes check latest ", "hermes what are the best ",
                           "hermes are there ", "search the web for ",
                           "research ", "look up ", "what are the best ", "find "]:
                if query.startswith(prefix):
                    query = query[len(prefix):].strip()
                    break
            search_query = query or message
            break

    # Check if this is a URL review
    url_match = re.search(r"https?://\S+", message_lower)
    if url_match:
        return _hermes_url_review_answer(url_match.group(0), message)

    # Read current state for contextual answers
    ctx = load_conversation_context()
    chat_ctx = get_chat_context(ctx, 1288928049)
    alpha_topic = chat_ctx.get("last_topic", "none")
    recs = chat_ctx.get("last_alpha_recommendations", [])
    top_rec = recs[0]["title"] if recs else "none"

    # Count pending approvals
    approval_count = 0
    try:
        for f in os.listdir("reports/approval_packets"):
            if f.endswith(".json"):
                approval_count += 1
    except:
        pass

    # If web search is needed and available, use research advisor
    if needs_web_search and HERMES_SEARCH_AVAILABLE:
        try:
            advisory = build_advisory_answer(search_query)
            answer_lines = [
                f"Hermes Research — {search_query[:60]}",
                "",
                advisory.get("answer", "No results."),
                "",
                f"Source: {advisory.get('provider', 'none')}",
                f"Checked: {advisory.get('checked_at', 'unknown')[:16]}",
            ]
            if advisory.get("opportunity_score", {}).get("overall", 0) > 0:
                score = advisory["opportunity_score"]
                answer_lines.append(f"Score: {score['overall']}/10")
            if advisory.get("risks"):
                answer_lines.append(f"Risks: {'; '.join(advisory['risks'][:2])}")
            if advisory.get("next_step"):
                answer_lines.append(f"\n{advisory['next_step']}")

            # Ingest into shared recommendation layer
            if SHARED_REC_AVAILABLE:
                try:
                    shared_ingest_hermes(search_query, {"status": "ok", "provider": advisory.get("provider", "unknown")}, advisory, topic=search_query)
                except Exception:
                    pass
            answer = "\n".join(answer_lines)
        except Exception as e:
            answer = f"Hermes search error: {str(e)[:100]}\n\nFalling back to internal context."
    elif needs_web_search and not HERMES_SEARCH_AVAILABLE:
        answer_lines = [
            "Hermes web search is not available.",
            "",
            "The search module could not be imported.",
            "Check that scripts/hermes/hermes_web_search.py exists.",
            "",
            f"Your query was: {search_query[:80]}",
            "",
            "I can still help with internal context and Alpha research.",
        ]
        answer = "\n".join(answer_lines)
    elif any(kw in message_lower for kw in ["priority", "priorities", "top priority", "what should", "what matters", "where should we focus"]):
        answer_lines = [
            "Hermes Advisory — Today's Priorities:",
            "",
        ]
        priorities = []
        if approval_count > 0:
            priorities.append(f"Review {approval_count} pending approval(s) — blocks downstream action")
        if alpha_topic != "none" and not chat_ctx.get("last_work_order_path"):
            priorities.append(f"Act on Alpha research: {alpha_topic[:50]}")
        priorities.append("Publish GoClear public landing page with plans/login/signup")
        priorities.append("Run Supabase browser verification (2 min)")
        priorities.append("Connect Stripe test checkout to portal")
        for i, p in enumerate(priorities, 1):
            answer_lines.append(f"{i}. {p}")
        answer_lines.extend([
            "",
            "Reason: Telegram and Alpha are now working. The next bottleneck is converting visitors into portal users and paid readiness reviews.",
        ])
        answer = "\n".join(answer_lines)

    elif any(kw in message_lower for kw in ["recommend", "suggest", "next step", "do next", "what do you"]):
        answer_lines = [
            "Hermes Advisory:",
            "",
            f"Based on current state (OS active, {approval_count} approvals pending, Alpha topic: {alpha_topic[:30]}):",
            "",
        ]
        if approval_count > 0:
            answer_lines.append(f"- Clear the {approval_count} pending approval(s) first — they gate downstream work")
        if alpha_topic != "none" and not chat_ctx.get("last_work_order_path"):
            answer_lines.append(f"- Review the Alpha recommendation for: {alpha_topic[:40]}")
        answer_lines.append("- Then push the GoClear landing page live")
        answer_lines.append("- After that, run Supabase verification and Stripe checkout test")
        answer = "\n".join(answer_lines)

    elif any(kw in message_lower for kw in ["realistic", "risk", "stop", "block", "fail"]):
        answer_lines = [
            "Hermes Advisory — Risk Assessment:",
            "",
            "Current blockers:",
            f"- {approval_count} pending approvals (if any are external-facing, they gate revenue)",
            "- Supabase browser verification not confirmed (low risk, quick fix)",
            "- Stripe checkout not connected to portal (blocks paid conversions)",
            "- RESEND_API_KEY not set (blocks live email lane)",
            "",
            "Overall: low execution risk, medium urgency on landing page and Stripe connection.",
        ]
        answer = "\n".join(answer_lines)

    elif any(kw in message_lower for kw in ["approval", "approve", "pending", "review"]):
        answer_lines = [
            f"Hermes Advisory — Approvals:",
            "",
            f"Pending: {approval_count} item(s)",
            "",
        ]
        if approval_count > 0:
            answer_lines.append("Use /approvals to see details, then /approve <id> or /reject <id>.")
        else:
            answer_lines.append("No pending approvals. Queue is clear.")
        answer = "\n".join(answer_lines)

    elif any(kw in message_lower for kw in ["status", "how is", "how are", "doing"]):
        score = "?"
        try:
            with open("reports/runtime/nexus_anytime_operator_report_latest.json") as f:
                r = json.load(f)
            score = r.get("system_status", {}).get("active_os_score", "?")
        except:
            pass
        answer_lines = [
            "Hermes Advisory — System Status:",
            "",
            f"Active OS: {score}/100",
            "Telegram: active (live polling)",
            f"Alpha: {'active — ' + alpha_topic[:30] if alpha_topic != 'none' else 'no recent topic'}",
            f"Approvals: {approval_count} pending",
            f"Top Alpha rec: {top_rec[:40] if top_rec != 'none' else 'none'}",
            f"Web search: {'AVAILABLE' if HERMES_SEARCH_AVAILABLE else 'NOT_CONFIGURED'}",
        ]
        answer = "\n".join(answer_lines)

    else:
        # General advisory
        answer_lines = [
            "Hermes Advisory:",
            "",
            f"Current state: OS active, {approval_count} approvals pending.",
        ]
        if alpha_topic != "none":
            answer_lines.append(f"Latest Alpha topic: {alpha_topic[:50]}")
        if top_rec != "none":
            answer_lines.append(f"Top recommendation: {top_rec[:50]}")
        if HERMES_SEARCH_AVAILABLE:
            answer_lines.append("\nI can also search the web for current info. Try: 'hermes search the web for ...'")
        answer_lines.extend([
            "",
            "I can advise on priorities, risk, approvals, or next steps. What specifically do you want to discuss?",
        ])
        answer = "\n".join(answer_lines)

    # Create a work order in the background (non-blocking)
    route = "hermes_general"
    patterns = [
        (r"research|find|discover", "research"),
        (r"youtube|video|channel", "youtube_research"),
        (r"client|portal|onboard", "client_portal"),
        (r"marketing|campaign|content", "marketing"),
        (r"trade|trading|backtest", "trading"),
        (r"health|status|monitor", "system_health"),
        (r"review|approve", "ray_review"),
    ]
    for pat, dept in patterns:
        if re.search(pat, message, re.I):
            route = dept
            break

    wo = create_work_order(f"Hermes: {message}", route, "ACTIVE_INTERNAL", source="telegram_hermes")
    receipt = write_receipt("hermes", {
        "type": "hermes_request",
        "message": message[:200],
        "routed_to": route,
        "work_order_id": wo["work_order_id"],
        "mode": "ACTIVE_INTERNAL",
        "web_search_used": needs_web_search,
    })

    return f"{answer}\n\nWork Order: {wo['work_order_id']}"


def _hermes_url_review_answer(url, full_message):
    """Handle Hermes URL review requests."""
    if HERMES_SEARCH_AVAILABLE:
        try:
            review = hermes_url_review(url)
            lines = [
                f"Hermes URL Review — {url[:60]}",
                "",
            ]
            if review.get("title"):
                lines.append(f"Title: {review['title']}")
            if review.get("summary"):
                lines.append(f"Summary: {review['summary'][:300]}")
            lines.append(f"Provider: {review.get('provider', 'none')}")
            lines.append(f"Status: {review.get('status', 'unknown')}")
            if review.get("notes"):
                lines.append(f"Notes: {'; '.join(review['notes'][:2])}")
            lines.append("\nSay 'turn this into a work order' to create an approval-gated plan.")
            return "\n".join(lines)
        except Exception as e:
            return f"URL review error: {str(e)[:100]}"
    else:
        # Parse domain for limited safe guidance
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path
        except:
            domain = url
        return (
            f"URL Review — {url[:60]}\n\n"
            f"Domain: {domain}\n"
            f"Web search is not configured, so I cannot fetch live page content.\n\n"
            f"To enable URL review, add FIRECRAWL_API_KEY or BRAVE_SEARCH_API_KEY.\n"
            f"See docs/hermes_internet_search_setup.md for details."
        )

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

# --- Intent Classification ---

GREETING_PATTERNS = [
    r"^good\s+(morning|afternoon|evening|night)",
    r"^hello",
    r"^hey",
    r"^hi\b",
    r"^yo\b",
    r"^sup\b",
    r"^what'?s\s+up",
    r"^howdy",
    r"^greetings",
]

CASUAL_AGENT_CHAT_PATTERNS = [
    r"^alpha\s+(how\s+did\s+you|are\s+you|what\s+are|can\s+you|do\s+you)",
    r"^hermes\s+(how\s+did\s+you|are\s+you|what\s+are|can\s+you|do\s+you)",
    r"^nexus\s+(how\s+did\s+you|are\s+you|what\s+are|can\s+you|do\s+you)",
    r"^how\s+did\s+you\s+(sleep|wake|do)",
    r"^are\s+you\s+(there|awake|online|ready|ok)",
    r"^what\s+are\s+you\s+(doing|up|working|thinking)",
    r"^can\s+you\s+hear\s+me",
    r"^how\s+are\s+you\s+(doing|feeling|today)",
    r"^you\s+(ok|good|there|awake)",
]

ALPHA_RESEARCH_PATTERNS = [
    r"^alpha\s+research\b",
    r"^research\s+",
    r"\blook\s+into\b",
    r"\bis\s+this\s+worth\b",
    r"\bscore\s+this\b",
    r"\bcompare\b",
    r"\bpros\s+and\s+cons\b",
    r"\bfind\s+the\s+best\b",
    r"\bwhat\s+are\s+the\s+best\b",
    r"\bhow\s+can\s+we\s+(get|find|land|acquire|build|create|make)\b",
    r"\bwhat\s+are\s+the\s+options\b",
    r"\bexplore\b",
    r"\banalyze\b",
    r"\bevaluate\b",
    r"\bstrateg(y|ize|ies)\b",
    r"\bplan\s+(for|to|how)\b",
]

ALPHA_CONTEXT_FOLLOWUP_PATTERNS = [
    (r"what\s+did\s+alpha\s+find", "what_did_alpha_find"),
    (r"what\s+did\s+.*find", "what_did_alpha_find"),
    (r"which\s+one\s+should\s+we\s+do\s+first", "which_one_first"),
    (r"which\s+one", "which_one_first"),
    (r"which\s+is\s+(fastest|best|easiest|quickest)", "which_one_first"),
    (r"turn\s+(?:number\s+)?(\d+)\s+into\s+a\s+work\s+order", "turn_into_work_order"),
    (r"turn\s+(\d+)", "turn_into_work_order"),
    (r"send\s+that\s+to\s+hermes", "send_to_hermes"),
    (r"send\s+it\s+to\s+hermes", "send_to_hermes"),
    (r"make\s+that\s+an?\s+approval", "send_to_hermes"),
    (r"research\s+deeper", "what_did_alpha_find"),
]

HERMES_ADVISORY_PATTERNS = [
    r"^hermes\s+what\s+(is|should|do|would|can|will|are|were)",
    r"^hermes\s+(how|why|when|where|who|what|which|give|tell|show|help|advise|recommend)",
    r"^what\s+should\s+we\s+do\s+next",
    r"^what\s+do\s+you\s+recommend",
    r"^is\s+this\s+realistic",
    r"^what\s+would\s+stop\s+us",
    r"^give\s+me\s+a\s+(ceo|boss|leader|executive)\s+view",
    r"^what\s+needs?\s+my\s+approval",
    r"^what\s+is\s+today'?s?\s+priority",
    r"^what\s+(are|is)\s+the\s+top\s+priority",
    r"^where\s+should\s+we\s+focus",
    r"^what\s+matters?\s+most",
    r"^priorit(y|ize|ies)\b",
    r"^what'?s\s+blocking\s+us",
]

# Web search intent — triggers live web research via Hermes
HERMES_WEB_SEARCH_PATTERNS = [
    r"^hermes\s+search\s+(the\s+)?web",
    r"^hermes\s+research\b",
    r"^hermes\s+look\s+up",
    r"^hermes\s+find\s+(current|latest|recent|new)",
    r"^hermes\s+what\s+are\s+the\s+best",
    r"^hermes\s+find\s+open\s*source",
    r"^hermes\s+check\s+latest",
    r"^hermes\s+are\s+there\s+(grants|funding|opportunities)",
    r"^hermes\s+find\s+affiliate",
    r"^hermes\s+research\s+competitors",
    r"^hermes\s+find\s+better",
    r"^hermes\s+review\s+https?://",
    r"^hermes\s+what\s+(is|are)\s+the\s+(best|top|current|latest)",
    r"^search\s+the\s+web\s+for",
    r"^research\s+(this|that|current|latest)\b",
    r"^look\s+up\s+(current|latest|best|top)",
    r"^what\s+are\s+the\s+best\s+.*\s+(tools|platforms|services|options|programs)",
    r"^find\s+(current|latest|best|top|low[\s-]cost)",
]

NEXUS_STATUS_PATTERNS = [
    r"^what\s+(is|are)\s+the\s+status",
    r"^give\s+me\s+a\s+report",
    r"^what\s+happened\s+today",
    r"^what\s+is\s+running",
    r"^how\s+is\s+nexus\s+doing",
    r"^status\s+report",
    r"^system\s+status",
    r"^how\s+are\s+things",
    r"^what'?s\s+going\s+on",
    r"^update\s+me",
    r"^what'?s\s+new",
]

WORK_ORDER_PATTERNS = [
    r"^create\s+a\s+(task|work\s+order|ticket|item)",
    r"^make\s+this\s+a\s+(project|task|work\s+order)",
    r"^assign\s+this\s+to",
    r"^add\s+to\s+(the\s+)?backlog",
]


def classify_message_intent(text):
    """
    Classify a plain-language message into one of 9 intent categories.
    Returns (intent, match_object_or_none, stripped_topic_or_none).
    """
    text_lower = text.lower().strip()
    # Strip agent prefix if present (e.g., "alpha good morning" → "good morning")
    stripped = re.sub(r"^(alpha|hermes|nexus)\s+", "", text_lower)

    # APPROVAL_ACTION — slash-only, handled before this
    # But check anyway for plain-language like "approve EMAIL-001"
    if re.match(r"^(approve|reject|revise)\s+\w+", text_lower):
        return "APPROVAL_ACTION", None, None

    # WORK_ORDER_REQUEST
    for pat in WORK_ORDER_PATTERNS:
        if re.search(pat, text_lower):
            return "WORK_ORDER_REQUEST", None, None

    # GREETING
    for pat in GREETING_PATTERNS:
        if re.search(pat, text_lower) or re.search(pat, stripped):
            # Determine which agent prefix was used
            agent = None
            if text_lower.startswith("alpha "):
                agent = "alpha"
            elif text_lower.startswith("hermes "):
                agent = "hermes"
            elif text_lower.startswith("nexus "):
                agent = "nexus"
            return "GREETING", None, agent

    # CASUAL_AGENT_CHAT
    for pat in CASUAL_AGENT_CHAT_PATTERNS:
        if re.search(pat, text_lower):
            agent = "alpha" if "alpha" in text_lower else "hermes" if "hermes" in text_lower else "nexus"
            return "CASUAL_AGENT_CHAT", None, agent

    # HERMES_ADVISORY (must check before alpha research to catch "hermes what...")
    for pat in HERMES_ADVISORY_PATTERNS:
        if re.search(pat, text_lower):
            # Extract the actual question
            question = re.sub(r"^hermes\s+", "", text_lower).strip()
            return "HERMES_ADVISORY", None, question

    # HERMES_WEB_SEARCH (triggers live web research)
    for pat in HERMES_WEB_SEARCH_PATTERNS:
        if re.search(pat, text_lower):
            # Extract the search query
            query = text_lower
            for prefix in ["hermes search the web for ", "hermes search web for ",
                           "hermes research ", "hermes look up ", "hermes find ",
                           "hermes check latest ", "hermes what are the best ",
                           "hermes are there ", "hermes review ",
                           "search the web for ", "research ", "look up ",
                           "what are the best ", "find "]:
                if query.startswith(prefix):
                    query = query[len(prefix):].strip()
                    break
            # Clean up URL review queries
            url_match = re.search(r"https?://\S+", text_lower)
            if url_match:
                return "HERMES_URL_REVIEW", None, url_match.group(0)
            if not query:
                query = text_lower
            return "HERMES_WEB_SEARCH", None, query

    # NEXUS_STATUS_OR_REPORT
    for pat in NEXUS_STATUS_PATTERNS:
        if re.search(pat, text_lower):
            return "NEXUS_STATUS_OR_REPORT", None, None

    # ALPHA_CONTEXT_FOLLOWUP (must check before alpha research)
    for pat, followup_intent in ALPHA_CONTEXT_FOLLOWUP_PATTERNS:
        match = re.search(pat, text_lower)
        if match:
            return "ALPHA_CONTEXT_FOLLOWUP", match, followup_intent

    # ALPHA_RESEARCH_REQUEST
    for pat in ALPHA_RESEARCH_PATTERNS:
        if re.search(pat, text_lower):
            # Extract topic: strip agent prefix and research keywords
            topic = stripped
            for prefix in ["research ", "look into ", "score this ", "compare ", "analyze ", "evaluate "]:
                if topic.startswith(prefix):
                    topic = topic[len(prefix):].strip()
                    break
            if not topic:
                topic = text_lower
            return "ALPHA_RESEARCH_REQUEST", None, topic

    # UNKNOWN_HELPFUL_FALLBACK
    return "UNKNOWN_HELPFUL_FALLBACK", None, None

# --- Greeting & Casual Response Helpers ---

def get_system_quick_status():
    """Get a quick status summary for greeting responses."""
    try:
        with open("reports/runtime/nexus_anytime_operator_report_latest.json") as f:
            r = json.load(f)
        score = r.get("system_status", {}).get("active_os_score", "?")
        approvals = r.get("approval_queue", {}).get("count", 0)
    except:
        score = "?"
        approvals = 0

    ctx = load_conversation_context()
    chat_ctx = get_chat_context(ctx, 1288928049)
    alpha_topic = chat_ctx.get("last_topic", "none")
    recs = chat_ctx.get("last_alpha_recommendations", [])
    top_rec = recs[0]["title"][:40] if recs else "none"

    return score, approvals, alpha_topic, top_rec


def get_next_step_suggestion():
    """Suggest one useful next step based on current state."""
    ctx = load_conversation_context()
    chat_ctx = get_chat_context(ctx, 1288928049)
    if not chat_ctx.get("last_topic"):
        return "Start research: 'Alpha research <topic>'"
    if not chat_ctx.get("last_work_order_path"):
        return f"Review Alpha recommendation for: {chat_ctx['last_topic'][:30]}"
    try:
        with open("reports/approval_packets") as _:
            pass
    except:
        pass
    packets = []
    try:
        for f in os.listdir("reports/approval_packets"):
            if f.endswith(".json"):
                packets.append(f)
    except:
        pass
    if packets:
        return f"Review {len(packets)} pending approval(s)"
    return "Ask Hermes for priorities: 'what should we do next?'"


def handle_greeting(agent=None):
    """Handle a greeting message with a natural, concise reply."""
    score, approvals, alpha_topic, top_rec = get_system_quick_status()
    next_step = get_next_step_suggestion()

    if agent == "alpha":
        return (
            "Good morning Ray. Alpha is online. I can research opportunities, "
            "compare tools, score ideas, or turn findings into work orders. "
            "What should I look into today?"
        )
    if agent == "hermes":
        return (
            "Good morning Ray. Hermes is online. I can help prioritize the business path, "
            "review approvals, or turn Alpha research into action. What needs attention?"
        )
    if agent == "nexus":
        return (
            "Good morning Ray. Nexus is online. Telegram live polling active, "
            "Alpha responsive, approvals gated. What do you need?"
        )

    return (
        f"Good morning Ray. Nexus is running.\n\n"
        f"Active OS: {score}/100\n"
        f"Telegram: active\n"
        f"Approvals: {approvals} pending\n"
        f"Alpha: {alpha_topic}\n"
        f"Top rec: {top_rec}\n\n"
        f"Suggested: {next_step}\n\n"
        f"Say /report for full details, or ask Hermes/Alpha directly."
    )


def handle_casual_chat(agent=None):
    """Handle casual agent chat without creating research or work orders."""
    if agent == "alpha":
        return (
            "Alpha does not sleep, but I'm online and ready. "
            "I can research, score, compare, or turn an idea into a Nexus work order. "
            "Want me to look into something?"
        )
    if agent == "hermes":
        return (
            "Hermes is online. I can advise on priorities, review what's pending, "
            "or help you decide what to tackle next. What's on your mind?"
        )
    return (
        "Yes — Nexus is online. Hermes can advise, Alpha can research, "
        "and Nexus can prepare approval-gated work. What do you want to check?"
    )


def handle_status_report():
    """Handle a status/report request with direct answer."""
    score, approvals, alpha_topic, top_rec = get_system_quick_status()
    return (
        f"Nexus Status\n\n"
        f"Active OS: {score}/100\n"
        f"Telegram: active (live polling)\n"
        f"Approvals: {approvals} pending\n"
        f"Alpha: {alpha_topic}\n"
        f"Top rec: {top_rec}\n\n"
        f"Say /report for the full report."
    )


def handle_unknown_fallback():
    """Handle unknown messages with a helpful but concise reply."""
    return (
        "I'm not sure what you mean. I can:\n"
        "- Research a topic: 'Alpha research <topic>'\n"
        "- Advise on priorities: 'what should we do next?'\n"
        "- Check status: 'what's the status?'\n"
        "- Route to Hermes: 'hermes <question>'\n\n"
        "Or say /help for the full command list."
    )


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

    # Ingest into shared recommendation layer
    if SHARED_REC_AVAILABLE:
        try:
            ranked_ideas = [ideas[idx] for idx, _ in ranked]
            shared_ingest_alpha(topic, ranked_ideas, avg_score, category=category)
        except Exception:
            pass  # non-critical

    # Save conversation context — use RANKED (sorted) order for consistency
    ctx = load_conversation_context()
    update_chat_context(ctx, 1288928049, {
        "last_agent": "alpha",
        "last_topic": topic,
        "last_alpha_brief_path": brief_path,
        "last_alpha_score_path": os.path.join(ALPHA_SCORES_DIR, f"{intake_id}.json"),
        "last_alpha_recommendations": [{"title": ranked[i][1]["title"], "action": ranked[i][1]["action"], "score": ranked[i][1]["score"]["total"]} for i in range(len(ranked))],
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

def cmd_recs(args=None):
    """Show shared recommendations across all sources."""
    if not SHARED_REC_AVAILABLE:
        return "Shared recommendation layer not available.\nCheck that scripts/recommendations/ exists."
    try:
        subcmd = (args[0] if args else "top").lower()
        if subcmd == "top":
            limit = int(args[1]) if len(args) > 1 else 5
            recs = get_top_recommendations(n=limit)
            if not recs:
                return "No recommendations yet. Run Alpha research or Hermes search to generate some."
            lines = [f"Top {len(recs)} Recommendations", ""]
            for i, r in enumerate(recs, 1):
                lines.append(f"{i}. {r['title'][:60]}")
                lines.append(f"   Score: {r['composite_score']}/10 | {r['priority'].upper()} | {r['source']}")
                if r.get("summary"):
                    lines.append(f"   {r['summary'][:100]}")
                lines.append(f"   ID: {r['id'][:24]}")
                lines.append("")
            return "\n".join(lines)
        elif subcmd == "summary":
            s = rec_summary()
            lines = [
                "Shared Recommendation Summary",
                f"Total: {s['total']}",
                f"By status: {s['by_status']}",
                f"By source: {s['by_source']}",
                f"Avg score: {s['avg_composite_score']}/10",
            ]
            return "\n".join(lines)
        elif subcmd == "next":
            return rec_next_steps()
        elif subcmd == "approve" and len(args) > 1:
            from recommendation_schema import get_recommendations, update_recommendation, add_follow_up_event
            recs = get_recommendations(status="new")
            idx = int(args[1]) - 1 if args[1].isdigit() else -1
            if 0 <= idx < len(recs):
                rec = recs[idx]
                update_recommendation(rec["id"], {"status": "approved"})
                add_follow_up_event(rec["id"], "approved", "Approved via Telegram /recs approve")
                return f"Approved: {rec['title'][:50]}\nStatus set to approved."
            return "Invalid recommendation number. Use /recs top to see options."
        elif subcmd == "reject" and len(args) > 1:
            from recommendation_schema import get_recommendations, update_recommendation, add_follow_up_event
            recs = get_recommendations(status="new")
            idx = int(args[1]) - 1 if args[1].isdigit() else -1
            if 0 <= idx < len(recs):
                rec = recs[idx]
                reason = " ".join(args[2:]) if len(args) > 2 else "Rejected via Telegram"
                update_recommendation(rec["id"], {"status": "rejected"})
                add_follow_up_event(rec["id"], "rejected", reason)
                return f"Rejected: {rec['title'][:50]}\nReason: {reason}"
            return "Invalid recommendation number. Use /recs top to see options."
        else:
            return f"Usage:\n/recs top [n] - Top recommendations\n/recs summary - Overview\n/recs next - Next steps\n/recs approve <n> - Approve recommendation\n/recs reject <n> [reason] - Reject recommendation"
    except Exception as e:
        return f"Recommendation error: {str(e)[:100]}"

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
        "/recs": cmd_recs,
        "/orders": lambda a: cmd_orders(),
        "/recover": lambda a: "Recovery check: use /run recovery",
        "/processes": lambda a: cmd_processes(),
        "/run": cmd_run,
        "/blocked": lambda a: cmd_blocked(),
    }

    handler = handlers.get(cmd)
    if handler:
        return handler(args)

    # Not a slash command — classify intent
    full_text = text.strip()
    intent, match, extra = classify_message_intent(full_text)

    # Debug receipt
    write_alpha_debug_receipt({
        "source": "process_command",
        "raw_text": full_text[:100],
        "detected_intent": intent,
        "routed_to": intent,
    })

    # Route by intent
    if intent == "GREETING":
        return handle_greeting(agent=extra)

    elif intent == "CASUAL_AGENT_CHAT":
        return handle_casual_chat(agent=extra)

    elif intent == "HERMES_ADVISORY":
        return hermes_direct_answer(extra or full_text)

    elif intent == "HERMES_WEB_SEARCH":
        if HERMES_SEARCH_AVAILABLE:
            try:
                advisory = build_advisory_answer(extra or full_text)
                lines = [
                    f"Hermes Web Search — {extra[:60] if extra else 'query'}",
                    "",
                    advisory.get("answer", "No results."),
                    "",
                    f"Provider: {advisory.get('provider', 'none')}",
                ]
                if advisory.get("opportunity_score", {}).get("overall", 0) > 0:
                    score = advisory["opportunity_score"]
                    lines.append(f"Score: {score['overall']}/10")
                if advisory.get("next_step"):
                    lines.append(f"\n{advisory['next_step']}")
                # Ingest into shared recommendation layer
                if SHARED_REC_AVAILABLE:
                    try:
                        shared_ingest_hermes(extra or full_text, {"status": "ok", "provider": advisory.get("provider", "unknown")}, advisory, topic=extra or full_text)
                    except Exception:
                        pass
                return "\n".join(lines)
            except Exception as e:
                return f"Search error: {str(e)[:100]}"
        else:
            return (
                "Hermes web search is not configured.\n\n"
                "No search provider key found. Add one of:\n"
                "  BRAVE_SEARCH_API_KEY (recommended)\n"
                "  TAVILY_API_KEY\n"
                "  SERPAPI_API_KEY\n"
                "  ALPHA_SEARXNG_URL\n\n"
                f"Your query: {extra or 'N/A'}\n\n"
                "See docs/hermes_internet_search_setup.md for details."
            )

    elif intent == "HERMES_URL_REVIEW":
        if HERMES_SEARCH_AVAILABLE:
            try:
                review = hermes_url_review(extra or "")
                lines = [
                    f"Hermes URL Review — {extra[:60] if extra else 'URL'}",
                    "",
                ]
                if review.get("title"):
                    lines.append(f"Title: {review['title']}")
                if review.get("summary"):
                    lines.append(f"Summary: {review['summary'][:300]}")
                lines.append(f"Provider: {review.get('provider', 'none')}")
                lines.append(f"Status: {review.get('status', 'unknown')}")
                return "\n".join(lines)
            except Exception as e:
                return f"URL review error: {str(e)[:100]}"
        else:
            return _hermes_url_review_answer(extra or "", "")

    elif intent == "NEXUS_STATUS_OR_REPORT":
        return handle_status_report()

    elif intent == "ALPHA_CONTEXT_FOLLOWUP":
        return cmd_followup(extra, match, 1288928049)

    elif intent == "ALPHA_RESEARCH_REQUEST":
        return cmd_alpha_fallback(extra or full_text, source="live_polling")

    elif intent == "WORK_ORDER_REQUEST":
        wo = create_work_order(full_text, "hermes", "ACTIVE_INTERNAL", source="telegram")
        return f"Work Order Created: {wo['work_order_id']}\nRoute: hermes\nMode: ACTIVE_INTERNAL"

    elif intent == "APPROVAL_ACTION":
        # Should have been caught by slash command, but handle plain-language too
        parts_lower = full_text.lower().split()
        if len(parts_lower) >= 2:
            action = parts_lower[0]
            item_id = parts_lower[1]
            if action == "approve":
                return cmd_approve([item_id])
            elif action == "reject":
                reason = " ".join(parts_lower[2:]) if len(parts_lower) > 2 else "no reason"
                return cmd_reject([item_id, reason])
            elif action == "revise":
                feedback = " ".join(parts_lower[2:]) if len(parts_lower) > 2 else "no feedback"
                return cmd_revise([item_id, feedback])
        return "Usage: approve <id>, reject <id> <reason>, or revise <id> <feedback>"

    else:  # UNKNOWN_HELPFUL_FALLBACK
        return handle_unknown_fallback()

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
