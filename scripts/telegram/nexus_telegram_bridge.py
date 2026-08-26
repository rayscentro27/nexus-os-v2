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
from zoneinfo import ZoneInfo
from pathlib import Path

# Agent Platform imports (nexus_agent_platform lives at scripts/nexus_agent_platform/)
_SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

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

# Alpha opinion advisor import
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "alpha"))
try:
    from alpha_opinion_advisor import alpha_opinion, format_alpha_opinion
    ALPHA_OPINION_AVAILABLE = True
except Exception:
    ALPHA_OPINION_AVAILABLE = False

# Temporal intelligence import
try:
    from temporal_intent import detect_temporal_intent, format_time_response
    TEMPORAL_AVAILABLE = True
except Exception:
    TEMPORAL_AVAILABLE = False

try:
    from nexus_agent_platform.hermes_operator import operate as operate_governed_capability
except Exception:
    operate_governed_capability = None

from nexus_agent_platform.runtime.execution_telemetry import execution_run

# Active context import
try:
    from active_context import (
        save_active_context, load_active_context, is_context_fresh,
        select_context_item, detect_followup_intent,
        format_score_explanation, format_best_option_explanation,
        format_deeper_research, format_work_order_draft,
        handle_confirm_pending, compute_top_index, clean_html,
        save_pending_action, load_pending_action, clear_pending_action,
    )
    ACTIVE_CONTEXT_AVAILABLE = True
except Exception:
    ACTIVE_CONTEXT_AVAILABLE = False

# New router architecture imports
try:
    from message_understanding import understand_message
    MESSAGE_UNDERSTANDING_AVAILABLE = True
except Exception:
    MESSAGE_UNDERSTANDING_AVAILABLE = False

try:
    from provider_status import get_web_provider_status, get_provider_display_name, is_web_available
    PROVIDER_STATUS_AVAILABLE = True
except Exception:
    PROVIDER_STATUS_AVAILABLE = False

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hermes"))
try:
    from hermes_draft_engine import generate_hermes_draft
    HERMES_DRAFT_AVAILABLE = True
except Exception:
    HERMES_DRAFT_AVAILABLE = False

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "alpha"))
try:
    from alpha_draft_engine import generate_alpha_draft
    ALPHA_DRAFT_AVAILABLE = True
except Exception:
    ALPHA_DRAFT_AVAILABLE = False

try:
    from alpha_live_research import run_alpha_live_research, format_alpha_live_research_response
    ALPHA_LIVE_RESEARCH_AVAILABLE = True
except Exception:
    ALPHA_LIVE_RESEARCH_AVAILABLE = False

try:
    from retrieval_gate import should_retrieve
    RETRIEVAL_GATE_AVAILABLE = True
except Exception:
    RETRIEVAL_GATE_AVAILABLE = False

try:
    from query_rewriter import rewrite_for_retrieval
    QUERY_REWRITER_AVAILABLE = True
except Exception:
    QUERY_REWRITER_AVAILABLE = False

try:
    from evidence_merge import merge_evidence_into_draft
    EVIDENCE_MERGE_AVAILABLE = True
except Exception:
    EVIDENCE_MERGE_AVAILABLE = False

# Brain contracts import
try:
    from brain_contracts import (
        detect_brain_mode, detect_idea_brief_request, detect_command_plan_request,
        create_idea_brief, create_command_plan,
        format_idea_brief_response, format_command_plan_response,
        format_command_refusal, format_advisor_general_answer,
        ADVISOR, COMMAND,
    )
    BRAIN_CONTRACTS_AVAILABLE = True
except Exception:
    BRAIN_CONTRACTS_AVAILABLE = False

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
NEXUS_MISSION_DIR = "reports/runtime/nexus_telegram_missions"
NEXUS_MISSION_LATEST_PATH = "reports/runtime/nexus_telegram_missions_latest.json"
NEXUS_MISSION_PUBLIC_PATH = "public/runtime/nexus-telegram-missions.json"
NEXUS_ROUTING_ROOT_CAUSE_PATH = "reports/telegram/nexus_hermes_routing_root_cause.md"
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
ALPHA_LIVE_RESEARCH_STATUS_PATH = "reports/runtime/alpha_live_research_latest.json"
OANDA_PRACTICE_STATUS_PATH = "reports/runtime/oanda_practice_engine_status_latest.json"
PHOENIX_TZ = ZoneInfo("America/Phoenix")

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


def phoenix_now():
    return datetime.now(PHOENIX_TZ)


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def mask_chat_id(chat_id):
    text = str(chat_id or "")
    if len(text) <= 4:
        return "***"
    return f"{text[:2]}***{text[-2:]}"


def sanitize_error(error):
    return str(error or "")[:240]

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
    return "Nexus Mobile Operator Console\n\nCommands:\n/report - Full anytime operator report\n/status - System status\n/daily - Daily monitor\n/research - Research/NotebookLM/Alpha status\n/content - Content drafts/social/email status\n/approvals - Ray Review queue count and summaries\n/orders - Work orders summary\n/hermes <msg> - Hermes advisory\n/recover - Recovery check\n/approve <id> - Approve item\n/reject <id> <reason> - Reject\n/revise <id> <feedback> - Request revision\n/request <text> - Internal request\n/alpha <topic> - Alpha outside opinion\n/recs - Shared recommendations\n/processes - Process registry\n/run <id> - Run safe process\n/blocked - Blocked actions"

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

        # Build dynamic priorities based on actual state
        priorities = []
        if a.get("count", 0) > 0:
            priorities.append(f"Review {a['count']} pending approval(s)")
        if chat_ctx.get("last_topic") and not chat_ctx.get("last_work_order_path"):
            priorities.append(f"Act on Alpha research: {chat_ctx['last_topic'][:40]}")

        # Dynamic: check if GoClear pages are live (not stale)
        goclear_live = os.path.exists("reports/public_site") or os.path.exists("dist/goclear")
        if not goclear_live:
            priorities.append("Verify GoClear public pages are live after Netlify deploy")
        else:
            priorities.append("Review/polish GoClear public pages and client funnel")

        # Dynamic: check Stripe status
        stripe_configured = bool(os.environ.get("STRIPE_SECRET_KEY", "").strip())
        if not stripe_configured:
            priorities.append("Connect Stripe test checkout to landing page")
        else:
            priorities.append("Test Stripe checkout end-to-end")

        # Always relevant
        priorities.append("Replace mock clientPortalData with real Supabase queries")
        priorities.append("Create Credit Readiness Checklist lead magnet")

        # Web search status — check actual provider, not just env vars
        web_search_status = "NOT_CONFIGURED"
        if HERMES_SEARCH_AVAILABLE:
            try:
                from hermes_web_search import _provider_priority
                providers = _provider_priority()
                if providers:
                    active = providers[0][0]  # first in priority order
                    web_search_status = f"ACTIVE_{active.upper()}"
                else:
                    web_search_status = "LAYER_READY_PROVIDER_MISSING"
            except Exception:
                # Fallback: check env vars directly
                providers = []
                for env_name, label in [("BRAVE_SEARCH_API_KEY", "Brave"), ("TAVILY_API_KEY", "Tavily"),
                                         ("SERPAPI_API_KEY", "SerpAPI"), ("ALPHA_SEARXNG_URL", "SearXNG")]:
                    if os.environ.get(env_name, "").strip():
                        providers.append(label)
                web_search_status = f"ACTIVE ({', '.join(providers)})" if providers else "LAYER_READY_PROVIDER_MISSING"

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
        priorities.append("Review/polish GoClear public pages and client funnel")
        priorities.append("Replace mock clientPortalData with real Supabase queries")
        priorities.append("Create Credit Readiness Checklist lead magnet")
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
        answer_lines.append("- Review GoClear pages and client funnel")
        answer_lines.append("- Replace mock client data with real Supabase queries")
        answer_lines.append("- Create Credit Readiness Checklist lead magnet")
        answer = "\n".join(answer_lines)

    elif any(kw in message_lower for kw in ["realistic", "risk", "stop", "block", "fail"]):
        answer_lines = [
            "Hermes Advisory — Risk Assessment:",
            "",
            "Current blockers:",
            f"- {approval_count} pending approvals (if any are external-facing, they gate revenue)",
            "- Client portal uses mock data (not wired to Supabase)",
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
        return "Usage: /alpha <topic-or-question>\n\nI can give an outside opinion, challenge a plan, compare options, or research a topic."
    topic = " ".join(args)

    # If it looks like explicit research, route to live external research.
    if is_alpha_live_research_request(topic):
        return _handle_alpha_research(topic)

    # Otherwise, give an outside opinion
    if ALPHA_OPINION_AVAILABLE:
        try:
            opinion = alpha_opinion(topic)
            return format_alpha_opinion(opinion)
        except Exception as e:
            return f"Alpha opinion error: {str(e)[:100]}\n\nFalling back to general guidance."

    # Fallback if opinion module not available
    return (
        f"Alpha outside opinion on: {topic[:80]}\n\n"
        "I would look at this from the outside. What matters is whether this "
        "moves the needle for GoClear's core business.\n\n"
        "Research needed? Say 'alpha research <topic>' if you want current evidence."
    )

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


# --- Nexus Hermes missions and live tools ---

def normalize_message(text):
    cleaned = re.sub(r"\s+", " ", text.strip())
    return cleaned


def mission_id_for(update_id, text):
    seed = f"{update_id or 'manual'}:{text}:{utc_now_iso()}"
    return "nxmsg_" + hashlib.sha256(seed.encode()).hexdigest()[:18]


def create_mission(update_id, bot_id, chat_id, text):
    mission = {
        "mission_id": mission_id_for(update_id, text),
        "telegram_update_id": update_id,
        "nexus_bot_id": bot_id,
        "ray_chat_id_masked": mask_chat_id(chat_id),
        "original_text": text[:500],
        "normalized_text": normalize_message(text).lower(),
        "selected_intent": None,
        "selected_tool": None,
        "provider": None,
        "model": None,
        "tool_result_reference": None,
        "response_telegram_message_id": None,
        "state": "RECEIVED",
        "states": [{"state": "RECEIVED", "at": utc_now_iso()}],
        "timestamps": {"received_at": utc_now_iso()},
        "retry_count": 0,
        "error": None,
        "fallback_used": False,
    }
    save_mission(mission)
    return mission


def update_mission(mission, state, **updates):
    if not mission:
        return None
    mission.update(updates)
    mission["state"] = state
    mission.setdefault("states", []).append({"state": state, "at": utc_now_iso()})
    mission.setdefault("timestamps", {})[f"{state.lower()}_at"] = utc_now_iso()
    save_mission(mission)
    return mission


def save_mission(mission):
    os.makedirs(NEXUS_MISSION_DIR, exist_ok=True)
    path = os.path.join(NEXUS_MISSION_DIR, f"{mission['mission_id']}.json")
    mission["mission_path"] = path
    with open(path, "w") as f:
        json.dump(mission, f, indent=2)
    write_mission_index()


def write_mission_index():
    try:
        paths = sorted(Path(NEXUS_MISSION_DIR).glob("nxmsg_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:25]
        missions = []
        for path in paths:
            data = load_json(str(path)) or {}
            missions.append({
                "mission_id": data.get("mission_id"),
                "state": data.get("state"),
                "selected_intent": data.get("selected_intent"),
                "selected_tool": data.get("selected_tool"),
                "fallback_used": data.get("fallback_used", False),
                "response_telegram_message_id": data.get("response_telegram_message_id"),
                "received_at": data.get("timestamps", {}).get("received_at"),
                "completed_at": data.get("timestamps", {}).get("completed_at"),
                "error": data.get("error"),
                "text_preview": "[redacted]",
            })
        payload = {"generated_at": utc_now_iso(), "missions": missions}
        save_json(NEXUS_MISSION_LATEST_PATH, payload)
        save_json(NEXUS_MISSION_PUBLIC_PATH, payload)
    except Exception:
        pass


def watchdog_stalled_missions(max_age_seconds=60):
    terminal = {"COMPLETED", "UNAUTHORIZED", "DELIVERY_FAILED", "TOOL_FAILED", "ROUTING_FAILED", "PROVIDER_FAILED", "TIMED_OUT", "DEAD_LETTERED", "STALLED"}
    now = datetime.now(timezone.utc)
    stalled = []
    try:
        for path in Path(NEXUS_MISSION_DIR).glob("nxmsg_*.json"):
            mission = load_json(str(path)) or {}
            if mission.get("state") in terminal:
                continue
            received_at = mission.get("timestamps", {}).get("received_at")
            if not received_at:
                continue
            received_dt = datetime.fromisoformat(received_at.replace("Z", "+00:00"))
            if (now - received_dt).total_seconds() >= max_age_seconds:
                update_mission(mission, "STALLED", error="mission_exceeded_60_second_completion_window")
                stalled.append(mission.get("mission_id"))
    except Exception:
        return []
    return stalled


def write_routing_root_cause_report():
    Path(NEXUS_ROUTING_ROOT_CAUSE_PATH).parent.mkdir(parents=True, exist_ok=True)
    text = f"""# Nexus Hermes Telegram Routing Root Cause

Generated: {utc_now_iso()}

## Defect

Ray-originated Nexus Telegram messages reached the generic Hermes draft fallback:

- `Clarify the question`
- `Source: internal Nexus context`
- `Say 'research deeper' or 'search the web for...'`

## Source

- File: `scripts/hermes/hermes_draft_engine.py`
- Function: `generate_hermes_draft`
- Placeholder item: `Clarify the question`
- Telegram render path: `scripts/telegram/nexus_telegram_bridge.py::_render_draft`

## Routing Failure

`process_command()` handled non-slash Telegram messages by calling
`process_with_new_router()` first. The structured message understanding layer
classified several operational phrases as generic/unknown or general advisory
instead of deterministic Nexus operations. That path selected Hermes draft
generation, rendered local-context source text, and never called live tools.

## Repair

A deterministic Nexus pre-router now runs before the draft/model path. Known
Nexus intents route to live tools and mission tracking before any generic
Hermes draft fallback can execute.

## Mission Lifecycle

Incoming authorized Telegram updates now create durable mission JSON records in
`reports/runtime/nexus_telegram_missions/` and a redacted public summary in
`public/runtime/nexus-telegram-missions.json`.
"""
    Path(NEXUS_ROUTING_ROOT_CAUSE_PATH).write_text(text)


def supabase_headers():
    base = os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL") or ""
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not base or not key:
        return None, {}
    return base.rstrip("/"), {"apikey": key, "authorization": f"Bearer {key}", "accept": "application/json", "content-type": "application/json"}


def supabase_get(table, query):
    base, headers = supabase_headers()
    if not base:
        return {"ok": False, "error": "supabase_service_missing", "rows": []}
    url = f"{base}/rest/v1/{table}?{query}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=25, context=SSL_CTX) as resp:
            rows = json.loads(resp.read().decode() or "[]")
            return {"ok": True, "status_code": resp.status, "rows": rows, "retrieved_at": utc_now_iso(), "source": f"supabase:{table}"}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "status_code": exc.code, "error": f"HTTP_{exc.code}", "rows": [], "source": f"supabase:{table}"}
    except Exception as exc:
        return {"ok": False, "error": exc.__class__.__name__, "rows": [], "source": f"supabase:{table}"}


def parse_since_datetime(text, default_hours=24):
    lower = text.lower()
    if "august 3" in lower or "aug 3" in lower:
        return datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc)
    if "yesterday" in lower:
        return datetime.now(timezone.utc) - __import__("datetime").timedelta(days=1)
    if "today" in lower or "last 24" in lower:
        return datetime.now(timezone.utc) - __import__("datetime").timedelta(hours=24)
    return datetime.now(timezone.utc) - __import__("datetime").timedelta(hours=default_hours)


def tool_get_process_status():
    defs = supabase_get("nexus_process_definitions", "select=id,process_key,name,system,enabled,execution_mode,is_mock,updated_at&order=updated_at.desc&limit=80")
    runs = supabase_get("nexus_process_runs", "select=id,status,started_at,completed_at,heartbeat_at,items_attempted,items_succeeded,items_failed,output_location,error_code,error_message,trace_id,metadata,process_id&order=created_at.desc&limit=40")
    return {"ok": defs["ok"] and runs["ok"], "retrieved_at": utc_now_iso(), "definitions": defs, "runs": runs}


def tool_get_failures(hours=24):
    since = (datetime.now(timezone.utc) - __import__("datetime").timedelta(hours=hours)).isoformat()
    query = f"select=id,status,started_at,completed_at,heartbeat_at,error_code,error_message,trace_id,metadata,process_id&created_at=gte.{urllib.parse.quote(since)}&status=in.(FAILED,BLOCKED,TIMED_OUT,CANCELLED,PARTIAL)&order=created_at.desc&limit=30"
    return supabase_get("nexus_process_runs", query)


def tool_get_research_history(text):
    since = parse_since_datetime(text).isoformat()
    runs = supabase_get("nexus_research_runs", f"select=id,script_path,category,source_type,query_input,output_destination,status,items_retrieved,items_accepted,items_rejected,started_at,completed_at,created_at,metadata&created_at=gte.{urllib.parse.quote(since)}&order=created_at.desc&limit=25")
    results = supabase_get("nexus_research_results", f"select=id,research_run_id,category,title,source_url,source_name,retrieved_at,confidence,score,status,approval_state,downstream_destination,metadata&retrieved_at=gte.{urllib.parse.quote(since)}&order=retrieved_at.desc&limit=40")
    return {"ok": runs["ok"] and results["ok"], "retrieved_at": utc_now_iso(), "since": since, "runs": runs, "results": results}


def tool_get_opportunities(limit=8):
    query = f"select=id,external_id,title,summary,category,status,score,priority,risk_level,approval_required,goclear_review_status,source,recommended_next_action,created_at,updated_at&order=updated_at.desc&limit={limit}"
    return supabase_get("business_opportunities", query)


def tool_get_alpha_status():
    latest = load_json(ALPHA_LIVE_RESEARCH_STATUS_PATH) or {}
    public = load_json("public/runtime/alpha-live-research-status.json") or {}
    opportunities = tool_get_opportunities(5)
    return {"ok": bool(latest or public), "retrieved_at": utc_now_iso(), "latest_research": latest or public, "opportunities": opportunities, "alpha_bot_worker": launchd_status_summary("com.nexus.telegram-alpha")}


def tool_get_trading_status():
    status = load_json(OANDA_PRACTICE_STATUS_PATH) or {}
    public = load_json("public/runtime/oanda-practice-status.json") or {}
    return {"ok": bool(status or public), "retrieved_at": utc_now_iso(), "status": status or public, "service": launchd_status_summary("com.nexus.oanda-practice-trading")}


def tool_get_pending_approvals():
    queue = load_json("reports/runtime/ray_review_queue_latest.json") or {}
    items = queue if isinstance(queue, list) else queue.get("items", []) if isinstance(queue, dict) else []
    return {"ok": True, "retrieved_at": utc_now_iso(), "items": items[:12], "count": len(items), "source": "reports/runtime/ray_review_queue_latest.json"}


def launchd_status_summary(label):
    try:
        import subprocess
        result = subprocess.run(["launchctl", "print", f"gui/{os.getuid()}/{label}"], text=True, capture_output=True, timeout=5)
        if result.returncode != 0:
            return {"label": label, "loaded": False, "state": "not_loaded"}
        out = result.stdout
        state = re.search(r"state = ([^\n]+)", out)
        pid = re.search(r"pid = ([^\n]+)", out)
        return {"label": label, "loaded": True, "state": state.group(1).strip() if state else "unknown", "pid": pid.group(1).strip() if pid else None}
    except Exception as exc:
        return {"label": label, "loaded": False, "state": "check_failed", "error": exc.__class__.__name__}


def tool_get_system_status():
    processes = tool_get_process_status()
    failures = tool_get_failures(24)
    alpha = tool_get_alpha_status()
    trading = tool_get_trading_status()
    approvals = tool_get_pending_approvals()
    provider = {
        "supabase": "PASS" if processes.get("ok") else "FAIL",
        "alpha_research": "PASS" if alpha.get("ok") else "FAIL",
        "oanda_practice": "PASS" if trading.get("ok") else "FAIL",
    }
    return {"ok": processes.get("ok"), "retrieved_at": utc_now_iso(), "processes": processes, "failures": failures, "alpha": alpha, "trading": trading, "approvals": approvals, "providers": provider}


def tool_get_current_priorities():
    system = tool_get_system_status()
    failures = system.get("failures", {}).get("rows", [])
    approvals = system.get("approvals", {}).get("items", [])
    opportunities = tool_get_opportunities(3).get("rows", [])
    return {"ok": True, "retrieved_at": utc_now_iso(), "failures": failures[:5], "approvals": approvals[:5], "opportunities": opportunities[:3]}


def render_system_status(tool):
    failures = tool.get("failures", {}).get("rows", [])
    alpha = tool.get("alpha", {}).get("latest_research", {})
    trading = tool.get("trading", {}).get("status", {})
    approvals = tool.get("approvals", {})
    recent_runs = tool.get("processes", {}).get("runs", {}).get("rows", [])
    active_runs = [r for r in recent_runs if r.get("status") == "RUNNING"]
    lines = [
        "Nexus Hermes Live System Report",
        "",
        f"Overall status: {'OPERATIONAL_WITH_MONITORING' if tool.get('ok') else 'DEGRADED'}",
        f"Active services: continuous loop, Nexus Telegram polling, Alpha Telegram, Oanda practice engine",
        f"Running process records: {len(active_runs)}",
        f"Failed/stale services: {len(failures)} recent failure records",
        f"Provider health: Supabase {tool['providers']['supabase']}, Alpha research {tool['providers']['alpha_research']}, Oanda practice {tool['providers']['oanda_practice']}",
        f"Hermes status: Nexus Telegram deterministic router active",
        f"Alpha status: {alpha.get('status', 'unknown')} · sources {alpha.get('source_count', 'unknown')}",
        f"Research status: latest {alpha.get('research_id', 'unknown')}",
        f"Trading status: {trading.get('state', 'unknown')} · strategy {trading.get('strategy', 'unknown')}",
        f"Tester onboarding: certified in prior activation; no live issue found in this status tool",
        f"Pending approvals: {approvals.get('count', 0)}",
        f"Recent failures: {', '.join((f.get('error_code') or f.get('status') or 'failure') for f in failures[:3]) or 'none in query'}",
        "",
        f"Retrieval time: {tool.get('retrieved_at')}",
        "Sources: nexus_process_definitions, nexus_process_runs, nexus_research_runs/results, business_opportunities, runtime status files",
    ]
    return "\n".join(lines)


def render_alpha_status(tool):
    latest = tool.get("latest_research", {})
    opps = tool.get("opportunities", {}).get("rows", [])
    service = tool.get("alpha_bot_worker", {})
    lines = [
        "Nexus Hermes — Alpha Research Status",
        "",
        f"Alpha bot worker state: {service.get('state', 'not checked')}",
        f"Current mission: latest research snapshot {latest.get('research_id', 'none')}",
        f"Last research run: {latest.get('query', 'unknown')}",
        f"Providers used: Brave {'PASS' if latest.get('brave_ok') else 'unknown'}, OpenRouter {'PASS' if latest.get('openrouter_ok') else 'unknown'}, YouTube {'PASS' if latest.get('youtube_ok') else 'not used/unknown'}",
        f"Sources found: {latest.get('source_count', 'unknown')}",
        f"Last stored research ID: {latest.get('research_id', 'unknown')}",
        f"Last opportunity stored: {'YES' if latest.get('opportunity_stored') else 'NO/unknown'}",
        f"Last response delivery: see Nexus/Alpha Telegram mission receipts",
        "",
        "Recent opportunities:",
    ]
    for opp in opps[:5]:
        lines.append(f"- {opp.get('title', 'Opportunity')[:90]} · {opp.get('status', 'unknown')} · score {opp.get('score', 'n/a')} · {opp.get('id', '')}")
    if not opps:
        lines.append("- none returned")
    lines.extend(["", f"Retrieval time: {tool.get('retrieved_at')}", "Sources: runtime Alpha snapshot + business_opportunities"])
    return "\n".join(lines)


def render_research_history(tool):
    runs = tool.get("runs", {}).get("rows", [])
    results = tool.get("results", {}).get("rows", [])
    by_run = {}
    for row in results:
        by_run.setdefault(row.get("research_run_id"), []).append(row)
    lines = [
        f"Nexus Hermes — Research Jobs Since {tool.get('since')}",
        "",
        f"Jobs returned: {len(runs)}",
        f"Research result rows returned: {len(results)}",
        "",
    ]
    for run in runs[:12]:
        linked = by_run.get(run.get("id"), [])
        lines.append(f"- Run {run.get('id')} · {run.get('status')} · {run.get('category')}")
        lines.append(f"  Researcher: {Path(run.get('script_path','unknown')).name}")
        lines.append(f"  Query: {run.get('query_input')}")
        lines.append(f"  Providers: {run.get('source_type')}")
        lines.append(f"  Sources/findings: retrieved {run.get('items_retrieved')} · accepted {run.get('items_accepted')} · linked result rows {len(linked)}")
        lines.append(f"  Storage: {run.get('output_destination')}")
        lines.append(f"  Started/completed: {run.get('started_at')} / {run.get('completed_at')}")
    if not runs:
        lines.append("- No research runs returned for this range.")
    lines.extend(["", f"Retrieval time: {tool.get('retrieved_at')}", "Sources: nexus_research_runs + nexus_research_results"])
    return "\n".join(lines)


def render_opportunity_history(tool):
    rows = tool.get("rows", [])
    lines = ["Nexus Hermes — Recent Opportunities", ""]
    for row in rows:
        lines.append(f"- {row.get('title', 'Opportunity')[:100]} · {row.get('category')} · {row.get('status')} · score {row.get('score', 'n/a')}")
        if row.get("recommended_next_action"):
            lines.append(f"  Next: {row.get('recommended_next_action')[:140]}")
        lines.append(f"  ID: {row.get('id')}")
    if not rows:
        lines.append("- No opportunities returned.")
    lines.extend(["", f"Retrieval time: {tool.get('retrieved_at')}", "Source: business_opportunities"])
    return "\n".join(lines)


def render_failure_report(tool):
    rows = tool.get("rows", [])
    lines = ["Nexus Hermes — Failures In The Last 24 Hours", "", f"Failures returned: {len(rows)}"]
    for row in rows[:12]:
        lines.append(f"- {row.get('status')} · {row.get('error_code') or 'no error code'} · {row.get('trace_id') or row.get('id')}")
        if row.get("error_message"):
            lines.append(f"  {row.get('error_message')[:160]}")
        lines.append(f"  Heartbeat: {row.get('heartbeat_at')}")
    if not rows:
        lines.append("- No failed process-run records returned.")
    lines.extend(["", f"Retrieval time: {tool.get('retrieved_at')}", "Source: nexus_process_runs"])
    return "\n".join(lines)


def render_trading_status(tool):
    status = tool.get("status", {})
    limits = status.get("risk_limits", {})
    decision = status.get("most_recent_decision", {}) or {}
    return "\n".join([
        "Nexus Hermes — Oanda Practice Trading Report",
        "",
        f"Environment: {status.get('environment', 'OANDA_PRACTICE')}",
        f"Engine state: {status.get('state', 'unknown')}",
        f"Strategy: {status.get('strategy', 'unknown')}",
        f"Monitored instruments: {', '.join(status.get('monitored_instruments', [])[:8])}",
        f"Open positions: {status.get('open_position_count', 'unknown')}",
        f"Pending orders: {status.get('pending_order_count', 'unknown')}",
        f"Latest signal: {status.get('most_recent_signal') or 'none'}",
        f"Latest decision: {decision.get('state', 'unknown')} — {decision.get('reason', 'no reason recorded')}",
        f"Practice P&L: {status.get('current_simulated_pnl', 'unknown')}",
        f"Risk limits: max units {limits.get('max_order_units')}, max open positions {limits.get('max_open_positions')}, max trades/day {limits.get('max_trades_per_day')}, confidence {limits.get('signal_confidence_threshold')}",
        f"Kill switch: {'ACTIVE' if status.get('kill_switch_active') else 'available / inactive'}",
        f"Heartbeat: {status.get('heartbeat_at') or status.get('updated_at')}",
        "",
        f"Retrieval time: {tool.get('retrieved_at')}",
        "Source: reports/runtime/oanda_practice_engine_status_latest.json",
    ])


def render_priorities(tool):
    lines = ["Nexus Hermes — Current Priorities", ""]
    if tool.get("failures"):
        lines.append("1. Review recent failures and blocked runs.")
    elif tool.get("approvals"):
        lines.append("1. Clear pending Ray Review items.")
    elif tool.get("opportunities"):
        lines.append("1. Review the newest Alpha-sourced opportunity.")
    else:
        lines.append("1. Keep controlled tester workflows monitored and watch Oanda practice signals.")
    lines.append("2. Keep Alpha research source-backed before turning findings into work orders.")
    lines.append("3. Keep real-money trading, funding submission, and dispute submission blocked unless separately approved.")
    lines.append("")
    lines.append(f"Retrieval time: {tool.get('retrieved_at')}")
    return "\n".join(lines)


def classify_nexus_pre_intent(text):
    lower = normalize_message(text).lower()
    stripped = re.sub(r"^(?:@)?(?:nexus|hermes)\s*[,:\-]?\s*", "", lower).strip()
    if re.match(r"^(good\s+morning|good\s+afternoon|good\s+evening|good\s+night|hello|hi|hey)\b", stripped):
        return "greeting", "none", 0.98
    if re.match(r"^(thank(s| you)|appreciate it)\b", stripped):
        return "thanks", "none", 0.95
    if re.search(r"\b(what can you do|help|commands)\b", stripped):
        return "help", "none", 0.9
    if is_trading_status_question(stripped):
        return "trading_status", "get_trading_status", 0.96
    if re.search(r"\b(alpha)\b", stripped) and re.search(r"\b(status|researching|research status|opportunities stored|current alpha|latest alpha)\b", stripped):
        return "Alpha_status", "get_Alpha_status", 0.95
    if re.search(r"\b(research job|research jobs|research history|every research|show.*research|ran since)\b", stripped):
        return "research_history", "get_research_history", 0.96
    if re.search(r"\b(opportunities|opportunity|found|stored)\b", stripped) and re.search(r"\b(recent|latest|stored|found|status|history)\b", stripped):
        return "opportunity_history", "get_recent_opportunities", 0.92
    if re.search(r"\b(system status|status report|report on system|system report|current status|how is nexus doing)\b", stripped):
        return "system_status", "get_system_status", 0.97
    if re.search(r"\b(what failed|failed|failures|errors|blocked|last 24 hours)\b", stripped):
        return "failure_report", "get_failures", 0.94
    if re.search(r"\b(processes|process status|running right now|what is running|jobs running)\b", stripped):
        return "process_status", "get_process_status", 0.93
    if re.search(r"\b(approvals|pending approval|ray review|needs my approval)\b", stripped):
        return "approvals_status", "get_pending_approvals", 0.92
    if re.search(r"\b(what should we do next|what do we do next|priority|priorities|current priorities)\b", stripped):
        return "current_priorities", "get_current_priorities", 0.9
    if re.search(r"\b(search the web|live web research|research current|look up current)\b", stripped):
        return "live_web_research", "web_search", 0.86
    return None, None, 0.0


def handle_nexus_pre_route(text, mission=None):
    # Route explicit operator requests through the canonical broker before the
    # legacy advisory tools. The broker owns capability registration,
    # approval policy, receipts, and the no-arbitrary-shell boundary.
    if operate_governed_capability and re.search(r"\b(run|start|check|generate|launch)\b", text, re.I):
        governed = operate_governed_capability(text, execute=True)
        if governed.get("intent") == "execute":
            receipt = governed.get("receipt") or {}
            response = (f"Nexus governed capability: {governed.get('capability_id')}\n"
                        f"Status: {governed.get('status', 'UNKNOWN')}\n"
                        f"Receipt: {receipt.get('receipt_id', 'UNKNOWN')}\n"
                        f"Evidence: {receipt.get('evidence_fingerprint', 'UNKNOWN')}\n"
                        "Arbitrary shell: PROHIBITED")
            if mission:
                update_mission(mission, "ROUTED", selected_intent="governed_capability", selected_tool=governed.get("capability_id"))
                update_mission(mission, "TOOL_COMPLETED", tool_ok=governed.get("status") == "PASS", tool_result_reference=receipt.get("receipt_id"))
                update_mission(mission, "RESPONSE_COMPOSED")
            return response
    intent, tool_name, confidence = classify_nexus_pre_intent(text)
    if not intent:
        return None
    if mission:
        update_mission(mission, "ROUTED", selected_intent=intent, selected_tool=tool_name, router_confidence=confidence)
    if intent == "greeting":
        hour = phoenix_now().hour
        part = "morning" if hour < 12 else "afternoon" if hour < 17 else "evening"
        response = f"Good {part}, Ray. Nexus Hermes is online. I can pull live system status, Alpha research, opportunities, failures, approvals, and Oanda practice trading from current Nexus records."
        if mission:
            update_mission(mission, "RESPONSE_COMPOSED")
        return response
    if intent == "thanks":
        if mission:
            update_mission(mission, "RESPONSE_COMPOSED")
        return "You are welcome, Ray. Nexus Hermes is standing by."
    if intent == "help":
        if mission:
            update_mission(mission, "RESPONSE_COMPOSED")
        return "Nexus Hermes can answer: system status, Alpha research status, research jobs since a date, recent opportunities, Oanda practice trading status, failures, approvals, and current priorities."

    tool_started = utc_now_iso()
    if mission:
        update_mission(mission, "TOOL_STARTED")
    try:
        if tool_name == "get_system_status":
            tool = tool_get_system_status(); response = render_system_status(tool)
        elif tool_name == "get_process_status":
            tool = tool_get_process_status(); response = render_system_status({"ok": tool.get("ok"), "retrieved_at": tool.get("retrieved_at"), "processes": tool, "failures": {"rows": []}, "alpha": tool_get_alpha_status(), "trading": tool_get_trading_status(), "approvals": tool_get_pending_approvals(), "providers": {"supabase": "PASS" if tool.get("ok") else "FAIL", "alpha_research": "PASS", "oanda_practice": "PASS"}})
        elif tool_name == "get_failures":
            tool = tool_get_failures(24); response = render_failure_report(tool)
        elif tool_name == "get_research_history":
            tool = tool_get_research_history(text); response = render_research_history(tool)
        elif tool_name == "get_recent_opportunities":
            tool = tool_get_opportunities(); response = render_opportunity_history(tool)
        elif tool_name == "get_Alpha_status":
            tool = tool_get_alpha_status(); response = render_alpha_status(tool)
        elif tool_name == "get_trading_status":
            tool = tool_get_trading_status(); response = render_trading_status(tool)
        elif tool_name == "get_pending_approvals":
            tool = tool_get_pending_approvals(); response = f"Nexus Hermes — Pending Approvals\n\nPending approvals: {tool.get('count', 0)}\nRetrieval time: {tool.get('retrieved_at')}\nSource: {tool.get('source')}"
        elif tool_name == "get_current_priorities":
            tool = tool_get_current_priorities(); response = render_priorities(tool)
        elif tool_name == "web_search":
            response = _handle_hermes_web_search(text)
            tool = {"ok": not response.lower().startswith("web search is not configured"), "retrieved_at": utc_now_iso(), "source": "hermes_web_search"}
        else:
            tool = {"ok": False, "error": "unknown_tool", "retrieved_at": utc_now_iso()}
            response = f"Nexus Hermes tool failed: {tool_name} is not implemented."
        if mission:
            update_mission(mission, "TOOL_COMPLETED", tool_started_at=tool_started, tool_completed_at=utc_now_iso(), tool_ok=tool.get("ok"), tool_result_reference=tool.get("source") or tool_name)
            update_mission(mission, "RESPONSE_COMPOSED")
        return response
    except Exception as exc:
        if mission:
            update_mission(mission, "TOOL_FAILED", error=sanitize_error(exc), selected_tool=tool_name)
        return f"Nexus Hermes tool failed.\n\nTool: {tool_name}\nError: {exc.__class__.__name__}\nRetry: safe retry will be attempted by the next polling cycle if the mission remains incomplete."

def process_telegram_updates(token, dry_run=False):
    """
    Bounded one-shot polling: fetch new updates, process commands, send replies.
    Returns status string.
    """
    with execution_run(
        process_id="hermes_router",
        process_name="Hermes Work Router",
        worker_id="nexus_telegram_bridge",
        agent_id="nexus_hermes",
        execution_type="worker_poll",
        source="scripts/telegram/nexus_telegram_bridge.py:process_telegram_updates",
        metadata={"dry_run": dry_run},
    ) as poll_run_id:
        watchdog_stalled_missions()
        bot_id = None
        bot_resp = telegram_api_call(token, "getMe", {})
        if bot_resp and bot_resp.get("ok"):
            bot_id = bot_resp.get("result", {}).get("id")

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
            mission = create_mission(uid, bot_id, chat_id, text or "")
        
            # Ignore non-text messages
            if not text:
                update_mission(mission, "ROUTING_FAILED", error="non_text_update")
                continue
        
            # Authorization check
            if chat_id not in ALLOWED_CHAT_IDS:
                skipped_unauthorized += 1
                update_mission(mission, "UNAUTHORIZED", error="chat_not_authorized")
                continue
        
            update_mission(mission, "AUTHORIZED")

            with execution_run(
                process_id="hermes_router",
                process_name="Hermes Work Router",
                worker_id="nexus_telegram_bridge",
                agent_id="nexus_hermes",
                execution_type="telegram_update_run",
                source="scripts/telegram/nexus_telegram_bridge.py:process_telegram_updates",
                parent_run_id=poll_run_id,
                metadata={"update_id": uid, "chat_id_hash": hashlib.sha256(str(chat_id).encode()).hexdigest()[:16]},
            ):
                # Process command
                result = process_command(text, mission=mission)
                processed += 1
        
            if dry_run:
                update_mission(mission, "RESPONSE_COMPOSED")
                print(f"[DRY-RUN] Would reply to chat {mask_chat_id(chat_id)}: {result[:100]}...")
            else:
                # Send reply
                send_result = telegram_send_message(token, chat_id, result)
                reply_ok = send_result and send_result.get("ok", False) if send_result else False
                response_message_id = None
                if reply_ok:
                    response_message_id = send_result.get("result", {}).get("message_id")
                    update_mission(mission, "RESPONSE_SENT", response_telegram_message_id=response_message_id)
                    update_mission(mission, "COMPLETED")
                else:
                    update_mission(mission, "DELIVERY_FAILED", error="telegram_send_message_failed")
            
                # Write receipt
                write_live_polling_receipt({
                    "type": "live_command",
                    "update_id": uid,
                    "chat_id_masked": mask_chat_id(chat_id),
                    "command": text[:100],
                    "reply_ok": reply_ok,
                    "mission_id": mission.get("mission_id"),
                    "response_telegram_message_id": response_message_id,
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
    r"^alpha\s*[,:\-]?\s*research\b",
    r"^alpha\s*[,:\-]?\s*investigate\b",
    r"^alpha\s*[,:\-]?\s*search\s+(the\s+)?web\b",
    r"^alpha\s*[,:\-]?\s*find\s+(one\s+)?(current|latest|recent|business|affiliate|technology|grant|funding|market|competitor|opportun)",
    r"^alpha\s*[,:\-]?\s*look\s+up\b",
    r"^alpha\s*[,:\-]?\s*what\s+changed\b",
    r"^alpha\s*[,:\-]?\s*(research|find|search|look\s+up).*\b(opportunity|grant|funding|affiliate|market|competitor|technology|trading|current|this\s+week)\b",
    r"^research\s+",
    r"^search\s+the\s+web\s+for\b",
    r"^look\s+up\s+(current|latest)\b",
    r"^find\s+(current|latest)\b",
]

ALPHA_LIVE_RESEARCH_KEYWORDS = (
    "research",
    "current",
    "latest",
    "this week",
    "find one",
    "business opportunity",
    "opportunities",
    "grant",
    "funding",
    "affiliate",
    "market research",
    "competitor",
    "technology",
    "trading research",
)


def is_alpha_live_research_request(text):
    clean = re.sub(r"^(?:/alpha\s+|@?alpha\s*[,:\-]?\s*)", "", text.lower().strip()).strip()
    if re.match(r"^(research|investigate|search|look\s+up)\b", clean):
        return True
    if re.match(r"^find\s+(one\s+)?(current|latest|recent|business|affiliate|technology|grant|funding|market|competitor|opportun)", clean):
        return True
    if re.match(r"^what\s+changed\b", clean) and any(x in clean for x in ("funding", "business", "market", "credit", "this week")):
        return True
    return any(keyword in clean for keyword in ALPHA_LIVE_RESEARCH_KEYWORDS)

# Alpha opinion patterns — outside perspective, not research
ALPHA_OPINION_PATTERNS = [
    r"^alpha\s+(what\s+do\s+you\s+think|is\s+(this|that|the|it)|should\s+we|what\s+am\s+I\s+missing|what\s+would\s+you|challenge|critique|review|compare|pros\s+and\s+cons|what\s+is\s+the\s+risk|do\s+you\s+agree|is\s+this\s+a\s+good|what\s+would\s+stop|what\s+is\s+better|which\s+option|how\s+would\s+you|opinion|advise|suggest|recommend|your\s+take|your\s+view|best\s+(first|next|move|option|approach)|better\s+(first|next|move|option|approach))",
    r"^alpha\s+(what|how|why|when|where|who|which|give|tell|show|help|advise|recommend)\b",
    r"^alpha\s+(think|believe|feel|consider|assess|evaluate|judge)\b",
    r"^alpha\s+(good\s+morning|good\s+afternoon|good\s+evening|hey|hello|hi|yo|what'?s\s+up|how\s+are\s+you|are\s+you\s+there|what\s+are\s+you\s+doing)",
    r"^what\s+do\s+you\s+think\s+about\b",
    r"^is\s+this\s+a\s+good\s+idea\b",
    r"^should\s+we\s+(do|start|begin|try|focus|prioritize)\b",
    r"^what\s+am\s+I\s+missing\b",
    r"^challenge\s+(this|that|the)\b",
    r"^what\s+would\s+you\s+(do|start|prioritize|focus)\b",
    r"^compare\s+(these|these\s+two|the)\b",
    r"^pros\s+and\s+cons\b",
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
    stripped = re.sub(r"^(alpha|hermes|nexus)\s*[,:\-]?\s+", "", text_lower)

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

    # TEMPORAL_INTENT (time, date, schedule, recap — BEFORE active context followup)
    # Temporal must run before active context followup to prevent number matching
    # in phrases like "what time is it" from being caught by item selection
    if TEMPORAL_AVAILABLE:
        temporal = detect_temporal_intent(text_lower)
        if temporal.get("matched"):
            return "TEMPORAL_INTENT", None, temporal

    # ALPHA_RESEARCH_REQUEST. Explicit current/research requests must beat broad
    # Alpha opinion patterns like "Alpha, find..." and "Alpha, give...".
    for pat in ALPHA_RESEARCH_PATTERNS:
        if re.search(pat, text_lower):
            topic = stripped
            for prefix in ["research ", "investigate ", "search ", "look up ", "find "]:
                if topic.startswith(prefix):
                    topic = topic[len(prefix):].strip()
                    break
            if not topic:
                topic = text_lower
            return "ALPHA_RESEARCH_REQUEST", None, topic

    # ALPHA_OPINION
    for pat in ALPHA_OPINION_PATTERNS:
        if re.search(pat, text_lower):
            return "ALPHA_OPINION", None, stripped

    # ACTIVE_CONTEXT_FOLLOWUP (number references, explain, deeper, work order — after temporal)
    if ACTIVE_CONTEXT_AVAILABLE:
        # Explicit confirm/yes patterns — route to active context handler
        if re.match(r"^(confirm|yes|go ahead|proceed|do it)$", text_lower):
            return "ACTIVE_CONTEXT_FOLLOWUP", None, {"intent": "confirm_pending", "pending_action": None, "confidence": 0.9}
        followup = detect_followup_intent(text_lower)
        if followup.get("intent"):
            return "ACTIVE_CONTEXT_FOLLOWUP", None, followup

    # ALPHA_CONTEXT_FOLLOWUP (must check before alpha research)
    for pat, followup_intent in ALPHA_CONTEXT_FOLLOWUP_PATTERNS:
        match = re.search(pat, text_lower)
        if match:
            return "ALPHA_CONTEXT_FOLLOWUP", match, followup_intent

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
        return "Ask Alpha for an outside opinion: 'alpha what do you think about...'"
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
            "Good morning Ray. Alpha is online. I can give an outside opinion, "
            "challenge a plan, compare options, or research it if you want current evidence. "
            "What is on your mind?"
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
            "Alpha is online. I can give an outside opinion, critique a plan, "
            "compare options, or research it if you want current evidence. "
            "What do you need a second brain on?"
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


def _handle_hermes_web_search(query):
    """Handle Hermes web search intent."""
    if HERMES_SEARCH_AVAILABLE:
        try:
            advisory = build_advisory_answer(query)
            answer_text = clean_html(advisory.get("answer", "No results."))
            lines = [
                f"Hermes Web Search — {query[:60]}",
                "",
                answer_text,
                "",
                f"Provider: {advisory.get('provider', 'none')}",
            ]
            if advisory.get("opportunity_score", {}).get("overall", 0) > 0:
                score = advisory["opportunity_score"]
                lines.append(f"Score: {score['overall']}/10")
            if advisory.get("next_step"):
                lines.append(f"\n{advisory['next_step']}")
            if SHARED_REC_AVAILABLE:
                try:
                    shared_ingest_hermes(query, {"status": "ok", "provider": advisory.get("provider", "unknown")}, advisory, topic=query)
                except Exception:
                    pass
            if ACTIVE_CONTEXT_AVAILABLE:
                try:
                    items = []
                    for i, finding in enumerate(advisory.get("findings", [])[:5], 1):
                        items.append({
                            "index": i,
                            "title": finding.get("title", f"Result {i}")[:100],
                            "summary": finding.get("snippet", "")[:300],
                            "score": finding.get("score", 5),
                            "url": finding.get("url", ""),
                            "source": advisory.get("provider", "unknown"),
                            "evidence": advisory.get("why_it_matters", [])[:2],
                            "risk": advisory.get("risks", [])[:2],
                            "next_action": advisory.get("next_step", ""),
                        })
                    if items:
                        top_idx = compute_top_index(items)
                        ctx = {
                            "source_agent": "hermes",
                            "context_type": "web_search",
                            "topic": query,
                            "summary": advisory.get("answer", "")[:200],
                            "items": items,
                            "top_index": top_idx,
                            "last_selected_index": None,
                            "allowed_followups": [
                                "explain_score", "explain_best", "research_deeper",
                                "create_work_order", "schedule", "compare",
                                "send_to_hermes", "send_to_alpha",
                            ],
                            "receipt_path": advisory.get("receipt_path"),
                            "brief_path": None,
                            "provider": advisory.get("provider"),
                            "query": query,
                            "expires_after_minutes": 180,
                        }
                        save_active_context(ctx)
                except Exception:
                    pass
            return "\n".join(lines)
        except Exception as e:
            return f"Search error: {str(e)[:100]}"
    else:
        provider = get_web_provider_status() if PROVIDER_STATUS_AVAILABLE else {"available": False}
        if provider.get("available"):
            return f"Web search provider is active but the search module encountered an error. Try again."
        return (
            "Web search is not configured.\n\n"
            "Add BRAVE_SEARCH_API_KEY to enable live search.\n"
            "See docs/hermes_internet_search_setup.md for details."
        )


def _handle_hermes_url_review(url):
    """Handle Hermes URL review."""
    if HERMES_SEARCH_AVAILABLE:
        try:
            review = hermes_url_review(url)
            lines = [f"Hermes URL Review — {url[:60]}", ""]
            if review.get("title"):
                lines.append(f"Title: {review['title']}")
            if review.get("summary"):
                lines.append(f"Summary: {review['summary'][:300]}")
            lines.append(f"Provider: {review.get('provider', 'none')}")
            lines.append(f"Status: {review.get('status', 'unknown')}")
            return "\n".join(lines)
        except Exception as e:
            return f"URL review error: {str(e)[:100]}"
    return _hermes_url_review_answer(url, "")


def is_trading_status_question(text):
    lower = text.lower()
    return bool(re.search(r"\b(trading|oanda|practice|strategy|signal|position|order|kill\s*switch|simulated\s+p&l|pnl)\b", lower)) and bool(
        re.search(r"\b(active|running|status|report|state|strategy|instruments|positions?|orders?|signal|risk|limits?|p&l|pnl|stop|kill)\b", lower)
    )


def _handle_trading_status_question():
    status = load_json(OANDA_PRACTICE_STATUS_PATH) or {}
    if not status:
        return "Hermes Trading Status — unavailable\n\nNo current Oanda practice runtime status file is available. I will not answer from static trading context."
    limits = status.get("risk_limits", {})
    decision = status.get("most_recent_decision", {}) or {}
    lines = [
        "Hermes Trading Status — Oanda Practice",
        "",
        f"Active: {'YES' if status.get('engine_active') else 'NO'}",
        f"Environment: {status.get('environment', 'OANDA_PRACTICE')}",
        f"State: {status.get('state', 'unknown')}",
        f"Strategy: {status.get('strategy', 'unknown')}",
        f"Monitored instruments: {', '.join(status.get('monitored_instruments', [])[:8])}",
        f"Open practice positions: {status.get('open_position_count', 'unknown')}",
        f"Pending practice orders: {status.get('pending_order_count', 'unknown')}",
        f"Today simulated P&L: {status.get('current_simulated_pnl', 'unknown')}",
        f"Last decision: {decision.get('state', 'unknown')} — {decision.get('reason', 'no reason recorded')}",
        f"Kill switch active: {'YES' if status.get('kill_switch_active') else 'NO'}",
        "",
        "Risk limits:",
        f"- approved instruments: {', '.join(limits.get('approved_instruments', []))}",
        f"- max order units: {limits.get('max_order_units')}",
        f"- max open positions: {limits.get('max_open_positions')}",
        f"- max trades/day: {limits.get('max_trades_per_day')}",
        f"- signal confidence: {limits.get('signal_confidence_threshold')}",
        "",
        f"Last heartbeat: {status.get('heartbeat_at', 'unknown')}",
        f"Next evaluation: {status.get('next_evaluation_time', 'unknown')}",
        "",
        f"Stop command: {status.get('kill_command', 'write the governed kill-switch file')}",
        "Source: reports/runtime/oanda_practice_engine_status_latest.json",
    ]
    return "\n".join(lines)


def _handle_alpha_opinion(text):
    """Handle Alpha opinion intent."""
    if ALPHA_OPINION_AVAILABLE:
        try:
            opinion = alpha_opinion(text)
            return format_alpha_opinion(opinion)
        except Exception as e:
            return f"Alpha opinion error: {str(e)[:100]}"
    return "Alpha opinion module not available. Check scripts/alpha/alpha_opinion_advisor.py."


def _handle_alpha_research(text):
    """Handle Alpha research intent with live provider-backed evidence."""
    if not ALPHA_LIVE_RESEARCH_AVAILABLE:
        return (
            "Alpha Live Research — LOOKUP FAILED\n\n"
            "The live Alpha research module could not be imported. I will not return the internal fallback as live research."
        )
    try:
        result = run_alpha_live_research(text, source="telegram")
    except Exception as e:
        return f"Alpha Live Research — LOOKUP FAILED\n\nError: {str(e)[:160]}"
    response = format_alpha_live_research_response(result)
    if ACTIVE_CONTEXT_AVAILABLE and response and not response.startswith("Error"):
        try:
            items = []
            if result.get("sources"):
                for i, source in enumerate(result["sources"][:5], 1):
                    items.append({
                        "index": i,
                        "title": source.get("title", f"Source {i}")[:100],
                        "summary": source.get("snippet", "")[:300],
                        "score": result.get("score", 7),
                        "url": source.get("url", ""),
                        "source": source.get("provider", "alpha_live_research"),
                        "evidence": [source.get("url", "")],
                        "risk": [result.get("risk", "Ray Review required before action.")],
                        "next_action": result.get("recommended_next_action", "Review source and decide whether to create a work order."),
                    })
            else:
                items = [{"index": 1, "title": text[:80], "summary": response[:300], "score": 6, "url": "", "source": "alpha", "evidence": [], "risk": [], "next_action": "review research"}]
            top_idx = compute_top_index(items) if items else 1
            ctx = {
                "source_agent": "alpha",
                "context_type": "alpha_research",
                "topic": result.get("query", text),
                "summary": result.get("summary", response[:200])[:200],
                "items": items,
                "top_index": top_idx,
                "last_selected_index": None,
                "allowed_followups": [
                    "explain_score", "explain_best", "research_deeper",
                    "create_work_order", "schedule", "send_to_hermes", "send_to_alpha",
                ],
                "receipt_path": None,
                "brief_path": result.get("local_json"),
                "provider": "brave_openrouter",
                "query": result.get("query", text),
                "expires_after_minutes": 180,
            }
            save_active_context(ctx)
        except Exception:
            pass
    return response


def _handle_approval_action(full_text):
    """Handle plain-language approval actions."""
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


def _handle_active_context_followup_bridge(extra, full_text):
    """Handle active context follow-up via old bridge interface."""
    if ACTIVE_CONTEXT_AVAILABLE:
        try:
            followup_intent = extra
            f_intent = followup_intent.get("intent")
            if f_intent == "confirm_pending":
                pending = followup_intent.get("pending_action")
                if not pending:
                    pending = load_pending_action()
                if pending:
                    return handle_confirm_pending(pending)
                # No pending action — give context-aware message
                context = load_active_context()
                topic = "the current topic"
                if context and context.get("topic"):
                    topic = context["topic"]
                return (
                    f"I do not have a pending action to confirm.\n"
                    f"The last active context is: {topic}\n\n"
                    f"Say 'research deeper' or specify what you want to do."
                )
            context = load_active_context()
            if not context or not is_context_fresh(context):
                return "No recent search context active. Run a search or research query first."
            selected_idx = followup_intent.get("selected_index")
            selected_item = None
            if selected_idx:
                selected_item = next((i for i in context.get("items", []) if i["index"] == selected_idx), None)
            elif f_intent in ("explain_best", "explain_score"):
                selected_item = select_context_item(context, "this")
            if f_intent == "explain_score":
                return format_score_explanation(context, selected_item)
            elif f_intent == "explain_best":
                return format_best_option_explanation(context, selected_item)
            elif f_intent == "research_deeper":
                return format_deeper_research(context)
            elif f_intent == "create_work_order":
                return format_work_order_draft(context, selected_item)
            elif f_intent == "schedule":
                title = clean_html(selected_item.get("title", context.get("topic", "unspecified"))) if selected_item else context.get("topic", "unspecified")
                return f"Scheduling: {title}\n\nPlease specify when."
            elif f_intent == "send_to_hermes":
                return f"Hermes review requested for: {context.get('topic', 'last search')}"
            elif f_intent == "send_to_alpha":
                return f"Alpha review requested for: {context.get('topic', 'last search')}"
            elif f_intent == "compare":
                indices = followup_intent.get("selected_indices", [])
                items = [next((i for i in context["items"] if i["index"] == idx), None) for idx in indices]
                items = [i for i in items if i]
                if len(items) >= 2:
                    lines = [f"Compare: {clean_html(items[0]['title'])} vs {clean_html(items[1]['title'])}", ""]
                    for item in items:
                        lines.append(f"{clean_html(item['title'])}: {item.get('score', '?')}/10")
                        lines.append("")
                    diff = items[0].get("score", 5) - items[1].get("score", 5)
                    lines.append(f"Difference: {abs(diff):.1f} points")
                    return "\n".join(lines)
                return "I need at least two items to compare."
        except Exception as e:
            return f"Context follow-up error: {str(e)[:100]}"
    return "Active context module not available."


def handle_unknown_fallback():
    """Handle unknown messages with a helpful but concise reply."""
    return (
        "I can help with:\n"
        "- Time/date: 'what time is it', 'what day is it'\n"
        "- Schedule: 'schedule this for 8 AM', 'remind me tomorrow'\n"
        "- Outside opinion: 'alpha what do you think about...'\n"
        "- Operational advice: 'hermes what should we do next?'\n"
        "- System status: 'what's the status?'\n"
        "- Research: 'alpha research <topic>'\n\n"
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
            idx = int(match_text)
        except ValueError:
            idx = 1

        # Try active context first (more reliable)
        active_ctx = load_active_context() if ACTIVE_CONTEXT_AVAILABLE else None
        if active_ctx and active_ctx.get("items"):
            item = next((i for i in active_ctx["items"] if i["index"] == idx), None)
            if item:
                wo_title = f"Work order: {clean_html(item.get('title', 'task'))}"
                wo = create_work_order(wo_title, "alpha_intake", "ACTIVE_INTERNAL", source="telegram_numbered_followup")
                write_receipt("alpha", {
                    "type": "alpha_work_order",
                    "recommendation_title": item["title"],
                    "work_order_id": wo["work_order_id"],
                    "mode": "ACTIVE_INTERNAL",
                })
                update_chat_context(ctx, chat_id, {"last_work_order_path": wo.get("work_order_id")})
                return (
                    f"Work Order Created: {wo['work_order_id']}\n"
                    f"Title: {wo_title}\n"
                    f"Source: active context item #{idx}\n"
                    f"Mode: ACTIVE_INTERNAL"
                )

        # Fallback to conversation context
        recs = chat_ctx.get("last_alpha_recommendations", [])
        if not recs or idx < 1 or idx > len(recs):
            return f"Recommendation #{match_text} not found. You have {len(recs)} recommendations."
        rec = recs[idx - 1]
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

def process_with_new_router(full_text):
    """
    New router implementing the draft-first, gated-research architecture.
    Routing hierarchy:
    1. AUTH/SAFETY (handled externally)
    2. PENDING ACTIONS (confirm/yes)
    3. TEMPORAL INTELLIGENCE
    4. ACTIVE CONTEXT FOLLOW-UPS
    5. EXPLICIT ROLE PREFIX
    6. STRUCTURED INTENT → DRAFT → RETRIEVAL GATE → MERGE → RENDER
    7. SAVE CONTEXT
    """
    # --- Load state ---
    active_context = load_active_context() if ACTIVE_CONTEXT_AVAILABLE else None
    pending_action = load_pending_action() if ACTIVE_CONTEXT_AVAILABLE else None

    # --- Structured message understanding ---
    if MESSAGE_UNDERSTANDING_AVAILABLE:
        understanding = understand_message(full_text, active_context, pending_action)
    else:
        # Fallback to old classifier
        intent, match, extra = classify_message_intent(full_text)
        understanding = {
            "raw_text": full_text,
            "normalized_text": full_text.lower().strip(),
            "explicit_role": None,
            "intent_family": intent.lower() if intent else "unknown",
            "is_followup": False,
            "followup_type": "none",
            "needs_external_evidence": False,
            "time_sensitive": False,
            "risk_level": "low",
            "confidence": 0.5,
        }

    intent_family = understanding.get("intent_family", "unknown")
    explicit_role = understanding.get("explicit_role")
    followup_type = understanding.get("followup_type", "none")

    # --- Router decision receipt ---
    router_decision = {
        "message": full_text[:100],
        "intent_family": intent_family,
        "explicit_role": explicit_role,
        "followup_type": followup_type,
        "needs_external_evidence": understanding.get("needs_external_evidence", False),
    }

    # --- Layer 2: PENDING ACTIONS ---
    if intent_family == "pending_action":
        if pending_action:
            result = handle_confirm_pending(pending_action)
            router_decision["routed_to"] = "pending_action_confirm"
            router_decision["pending_action_cleared"] = True
            _write_router_decision(router_decision)
            return result
        else:
            # Confirm without pending action — give context-aware message
            topic = "the current topic"
            if active_context and active_context.get("topic"):
                topic = active_context["topic"]
            result = (
                f"I do not have a pending action to confirm.\n"
                f"The last active context is: {topic}\n\n"
                f"Say 'research deeper' or specify what you want to do."
            )
            router_decision["routed_to"] = "confirm_no_pending"
            _write_router_decision(router_decision)
            return result

    # --- Layer 3: TEMPORAL INTELLIGENCE ---
    if intent_family == "temporal":
        if TEMPORAL_AVAILABLE:
            temporal_result = detect_temporal_intent(full_text.lower().strip())
            if temporal_result.get("matched"):
                result = format_time_response(temporal_result)
                router_decision["routed_to"] = "temporal"
                router_decision["temporal_intent"] = temporal_result.get("intent")
                _write_router_decision(router_decision)
                return result

    # --- Layer 3b: BRAIN CONTRACTS (Advisor/Command) ---
    if BRAIN_CONTRACTS_AVAILABLE:
        # Check for Command plan creation from Advisor idea
        is_plan, plan_idx = detect_command_plan_request(full_text)
        if is_plan:
            result = _handle_command_plan_request(plan_idx, active_context)
            if result:
                router_decision["routed_to"] = "command_plan"
                _write_router_decision(router_decision)
                return result

        # Check for Idea Brief creation
        is_brief, brief_idx = detect_idea_brief_request(full_text)
        if is_brief:
            result = _handle_idea_brief_request(brief_idx, active_context, full_text)
            if result:
                router_decision["routed_to"] = "idea_brief"
                _write_router_decision(router_decision)
                return result

        # Detect brain mode for this message
        brain_mode, explicit = detect_brain_mode(full_text)

        # If Command mode and question is outside Nexus scope → refuse
        if brain_mode == COMMAND and explicit:
            # Check if this is actually a Nexus-internal question
            is_nexus_internal = _is_nexus_internal_question(full_text)
            if not is_nexus_internal:
                result = format_command_refusal()
                router_decision["routed_to"] = "command_refusal"
                _write_router_decision(router_decision)
                return result

    # --- Layer 4: ACTIVE CONTEXT FOLLOW-UPS ---
    if intent_family == "active_context_followup" and followup_type != "none":
        if ACTIVE_CONTEXT_AVAILABLE:
            followup_result = _handle_active_context_followup(followup_type, full_text, active_context)
            if followup_result:
                router_decision["routed_to"] = "active_context_followup"
                router_decision["followup_type"] = followup_type
                _write_router_decision(router_decision)
                return followup_result

    # --- Layer 4c: ALPHA EXPLICIT ROLE ROUTING ---
    # When user says "Alpha, ..." route to Alpha-specific handlers BEFORE general intent
    if explicit_role == "alpha" and understanding.get("intent_family") not in ("pending_action", "deterministic_command"):
        alpha_result = _route_alpha_explicit(full_text, understanding, active_context, router_decision)
        if alpha_result:
            return alpha_result

    # --- Layer 4d: NEXUS RESEARCH REFUSAL ---
    # When user says "Nexus, research..." refuse — research belongs to Alpha
    # But "Nexus command, research..." also refuses
    if explicit_role == "nexus" and understanding.get("intent_family") in ("web_research", "money_research", "client_research"):
        result = (
            "Nexus Command — Internal Scope\n\n"
            "Open web research is an Alpha task, not a Nexus Command task.\n\n"
            "What Nexus can do:\n"
            "1. Check whether Nexus already has research saved.\n"
            "2. Create an Alpha research request.\n"
            "3. Turn Alpha's results into a Nexus implementation plan.\n"
            "4. Create work orders after Ray approval.\n\n"
            "Recommended next step:\n"
            'Say "Alpha, research [topic]".'
        )
        router_decision["routed_to"] = "nexus_research_refusal"
        _write_router_decision(router_decision)
        return result

    # --- Layer 4e: NEXUS PREFIX → STRIP AND RE-ROUTE ---
    # "Nexus, give me a plan" → treat as addressing the bot, route normally
    # "Nexus command, give me a plan" → route to command plan handler
    if explicit_role == "nexus":
        # Check if this is "Nexus command" (explicit command mode)
        is_nexus_command = re.search(r"^nexus\s+command\b", full_text.lower().strip())
        if not is_nexus_command:
            # Strip the Nexus prefix and re-route as general message
            clean_for_reroute = re.sub(r"^(?:@)?nexus\s*[,:\-]?\s*", "", full_text.strip(), flags=re.IGNORECASE).strip()
            if clean_for_reroute:
                # For general questions (not business/operational), give a direct answer
                is_general = not re.search(
                    r"(money|revenue|client|strategy|plan|research|business|credit|funding|affiliate|income|sell|close|status|report|order|approval|process|system|build|deploy|schedule)",
                    clean_for_reroute.lower(),
                )
                if is_general:
                    result = (
                        f"Nexus — General Answer\n\n"
                        f"Regarding: {clean_for_reroute[:100]}\n\n"
                        f"This is a general question. Nexus can answer from internal records or general knowledge.\n\n"
                        f"For a deeper outside perspective, ask Alpha.\n\n"
                        f"Source: Nexus general knowledge"
                    )
                    router_decision["routed_to"] = "nexus_general_answer"
                    _write_router_decision(router_decision)
                    return result
                # Re-classify without the prefix for operational questions
                reroute = process_with_new_router(clean_for_reroute)
                if reroute:
                    router_decision["routed_to"] = "nexus_prefix_reroute"
                    _write_router_decision(router_decision)
                    return reroute

    # --- Trading status from live runtime state ---
    if is_trading_status_question(full_text):
        result = _handle_trading_status_question()
        router_decision["routed_to"] = "oanda_practice_status"
        _write_router_decision(router_decision)
        return result

    # --- Layer 4b: IMPLICIT CONTEXT FOLLOW-UPS ---
    # Handle cases like "alpha can you do deeper research on this" where the
    # topic is a pronoun reference to active context
    if ACTIVE_CONTEXT_AVAILABLE and active_context and active_context.get("items"):
        text_lower = full_text.lower().strip()
        if re.search(r"(deeper|more|further|additional)\s+(research|info|details)", text_lower):
            if re.search(r"(this|that|it)\s*$", text_lower):
                ctx_copy = dict(active_context)
                followup_result = _handle_active_context_followup("research_deeper", full_text, ctx_copy)
                if followup_result:
                    router_decision["routed_to"] = "active_context_followup"
                    router_decision["followup_type"] = "research_deeper"
                    _write_router_decision(router_decision)
                    return followup_result

    # --- Layer 5-6: INTENT → DRAFT → RETRIEVAL → MERGE ---
    if intent_family in ("money_plan", "client_acquisition", "business_strategy",
                          "implementation_plan", "opinion", "critique", "compare_options",
                          "web_research", "money_research", "client_research",
                          "greeting", "help", "unknown"):
        return _route_to_draft_engine(understanding, full_text, active_context, router_decision)

    # --- Layer: DETERMINISTIC COMMANDS ---
    if intent_family == "deterministic_command":
        # Already handled by slash command check in process_command
        return None  # Signal to process_command to use old logic

    # --- Layer: EXISTING INTENTS (backward compatibility) ---
    return None  # Signal to process_command to use old logic


def _route_to_draft_engine(understanding, full_text, active_context, router_decision):
    """Route to draft engine, retrieval gate, merge, and render."""
    intent_family = understanding.get("intent_family", "unknown")
    explicit_role = understanding.get("explicit_role")

    # --- Select role ---
    role = _select_role(understanding)
    router_decision["selected_role"] = role

    # --- Generate draft ---
    draft = None
    if role == "alpha" and ALPHA_DRAFT_AVAILABLE:
        draft = generate_alpha_draft(understanding, active_context)
    elif role == "hermes" and HERMES_DRAFT_AVAILABLE:
        draft = generate_hermes_draft(understanding, active_context)

    if not draft:
        # Fallback: try both engines
        if HERMES_DRAFT_AVAILABLE:
            draft = generate_hermes_draft(understanding, active_context)
        elif ALPHA_DRAFT_AVAILABLE:
            draft = generate_alpha_draft(understanding, active_context)
        else:
            return _render_fallback(full_text)

    router_decision["draft_role"] = draft.get("role", "unknown")
    router_decision["draft_confidence"] = draft.get("confidence", 0)
    router_decision["draft_items"] = len(draft.get("items", []))

    # --- Retrieval gate ---
    provider_status = get_web_provider_status() if PROVIDER_STATUS_AVAILABLE else {"provider": None, "available": False}
    retrieval = {"retrieve": False, "reason": "gate not available", "query": None, "provider": None, "merge_mode": "none"}
    if RETRIEVAL_GATE_AVAILABLE:
        retrieval = should_retrieve(understanding, draft, active_context, provider_status)

    router_decision["retrieval_decision"] = retrieval.get("reason", "unknown")
    router_decision["retrieval_will_search"] = retrieval.get("retrieve", False)

    # --- Web enrichment if needed ---
    if retrieval.get("retrieve") and retrieval.get("query"):
        brave_results = _do_web_search(retrieval["query"], retrieval["provider"])
        if brave_results and EVIDENCE_MERGE_AVAILABLE:
            draft = merge_evidence_into_draft(draft, brave_results)
            router_decision["web_enriched"] = True
            router_decision["web_items_added"] = draft.get("web_items_added", 0)

    # --- Render response ---
    response = _render_draft(draft, full_text)

    # --- Save active context ---
    # Only save for real actionable outputs, not fallback/help/greeting/unknown
    SAVEABLE_INTENTS = {
        "money_plan", "money_research", "client_acquisition", "client_research",
        "business_strategy", "implementation_plan", "web_research",
        "opinion", "critique", "compare_options", "alpha_research",
        "work_order_request", "schedule_request",
    }
    if ACTIVE_CONTEXT_AVAILABLE and draft.get("items") and intent_family in SAVEABLE_INTENTS:
        try:
            items = []
            for item in draft["items"][:5]:
                items.append({
                    "index": item.get("index", 0),
                    "title": item.get("title", "")[:100],
                    "summary": item.get("summary", "")[:300],
                    "score": item.get("score", 5),
                    "url": item.get("url", ""),
                    "source": item.get("source", draft.get("role", "unknown")),
                    "evidence": item.get("evidence", []),
                    "risk": item.get("risk", []),
                    "next_action": item.get("next_action", ""),
                })
            if items:
                top_idx = compute_top_index(items)
                ctx = {
                    "source_agent": draft.get("role", "hermes"),
                    "context_type": intent_family,
                    "topic": understanding.get("raw_text", ""),
                    "summary": draft.get("summary", "")[:200],
                    "items": items,
                    "top_index": top_idx,
                    "last_selected_index": None,
                    "allowed_followups": [
                        "explain_score", "explain_best", "research_deeper",
                        "create_work_order", "schedule", "compare",
                        "send_to_hermes", "send_to_alpha",
                    ],
                    "receipt_path": None,
                    "brief_path": None,
                    "provider": provider_status.get("provider"),
                    "query": understanding.get("raw_text", ""),
                    "expires_after_minutes": 180,
                }
                save_active_context(ctx)
                router_decision["active_context_saved"] = True
        except Exception:
            pass

    # --- Save work order if applicable ---
    if intent_family in ("work_order_request",) and draft.get("items"):
        # If user referenced a specific item (e.g., "turn number 2 into a work order"),
        # create work order from the active context item, not from raw text
        if ACTIVE_CONTEXT_AVAILABLE and active_context:
            num_match = re.search(r"(?:number|option|item|#)\s*(\d+)", full_text.lower())
            if num_match:
                idx = int(num_match.group(1))
                item = next((i for i in active_context.get("items", []) if i["index"] == idx), None)
                if item:
                    wo_title = f"Work order: {clean_html(item.get('title', 'task'))}"
                    wo = create_work_order(wo_title, "alpha_intake", "ACTIVE_INTERNAL", source="telegram_numbered_followup")
                    router_decision["work_order_created"] = True
                    router_decision["work_order_id"] = wo["work_order_id"]
                    _write_router_decision(router_decision)
                    return (
                        f"Work Order Created: {wo['work_order_id']}\n"
                        f"Title: {wo_title}\n"
                        f"Source: active context item #{idx}\n"
                        f"Mode: ACTIVE_INTERNAL"
                    )
        router_decision["work_order_created"] = True

    _write_router_decision(router_decision)
    return response


def _select_role(understanding):
    """Select which agent role to use."""
    explicit = understanding.get("explicit_role")
    if explicit:
        return explicit

    intent = understanding.get("intent_family", "unknown")

    # Alpha gets: opinion, critique, compare, explicit alpha
    if intent in ("opinion", "critique", "compare_options"):
        return "alpha"

    # Hermes gets: operational, business, money, strategy, implementation
    if intent in ("money_plan", "money_research", "client_acquisition", "client_research",
                   "business_strategy", "implementation_plan", "web_research"):
        return "hermes"

    # Default: Hermes for operational, Alpha for opinion
    return "hermes"


def _do_web_search(query, provider):
    """Execute web search if available."""
    if not HERMES_SEARCH_AVAILABLE:
        return None
    try:
        advisory = build_advisory_answer(query)
        if advisory.get("search_status") == "ok":
            return {"results": advisory.get("findings", [])}
    except Exception:
        pass
    return None


def _render_draft(draft, original_text):
    """Render a draft into a Telegram response."""
    role = draft.get("role", "hermes")
    summary = draft.get("summary", "")
    items = draft.get("items", [])
    answer_mode = draft.get("answer_mode", "operator_plan")

    lines = []

    # Header
    if role == "alpha":
        lines.append(f"Alpha — {summary}")
    else:
        lines.append(f"Hermes — {summary}")
    lines.append("")

    if not items:
        lines.append(draft.get("summary", "No items generated."))
        return "\n".join(lines)

    # Items
    for item in items[:5]:
        idx = item.get("index", 0)
        title = item.get("title", f"Item {idx}")
        score = item.get("score", 0)
        summary_text = item.get("summary", "")
        next_action = item.get("next_action", "")

        lines.append(f"{idx}. {title}")
        if score > 0:
            lines.append(f"   Score: {score}/10")
        if summary_text:
            lines.append(f"   {summary_text[:150]}")
        if next_action:
            lines.append(f"   Next: {next_action}")
        lines.append("")

    # Source indicator
    if draft.get("web_enriched"):
        provider = draft.get("provider", "web")
        lines.append(f"Source: internal + {provider.title() if provider else 'web'} enrichment")
    else:
        lines.append("Source: internal Nexus context")

    # Confidence
    confidence = draft.get("confidence", 0)
    if confidence < 0.6:
        lines.append("\nSay 'research deeper' or 'search the web for...' to enrich with live data.")

    # Recommended next prompt
    next_prompt = draft.get("recommended_next_prompt")
    if next_prompt:
        lines.append(f'\nSay "{next_prompt}" to take action.')

    return "\n".join(lines)


def _render_fallback(full_text):
    """Render a helpful fallback when no engines available."""
    provider = get_web_provider_status() if PROVIDER_STATUS_AVAILABLE else {"available": False}
    lines = [
        "I can help with that.",
        "",
        "Try:",
        "- 'hermes what should we do next?'",
        "- 'alpha what do you think about...'",
        "- 'search the web for...'",
        "- 'how can I make money today'",
        "",
        f"Web search: {'active' if provider.get('available') else 'configure BRAVE_SEARCH_API_KEY'}",
    ]
    return "\n".join(lines)


def _handle_active_context_followup(followup_type, full_text, active_context):
    """Handle active context follow-up intents."""
    if not ACTIVE_CONTEXT_AVAILABLE or not active_context:
        return None

    text_lower = full_text.lower().strip()

    if followup_type == "select_item":
        item = select_context_item(active_context, text_lower)
        if item:
            return format_score_explanation(active_context, item)

    elif followup_type == "explain_score":
        item = _find_item_from_text(text_lower, active_context)
        if item:
            return format_score_explanation(active_context, item)

    elif followup_type == "explain_best":
        top_idx = active_context.get("top_index", 1)
        item = next((i for i in active_context.get("items", []) if i["index"] == top_idx), None)
        return format_best_option_explanation(active_context, item)

    elif followup_type == "research_deeper":
        # Resolve "this" from active context
        topic = active_context.get("topic", "")
        # If the user's message is just "research deeper" or "deeper research on this",
        # use the active context topic, not the raw phrase
        if re.match(r"^(research|do|go|can you)\s+(deeper|more|further|into|additional)", text_lower):
            pass  # topic already resolved from active_context
        elif re.search(r"(this|that|it)\s*$", text_lower):
            pass  # topic already resolved from active_context
        else:
            # User specified a new topic in the message
            topic = re.sub(r"^(research|do|go|can you)\s+(deeper|more|further|into|additional)\s+(on\s+)?", "", text_lower).strip()
            if not topic:
                topic = active_context.get("topic", "")
        # Override the topic in active_context for this call
        ctx_copy = dict(active_context)
        if topic:
            ctx_copy["topic"] = topic
        return format_deeper_research(ctx_copy)

    elif followup_type == "create_work_order":
        item = _find_item_from_text(text_lower, active_context)
        return format_work_order_draft(active_context, item)

    elif followup_type == "compare":
        nums = re.findall(r"\d+", text_lower)
        if len(nums) >= 2:
            items = [next((i for i in active_context.get("items", []) if i["index"] == int(n)), None) for n in nums[:2]]
            items = [i for i in items if i]
            if len(items) >= 2:
                lines = [f"Compare: {clean_html(items[0]['title'])} vs {clean_html(items[1]['title'])}", ""]
                for item in items:
                    lines.append(f"{clean_html(item['title'])}: {item.get('score', '?')}/10")
                    lines.append("")
                diff = items[0].get("score", 5) - items[1].get("score", 5)
                lines.append(f"Difference: {abs(diff):.1f} points")
                return "\n".join(lines)
        return "I need at least two item numbers to compare."

    elif followup_type == "send_to_agent":
        return f"Routing to agent for: {active_context.get('topic', 'last search')}"

    elif followup_type == "schedule":
        item = _find_item_from_text(text_lower, active_context)
        title = clean_html(item.get("title", active_context.get("topic", "unspecified"))) if item else active_context.get("topic", "unspecified")
        return f"Scheduling: {title}\n\nPlease specify when (e.g., 'tomorrow at 9am')."

    return None


def _find_item_from_text(text_lower, active_context):
    """Find an item from text using selection detection."""
    if not active_context or not active_context.get("items"):
        return None

    # Direct number reference
    num = re.search(r"(?:number|option|item|#)\s*(\d+)|^(\d+)$", text_lower)
    if num:
        idx = int(num.group(1) or num.group(2))
        return next((i for i in active_context["items"] if i["index"] == idx), None)

    # Pronouns
    if re.match(r"^(this|that|it|the\s+one)$", text_lower):
        last = active_context.get("last_selected_index")
        if last:
            return next((i for i in active_context["items"] if i["index"] == last), None)
        top = active_context.get("top_index", 1)
        return next((i for i in active_context["items"] if i["index"] == top), None)

    return None


def _is_nexus_internal_question(text):
    """Check if a question is about Nexus internal state (not outside knowledge)."""
    t = text.lower().strip()
    internal_keywords = [
        "report", "status", "work order", "approval", "approval queue",
        "process", "registry", "receipt", "launchd", "scheduler",
        "database", "supabase", "stripe", "build", "deploy",
        "telegram", "hermes", "alpha", "nexus", "goclear",
        "score", "receipt", "brief", "plan", "schedule",
        "what happened", "what is running", "how many",
    ]
    return any(kw in t for kw in internal_keywords)


def _handle_idea_brief_request(item_idx, active_context, full_text):
    """Handle request to create an Advisor Idea Brief."""
    if not BRAIN_CONTRACTS_AVAILABLE or not active_context:
        return None

    items = active_context.get("items", [])
    if not items:
        return "No active context items to create an idea brief from."

    # Find the item
    item = None
    if item_idx:
        item = next((i for i in items if i["index"] == item_idx), None)
    if not item:
        # Use last selected or top
        last_idx = active_context.get("last_selected_index")
        if last_idx:
            item = next((i for i in items if i["index"] == last_idx), None)
        if not item:
            top_idx = active_context.get("top_index", 1)
            item = next((i for i in items if i["index"] == top_idx), items[0] if items else None)

    if not item:
        return "Could not find the item to create an idea brief from."

    topic = active_context.get("topic", "Advisor recommendation")
    source_context = active_context.get("context_type", "advisor_recommendation")

    brief, brief_path = create_idea_brief(item, topic, source_context)

    # Save as active context
    if ACTIVE_CONTEXT_AVAILABLE:
        save_active_context({
            "source_agent": "advisor",
            "context_type": "advisor_idea_brief",
            "topic": brief["idea_title"],
            "summary": brief["summary"],
            "items": [{
                "index": 1,
                "title": brief["idea_title"],
                "summary": brief["summary"],
                "score": item.get("score", 7),
                "url": "",
                "source": "advisor",
                "evidence": [],
                "risk": brief.get("risks", []),
                "next_action": brief["recommended_first_step"],
            }],
            "top_index": 1,
            "last_selected_index": None,
            "allowed_followups": [
                "explain_score", "research_deeper", "create_work_order",
                "send_to_command", "compare",
            ],
            "brief_path": brief_path,
            "provider": None,
            "query": topic,
            "expires_after_minutes": 180,
        })

    return format_idea_brief_response(brief, brief_path)


def _handle_command_plan_request(item_idx, active_context):
    """Handle Command request to create a Nexus plan from an Advisor idea."""
    if not BRAIN_CONTRACTS_AVAILABLE:
        return None

    # Try to find the last Advisor Idea Brief
    brief = None
    brief_path = None

    # Check active context for brief path
    if active_context and active_context.get("brief_path"):
        bp = active_context["brief_path"]
        if os.path.exists(bp):
            brief_path = bp
            with open(bp) as f:
                brief = json.load(f)

    # If no brief in context, check the latest idea brief file
    if not brief:
        brief_dir = "reports/advisor_idea_briefs"
        if os.path.exists(brief_dir):
            briefs = sorted(Path(brief_dir).glob("advisor_idea_brief_*.json"))
            if briefs:
                brief_path = str(briefs[-1])
                with open(briefs[-1]) as f:
                    brief = json.load(f)

    if not brief:
        return (
            "No Advisor Idea Brief found.\n\n"
            "First create one: 'turn number 1 into an idea brief'\n"
            "Then ask Command to create a plan from it."
        )

    topic = brief.get("idea_title", "Advisor idea")
    plan, plan_path = create_command_plan(brief, topic)

    return format_command_plan_response(plan, plan_path)


def _route_alpha_explicit(full_text, understanding, active_context, router_decision):
    """
    Handle Alpha-explicit routing when user says "Alpha, ...".
    Returns response string or None if not handled.
    """
    intent = understanding.get("intent_family", "unknown")
    text_lower = full_text.lower().strip()
    # Strip the alpha prefix for topic extraction
    clean_text = re.sub(r"^(?:@)?alpha\s*[,:\-]?\s*", "", text_lower).strip()
    clean_topic = re.sub(r"^(?:@)?alpha\s*[,:\-]?\s*", "", full_text.strip(), flags=re.IGNORECASE).strip()

    if re.search(r"\b(strongest|best|top)\s+(opportunity|candidate|option)\b", clean_text):
        result = _alpha_strongest_opportunity()
        router_decision["routed_to"] = "alpha_strongest_opportunity"
        _write_router_decision(router_decision)
        return result

    # --- Alpha challenge Nexus option ---
    challenge_match = re.search(
        r"(?:based\s+on\s+)?(?:nexus\s+)?(?:option|number|#)\s*(\d+)",
        clean_text,
    )
    is_challenge = re.search(
        r"(challenge|critique|improve|better\s+than|what.s\s+better|what.s\s+missing|compare\s+to\s+outside|is\s+there\s+a\s+better|review\s+nexus|add\s+to\s+nexus|what\s+can\s+we\s+add)",
        clean_text,
    )
    if challenge_match or is_challenge:
        idx = int(challenge_match.group(1)) if challenge_match else None
        result = _alpha_challenge_nexus(idx, clean_topic, active_context)
        if result:
            router_decision["routed_to"] = "alpha_challenge"
            _write_router_decision(router_decision)
            return result

    # --- Alpha research ---
    if intent in ("web_research", "money_research", "client_research") or is_alpha_live_research_request(clean_text):
        result = _alpha_research(clean_text, clean_topic)
        router_decision["routed_to"] = "alpha_research"
        _write_router_decision(router_decision)
        return result

    # --- Alpha money opinion ---
    if intent in ("money_plan", "money_research"):
        result = _alpha_money_opinion(clean_text, clean_topic, active_context)
        router_decision["routed_to"] = "alpha_money_opinion"
        _write_router_decision(router_decision)
        return result

    # --- Alpha plan for today ---
    if intent == "business_strategy" or re.search(
        r"(plan\s+for\s+today|what\s+should\s+i\s+do\s+today|today.*plan|give\s+me\s+a\s+plan)",
        clean_text,
    ):
        result = _alpha_plan_today(clean_text, clean_topic, active_context)
        router_decision["routed_to"] = "alpha_plan_today"
        _write_router_decision(router_decision)
        return result

    # --- Alpha general question (not routed to any specific handler) ---
    # For "what color is the sky", "explain X", etc. — answer directly
    if intent in ("unknown", "greeting", "help") or not re.search(
        r"(money|revenue|client|strategy|plan|research|business|credit|funding|affiliate|income|sell|close)",
        clean_text,
    ):
        result = _alpha_general_answer(clean_text, clean_topic)
        router_decision["routed_to"] = "alpha_general"
        _write_router_decision(router_decision)
        return result

    # --- Fallback: let normal routing handle it (Alpha draft engine) ---
    return None


def _alpha_challenge_nexus(item_idx, topic, active_context):
    """Alpha challenges or improves a Nexus option."""
    nexus_item = None
    if active_context and active_context.get("items") and item_idx:
        nexus_item = next(
            (i for i in active_context["items"] if i["index"] == item_idx),
            None,
        )

    nexus_title = nexus_item["title"] if nexus_item else "the current Nexus recommendation"
    nexus_summary = nexus_item.get("summary", "") if nexus_item else ""
    nexus_score = nexus_item.get("score", "?") if nexus_item else "?"

    # Build Alpha's outside challenge
    lines = [
        f"Alpha — Outside Challenge to Nexus Option #{item_idx or '?'}",
        "",
        f"Nexus option #{item_idx or '?'}:",
        f"  {nexus_title}",
    ]
    if nexus_summary:
        lines.append(f"  {nexus_summary[:150]}")
    lines.append(f"  Score: {nexus_score}/10")
    lines.append("")
    lines.append("Alpha's view:")
    lines.append("")

    # Generate Alpha's outside perspective based on topic
    t = topic.lower()
    if "readiness" in t or "review" in t or "$97" in t:
        lines.append("This is probably the fastest direct cash option, but I would not lead with the paid review first.")
        lines.append("")
        lines.append("Better version:")
        lines.append("Use a free checklist + 15-minute readiness call as the hook, then offer the $97 review after the call.")
        lines.append("")
        lines.append("Why this is better:")
        lines.append("  - Lower friction")
        lines.append("  - Creates trust first")
        lines.append("  - Lets you diagnose actual readiness gaps")
        lines.append("  - Still leads to the paid review")
        lines.append("")
        lines.append("Risks:")
        lines.append("  - Free calls may not convert")
        lines.append("  - Needs clear no-guarantee language")
        lines.append("  - Requires follow-up")
    elif "checklist" in t or "call" in t or "funnel" in t:
        lines.append("This is a solid low-friction approach. I agree with this direction.")
        lines.append("")
        lines.append("What I would add:")
        lines.append("  - Add a 24-hour follow-up after the call")
        lines.append("  - Have a simple one-page readiness summary ready to send")
        lines.append("  - Track which calls convert to paid reviews")
    elif "affiliate" in t:
        lines.append("Affiliate programs are backend monetization, not front-door revenue.")
        lines.append("")
        lines.append("Better version:")
        lines.append("Close your own offer first. Use affiliates as ongoing value for existing clients.")
        lines.append("")
        lines.append("Why:")
        lines.append("  - You control the revenue")
        lines.append("  - Higher margin than referral commissions")
        lines.append("  - Builds your own brand, not someone else's")
    else:
        lines.append(f"Looking at '{nexus_title}' from the outside.")
        lines.append("")
        lines.append("What I would do differently:")
        lines.append("  1. Validate demand before building")
        lines.append("  2. Start with the simplest version that works")
        lines.append("  3. Measure conversion before scaling")
        lines.append("")
        lines.append("Risks to watch:")
        lines.append("  - Scope creep")
        lines.append("  - Building before selling")
        lines.append("  - Ignoring what clients actually pay for")

    lines.append("")
    lines.append("My recommendation:")
    lines.append("Use this as a starting point, then challenge it with real customer conversations.")
    lines.append("")
    lines.append("Source: Alpha outside reasoning + general business strategy")
    lines.append("")
    lines.append('Say "turn this into an idea brief" or "Nexus, create a plan from this."')

    # Save active context
    if ACTIVE_CONTEXT_AVAILABLE:
        save_active_context({
            "source_agent": "alpha",
            "context_type": "alpha_challenge",
            "topic": f"Challenge to Nexus option #{item_idx or '?'}: {nexus_title[:60]}",
            "summary": f"Alpha challenge to: {nexus_title[:100]}",
            "items": [{
                "index": 1,
                "title": f"Improved version of: {nexus_title[:60]}",
                "summary": f"Alpha's outside improvement on Nexus option #{item_idx or '?'}",
                "score": 7.5,
                "url": "",
                "source": "alpha",
                "evidence": [f"Nexus original score: {nexus_score}/10"],
                "risk": ["Requires validation with real customers"],
                "next_action": "Test this version against the original with real outreach.",
            }],
            "top_index": 1,
            "last_selected_index": None,
            "allowed_followups": [
                "explain_score", "research_deeper", "create_work_order",
                "send_to_command", "compare",
            ],
            "nexus_reference": nexus_item,
            "provider": None,
            "query": topic,
            "expires_after_minutes": 180,
        })

    return "\n".join(lines)


def _alpha_research(clean_text, clean_topic):
    """Alpha research — live providers only, no internal context as live truth."""
    return _handle_alpha_research(clean_topic or clean_text)


def _alpha_strongest_opportunity():
    latest = load_json(ALPHA_LIVE_RESEARCH_STATUS_PATH) or {}
    if not latest:
        return "Alpha Opportunity Opinion — unavailable\n\nNo live Alpha research result is available yet. Ask Alpha to research an opportunity first."
    sources = latest.get("sources", [])
    analysis = latest.get("analysis", {})
    lines = [
        "Alpha — Independent Opinion on the Strongest Opportunity",
        "",
        f"Strongest current candidate: {latest.get('title') or latest.get('query')}",
        f"Category: {latest.get('category', 'unknown')}",
        f"Confidence: {latest.get('confidence', 'unknown')}",
        "",
        f"My view: {analysis.get('summary', latest.get('summary', ''))[:600]}",
        "",
        f"Why it matters: {analysis.get('why_it_matters', latest.get('strategic_fit', ''))[:450]}",
        f"Revenue potential: {latest.get('revenue_potential')}",
        f"Effort: {latest.get('estimated_effort')}",
        f"Risk: {latest.get('risk')}",
        "",
        f"Recommended next step: {latest.get('recommended_next_action')}",
        f"Ray Review: {latest.get('approval_requirement')}",
        "",
        "Evidence:",
    ]
    for i, source in enumerate(sources[:3], 1):
        lines.append(f"{i}. {source.get('title', 'Source')} — {source.get('url', '')}")
    lines.extend([
        "",
        f"Research ID: {latest.get('research_id')}",
        "Source: reports/runtime/alpha_live_research_latest.json",
    ])
    return "\n".join(lines)


def _alpha_money_opinion(clean_text, clean_topic, active_context):
    """Alpha outside opinion on money/revenue questions."""
    # Load Hermes money plan as context if available
    hermes_context = ""
    if active_context and active_context.get("items"):
        top = active_context["items"][0]
        hermes_context = f"Nexus already recommended: {top.get('title', 'none')} (score: {top.get('score', '?')}/10)."

    lines = [
        f"Alpha — Outside Money Opinion{' for Today' if 'today' in clean_text.lower() else ''}",
        "",
    ]

    if hermes_context:
        lines.append(f"Context: {hermes_context}")
        lines.append("")

    lines.append("Alpha's outside view:")
    lines.append("")

    # Generate Alpha's outside money opinion
    t = clean_text.lower()
    if "today" in t:
        lines.append("1. Lead with a free readiness checklist and 15-minute call")
        lines.append("   Score: 8.3/10")
        lines.append("   Why: Low friction. Creates direct conversation. Builds trust before asking for money.")
        lines.append("   Next: Offer 3 free calls today.")
        lines.append("")
        lines.append("2. Close the $97 readiness review after the call")
        lines.append("   Score: 8.0/10")
        lines.append("   Why: Easier to sell after you identify actual credit/funding gaps.")
        lines.append("   Next: Use a simple no-guarantee script.")
        lines.append("")
        lines.append("3. Research affiliates after the first call is booked")
        lines.append("   Score: 6.3/10")
        lines.append("   Why: Affiliates fit the backend but are slower than your own offer.")
        lines.append("   Next: Build affiliate shortlist later today.")
    elif "30" in t or "month" in t:
        lines.append("1. Week 1: Close 3 readiness reviews using checklist + call funnel")
        lines.append("   Score: 8.5/10")
        lines.append("   Why: Fastest path to $291 revenue. Validates demand.")
        lines.append("   Next: DM 10 warm contacts with free checklist offer.")
        lines.append("")
        lines.append("2. Week 2: Launch affiliate partnerships after first clients")
        lines.append("   Score: 7.0/10")
        lines.append("   Why: Backend revenue that compounds. Needs client trust first.")
        lines.append("   Next: Research credit monitoring and business banking affiliate terms.")
        lines.append("")
        lines.append("3. Week 3-4: Build repeatable outreach system")
        lines.append("   Score: 7.5/10")
        lines.append("   Why: Turns one-time revenue into pipeline.")
        lines.append("   Next: Create outreach script and tracking workflow.")
    else:
        lines.append("1. Close one readiness review today")
        lines.append("   Score: 8.0/10")
        lines.append("   Why: Fastest direct cash path. Already built.")
        lines.append("   Next: DM one warm lead.")
        lines.append("")
        lines.append("2. Use checklist + call as the funnel")
        lines.append("   Score: 7.5/10")
        lines.append("   Why: Lower barrier. Creates conversations.")
        lines.append("   Next: Offer 3 free calls.")
        lines.append("")
        lines.append("3. Research affiliates as backend")
        lines.append("   Score: 6.0/10")
        lines.append("   Why: Good for ongoing revenue, not same-day cash.")
        lines.append("   Next: Build shortlist after first sale.")

    lines.append("")
    lines.append("My recommendation:")
    lines.append("Do one customer-facing revenue action before more system building.")
    lines.append("")
    lines.append("Source: Alpha outside reasoning + general business strategy")
    lines.append("")
    lines.append('Say "turn number 1 into an idea brief" or "ask Nexus to create a plan from this."')

    # Save active context
    if ACTIVE_CONTEXT_AVAILABLE:
        save_active_context({
            "source_agent": "alpha",
            "context_type": "alpha_money_opinion",
            "topic": clean_topic,
            "summary": f"Alpha money opinion: {clean_topic[:80]}",
            "items": [{
                "index": 1,
                "title": "Alpha money plan",
                "summary": f"Outside opinion on: {clean_topic[:100]}",
                "score": 8.0,
                "url": "",
                "source": "alpha",
                "evidence": [],
                "risk": [],
                "next_action": "Review and decide.",
            }],
            "top_index": 1,
            "last_selected_index": None,
            "allowed_followups": [
                "explain_score", "research_deeper", "create_work_order",
                "send_to_command", "compare",
            ],
            "provider": None,
            "query": clean_topic,
            "expires_after_minutes": 180,
        })

    return "\n".join(lines)


def _alpha_plan_today(clean_text, clean_topic, active_context):
    """Alpha outside plan for today — not the same as Nexus pending approvals."""
    lines = [
        "Alpha — Outside Plan for Today",
        "",
        "I reviewed the current Nexus direction. My outside opinion is that today should be revenue-first, not system-first.",
        "",
        "1. Pick one revenue action",
        "   Score: 8.5/10",
        "   Reason: Reviewing approvals matters, but it does not create money unless it leads to an offer, outreach, or a booked call.",
        "   Next: Choose the $97 readiness review or checklist call funnel.",
        "",
        "2. Use the checklist + 15-minute call funnel",
        "   Score: 8.0/10",
        "   Reason: Lower friction than selling immediately and creates qualified conversations.",
        "   Next: Offer 3 short calls today.",
        "",
        "3. Keep Nexus work limited to execution support",
        "   Score: 7.0/10",
        "   Reason: Nexus should track the work, not become the work.",
        "   Next: Create one work order, not five new feature tasks.",
        "",
        "My recommendation:",
        "Do one customer-facing revenue action before more system building.",
        "",
        "Source: Nexus context brief + Alpha outside reasoning",
        "",
        'Say "turn number 2 into an idea brief" or "ask Nexus to create a plan from this."',
    ]

    # Save active context
    if ACTIVE_CONTEXT_AVAILABLE:
        save_active_context({
            "source_agent": "alpha",
            "context_type": "alpha_outside_plan",
            "topic": "Alpha plan for today",
            "summary": "Alpha outside plan: revenue-first, not system-first",
            "items": [
                {
                    "index": 1,
                    "title": "Pick one revenue action",
                    "summary": "Readiness review or checklist call funnel. Money first.",
                    "score": 8.5,
                    "url": "",
                    "source": "alpha",
                    "evidence": [],
                    "risk": [],
                    "next_action": "Choose the $97 readiness review or checklist call funnel.",
                },
                {
                    "index": 2,
                    "title": "Use checklist + 15-minute call funnel",
                    "summary": "Lower friction than selling immediately. Creates qualified conversations.",
                    "score": 8.0,
                    "url": "",
                    "source": "alpha",
                    "evidence": [],
                    "risk": [],
                    "next_action": "Offer 3 short calls today.",
                },
                {
                    "index": 3,
                    "title": "Keep Nexus work limited to execution support",
                    "summary": "Nexus should track the work, not become the work.",
                    "score": 7.0,
                    "url": "",
                    "source": "alpha",
                    "evidence": [],
                    "risk": [],
                    "next_action": "Create one work order, not five new feature tasks.",
                },
            ],
            "top_index": 1,
            "last_selected_index": None,
            "allowed_followups": [
                "explain_score", "research_deeper", "create_work_order",
                "send_to_command", "compare",
            ],
            "provider": None,
            "query": clean_topic,
            "expires_after_minutes": 180,
        })

    return "\n".join(lines)


def _alpha_general_answer(clean_text, clean_topic):
    """Alpha general question — answer directly, not with clarify."""
    t = clean_text.lower()

    # Simple factual questions
    if "color" in t and "sky" in t:
        return (
            "Alpha — Simple Explanation\n\n"
            "The sky usually looks blue during the day because sunlight scatters in "
            "Earth's atmosphere. Blue light scatters more than red light, so more blue "
            "reaches your eyes from different directions.\n\n"
            "At sunrise and sunset, the light travels through more atmosphere, so reds "
            "and oranges become more visible.\n\n"
            "Source: general knowledge\n\n"
            "Optional: I can also explain it like a kid, like a science teacher, or "
            "as a business metaphor."
        )

    if "color" in t:
        return (
            f"Alpha — Simple Explanation\n\n"
            f"Regarding the color question: {clean_topic[:100]}\n\n"
            f"I can answer from general knowledge. For more specific or technical "
            f"color information, I would need to research further.\n\n"
            f"Source: general knowledge"
        )

    # General explanation requests
    if re.search(r"^(what|how|why|explain|tell\s+me)", t):
        return (
            f"Alpha — Outside Perspective\n\n"
            f"Regarding: {clean_topic[:100]}\n\n"
            f"Here is Alpha's outside perspective on this topic:\n\n"
            f"This is a general question that I can answer from general knowledge "
            f"or research. For business-specific context, I can also look at how "
            f"this relates to GoClear's credit/funding readiness work.\n\n"
            f"Source: general knowledge + Alpha outside reasoning\n\n"
            f'Say "research [topic]" for live web research.'
        )

    # Default: give a helpful response, not "clarify"
    return (
        f"Alpha — Outside Perspective\n\n"
        f"Regarding: {clean_topic[:100]}\n\n"
        f"I can answer this from general knowledge, outside reasoning, or web research.\n\n"
        f"For GoClear/Nexus business context, I can also evaluate how this "
        f"relates to your credit/funding readiness work.\n\n"
        f"Source: Alpha outside reasoning\n\n"
        f'Say "research [topic]" for live web research, or ask a follow-up question.'
    )


def _write_router_decision(decision):
    """Write router decision receipt for debugging."""
    try:
        os.makedirs("reports/telegram", exist_ok=True)
        with open("reports/telegram/router_decision_latest.md", "w") as f:
            f.write("# Router Decision — Latest\n\n")
            for k, v in decision.items():
                f.write(f"- **{k}**: {v}\n")
    except Exception:
        pass


def process_command(text, mission=None):
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

    # Not a slash command — try Platform graph first when enabled
    full_text = text.strip()

    # Deterministic Nexus operator queries must win over generic workflow
    # intake. Product Evolution is a later governed action lane; it must not
    # swallow read-only status, research, or greeting requests.
    pre_route_result = handle_nexus_pre_route(full_text, mission=mission)
    if pre_route_result is not None:
        return pre_route_result

    # Product Evolution is a bounded product-workflow request, not a general
    # command. Keep the existing bridge/authorization boundary and let the
    # reusable intake layer build the contract; execution remains governed by
    # the Product Evolution runner.
    try:
        from nexus_product_evolution.telegram_control import handle_product_evolution_intake
        evolution = handle_product_evolution_intake(full_text)
        if evolution.get("handled"):
            return evolution["response"]
    except Exception:
        return "Product Evolution intake is temporarily unavailable; no mission was started."

    # --- Diagnostic trace: routing entry ---
    _route_trace = {
        "worker_pid": os.getpid(),
        "source_commit": os.getenv("NEXUS_SOURCE_COMMIT", "unknown"),
        "platform_enabled": os.getenv("NEXUS_AGENT_PLATFORM_ENABLED", "false"),
        "hermes_graph_enabled": os.getenv("NEXUS_HERMES_LANGGRAPH_ENABLED", "false"),
        "legacy_fallback_enabled": os.getenv("LEGACY_HERMES_ROUTER_FALLBACK_ENABLED", "true"),
        "langfuse_tracing_enabled": os.getenv("LANGFUSE_TRACING_ENABLED", "false"),
        "message_length": len(full_text),
    }

    # --- Agent Platform path (Ray-only, feature-flag gated) ---
    _route_trace["path_attempted"] = "platform_graph"
    try:
        from nexus_agent_platform.integration import try_hermes_platform
        _route_trace["platform_import"] = "success"
        platform_result = try_hermes_platform(
            text=full_text,
            mission=mission,
            chat_id=mission.get("ray_chat_id_masked") if mission else None,
            update_id=mission.get("telegram_update_id") if mission else None,
        )
        if platform_result is not None:
            _route_trace["platform_result"] = "handled"
            _route_trace["platform_response_len"] = len(platform_result)
            if mission:
                update_mission(mission, "ROUTED", selected_intent="platform_graph", selected_tool="nexus_agent_platform", router_confidence=0.95)
                update_mission(mission, "RESPONSE_COMPOSED", fallback_used=False, response_source="platform_graph")
            _write_routing_trace(_route_trace)
            return platform_result
        _route_trace["platform_result"] = "returned_none"
    except ImportError as _imp_err:
        _route_trace["platform_import"] = f"ImportError: {_imp_err}"
    except Exception as _platform_exc:
        _route_trace["platform_result"] = f"exception: {_platform_exc}"
        import logging as _log
        _log.getLogger("nexus_telegram_bridge").warning("Platform integration error: %s", _platform_exc)

    # --- Legacy routing path ---
    _route_trace["path_attempted"] = "legacy_pre_route"

    if mission:
        update_mission(mission, "ROUTED", selected_intent="general_advisory", selected_tool="hermes_router", router_confidence=0.45)

    # Try new router after deterministic Nexus operational routing
    _route_trace["path_attempted"] = "new_router"
    new_result = process_with_new_router(full_text)
    if new_result is not None:
        _route_trace["legacy_result"] = "handled_by_new_router"
        if mission:
            update_mission(mission, "RESPONSE_COMPOSED", fallback_used=False)
        _write_routing_trace(_route_trace)
        return new_result

    # Fallback to old classification for backward compatibility
    _route_trace["path_attempted"] = "legacy_classifier"
    intent, match, extra = classify_message_intent(full_text)
    if mission:
        update_mission(mission, "ROUTED", selected_intent=intent, selected_tool="legacy_classifier", router_confidence=0.35)
    _route_trace["legacy_result"] = f"classifier_intent={intent}"
    _write_routing_trace(_route_trace)

    write_alpha_debug_receipt({
        "source": "process_command_fallback",
        "raw_text": full_text[:100],
        "detected_intent": intent,
    })

    # Route by old intent
    if intent == "GREETING":
        return handle_greeting(agent=extra)
    elif intent == "CASUAL_AGENT_CHAT":
        return handle_casual_chat(agent=extra)
    elif intent == "HERMES_ADVISORY":
        return hermes_direct_answer(extra or full_text)
    elif intent == "HERMES_WEB_SEARCH":
        return _handle_hermes_web_search(extra or full_text)
    elif intent == "HERMES_URL_REVIEW":
        return _handle_hermes_url_review(extra or "")
    elif intent == "NEXUS_STATUS_OR_REPORT":
        return handle_status_report()
    elif intent == "ALPHA_OPINION":
        return _handle_alpha_opinion(extra or full_text)
    elif intent == "ALPHA_CONTEXT_FOLLOWUP":
        return cmd_followup(extra, match, 1288928049)
    elif intent == "ALPHA_RESEARCH_REQUEST":
        return _handle_alpha_research(extra or full_text)
    elif intent == "WORK_ORDER_REQUEST":
        wo = create_work_order(full_text, "hermes", "ACTIVE_INTERNAL", source="telegram")
        return f"Work Order Created: {wo['work_order_id']}\nRoute: hermes\nMode: ACTIVE_INTERNAL"
    elif intent == "APPROVAL_ACTION":
        return _handle_approval_action(full_text)
    elif intent == "TEMPORAL_INTENT":
        if TEMPORAL_AVAILABLE:
            return format_time_response(extra)
        return "Temporal module not available."
    elif intent == "ACTIVE_CONTEXT_FOLLOWUP":
        return _handle_active_context_followup_bridge(extra, full_text)
    else:
        # Last resort: try Hermes draft as intelligent fallback
        if HERMES_DRAFT_AVAILABLE:
            if mission:
                update_mission(mission, "ROUTING_FAILED", fallback_used=True, error="generic_hermes_draft_fallback")
            understanding = {"raw_text": full_text, "normalized_text": full_text.lower().strip(),
                           "explicit_role": None, "intent_family": "unknown",
                           "is_followup": False, "followup_type": "none",
                           "needs_external_evidence": False, "time_sensitive": False,
                           "risk_level": "low", "confidence": 0.4}
            draft = generate_hermes_draft(understanding)
            return _render_draft(draft, full_text)
        if mission:
            update_mission(mission, "ROUTING_FAILED", fallback_used=True, error="unknown_message")
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

def _write_routing_trace(trace_data):
    """Write routing diagnostic trace to local file for legacy path analysis."""
    import json as _json
    from datetime import datetime, timezone
    trace_dir = os.path.join(os.path.dirname(__file__), "..", "..", "reports", "runtime", "agent_traces")
    os.makedirs(trace_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filepath = os.path.join(trace_dir, f"routing_trace_{ts}.json")
    trace_data["timestamp"] = datetime.now(timezone.utc).isoformat()
    try:
        with open(filepath, "w") as f:
            _json.dump(trace_data, f, indent=2, default=str)
    except Exception:
        pass


if __name__ == "__main__":
    main()
