#!/usr/bin/env python3
"""
Alpha Telegram Worker — Persistent inbound conversation handler for @AlphaHermes27bot.

Handles the complete lifecycle:
  Telegram update → Authorization → Mission creation → Intent routing →
  Live research → Synthesis → Readable response → Telegram delivery

Separate from Nexus bridge. Uses ALPHA_TELEGRAM_BOT_TOKEN only.
Owns its own update offset. Never shares Nexus state.

Usage:
  python3 scripts/alpha/alpha_telegram_worker.py --once
  python3 scripts/alpha/alpha_telegram_worker.py --poll
  python3 scripts/alpha/alpha_telegram_worker.py --test
"""

import json
import os
import sys
import re
import ssl
import time
import signal
import hashlib
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ─── Paths ──────────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
RUNTIME_ENV = os.path.expanduser("~/.config/nexus/runtime.env")

ALPHA_STATE_DIR = os.path.join(REPO_ROOT, "data", "runtime")
ALPHA_OFFSET_PATH = os.path.join(ALPHA_STATE_DIR, "alpha_telegram_last_update_id.json")
ALPHA_MISSIONS_DIR = os.path.join(REPO_ROOT, "data", "alpha", "missions")
ALPHA_RESEARCH_DIR = os.path.join(REPO_ROOT, "data", "alpha", "research")
ALPHA_STATUS_PATH = os.path.join(ALPHA_STATE_DIR, "alpha_telegram_status.json")
ALPHA_LOG_PATH = os.path.join(REPO_ROOT, "reports", "runtime", "alpha_telegram.log")
ALPHA_ERROR_LOG = os.path.join(REPO_ROOT, "reports", "runtime", "alpha_telegram_error.log")
RESEARCH_RESULTS_DIR = os.path.join(REPO_ROOT, "reports", "alpha", "research_results")
OPPORTUNITIES_DIR = os.path.join(REPO_ROOT, "reports", "alpha", "opportunities")

# ─── SSL ────────────────────────────────────────────────

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

# ─── Config ─────────────────────────────────────────────

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
TELEGRAM_MAX_MSG = 4000
MISSION_TIMEOUT_SECONDS = 120
POLL_TIMEOUT = 30
HEARTBEAT_INTERVAL = 60

# ─── Runtime env loader ─────────────────────────────────

def load_runtime_env():
    """Load canonical runtime.env without printing secrets."""
    if not os.path.exists(RUNTIME_ENV):
        _log_error(f"Runtime env not found: {RUNTIME_ENV}")
        return {}
    env = {}
    with open(RUNTIME_ENV) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, val = line.partition("=")
                env[key.strip()] = val.strip()
    return env

_ENV = None

def get_env():
    global _ENV
    if _ENV is None:
        _ENV = load_runtime_env()
        # Propagate to os.environ so imported modules (hermes_web_search etc.) can read them
        for k, v in _ENV.items():
            if k and v and k not in os.environ:
                os.environ[k] = v
    return _ENV

# ─── Logging ────────────────────────────────────────────

def _log(msg, path=None):
    ts = datetime.now(timezone.utc).isoformat()
    line = f"[{ts}] {msg}"
    target = path or ALPHA_LOG_PATH
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "a") as f:
        f.write(line + "\n")

def _log_error(msg):
    _log(f"ERROR: {msg}", ALPHA_ERROR_LOG)
    _log(f"ERROR: {msg}")

# ─── Telegram API ───────────────────────────────────────

def _tg_api(method, params=None, token=None, timeout=20):
    """Call Telegram API. Returns JSON response or None."""
    env = get_env()
    if token is None:
        token = env.get("ALPHA_TELEGRAM_BOT_TOKEN", "")
    if not token:
        _log_error("ALPHA_TELEGRAM_BOT_TOKEN not set")
        return None

    url = TELEGRAM_API.format(token=token, method=method)
    try:
        if params:
            data = urllib.parse.urlencode(params).encode("utf-8")
            req = urllib.request.Request(url, data=data)
        else:
            req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        _log_error(f"HTTP {e.code} calling {method}: {body[:200]}")
        return None
    except Exception as e:
        _log_error(f"Error calling {method}: {e}")
        return None


def tg_send_message(chat_id, text, token=None):
    """Send a message, chunking if needed. Returns list of message IDs."""
    if not text:
        return []

    env = get_env()
    if token is None:
        token = env.get("ALPHA_TELEGRAM_BOT_TOKEN", "")

    chunks = _chunk_message(text)
    message_ids = []

    for chunk in chunks:
        result = _tg_api("sendMessage", {
            "chat_id": chat_id,
            "text": chunk,
        }, token=token)
        if result and result.get("ok"):
            msg_id = result.get("result", {}).get("message_id")
            if msg_id:
                message_ids.append(msg_id)
        else:
            _log_error(f"Failed to send message to {chat_id}: {result}")
            # Retry once after brief pause
            time.sleep(1)
            result = _tg_api("sendMessage", {
                "chat_id": chat_id,
                "text": chunk,
            }, token=token)
            if result and result.get("ok"):
                msg_id = result.get("result", {}).get("message_id")
                if msg_id:
                    message_ids.append(msg_id)
            else:
                _log_error(f"Retry also failed for chat {chat_id}")

    return message_ids


def _chunk_message(text):
    """Split long messages into Telegram-safe chunks."""
    if len(text) <= TELEGRAM_MAX_MSG:
        return [text]

    chunks = []
    lines = text.split("\n")
    current = []
    current_len = 0

    for line in lines:
        line_len = len(line) + 1
        if current_len + line_len > TELEGRAM_MAX_MSG - 100 and current:
            chunks.append("\n".join(current))
            current = [line]
            current_len = line_len
        else:
            current.append(line)
            current_len += line_len

    if current:
        chunks.append("\n".join(current))

    return chunks

# ─── Offset Management ─────────────────────────────────

def load_offset():
    """Load the last processed update ID for Alpha."""
    try:
        with open(ALPHA_OFFSET_PATH) as f:
            data = json.load(f)
            return data.get("last_update_id", 0)
    except Exception:
        return 0


def save_offset(update_id):
    """Save the last processed update ID."""
    os.makedirs(os.path.dirname(ALPHA_OFFSET_PATH), exist_ok=True)
    with open(ALPHA_OFFSET_PATH, "w") as f:
        json.dump({
            "last_update_id": update_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, f, indent=2)

# ─── Authorization ──────────────────────────────────────

def is_authorized(chat_id, user_id, username):
    """Check if this user is authorized to interact with Alpha."""
    env = get_env()

    # Primary: TELEGRAM_CHAT_ID (Ray's private chat)
    allowed_chat_ids = set()
    raw_chat = env.get("TELEGRAM_CHAT_ID", "")
    if raw_chat:
        for cid in raw_chat.split(","):
            cid = cid.strip()
            if cid:
                try:
                    allowed_chat_ids.add(int(cid))
                except ValueError:
                    pass

    # Also check ALPHA_TELEGRAM_CHAT_ID if set
    alpha_chat = env.get("ALPHA_TELEGRAM_CHAT_ID", "")
    if alpha_chat:
        for cid in alpha_chat.split(","):
            cid = cid.strip()
            if cid:
                try:
                    allowed_chat_ids.add(int(cid))
                except ValueError:
                    pass

    # Fallback: hardcoded Ray chat ID
    if 1288928049 not in allowed_chat_ids:
        allowed_chat_ids.add(1288928049)

    if chat_id in allowed_chat_ids:
        return True

    _log_error(f"Unauthorized access attempt: chat_id={chat_id} user_id={user_id} username={username}")
    return False

# ─── Mission System ─────────────────────────────────────

MISSION_STATES = [
    "RECEIVED", "AUTHORIZED", "ROUTED", "RESEARCH_STARTED",
    "SOURCES_RETRIEVED", "SYNTHESIS_STARTED", "RESULT_STORED",
    "RESPONSE_COMPOSED", "RESPONSE_SENT", "COMPLETED",
]

FAILURE_STATES = [
    "UNAUTHORIZED", "ROUTING_FAILED", "PROVIDER_FAILED",
    "STORAGE_FAILED", "DELIVERY_FAILED", "TIMED_OUT",
    "STALLED", "DEAD_LETTERED",
]


def create_mission(update_id, chat_id, user_id, text):
    """Create a new Alpha mission record."""
    ts = datetime.now(timezone.utc)
    mission_id = f"alpha_mission_{ts.strftime('%Y%m%dT%H%M%S')}_{update_id}"

    mission = {
        "mission_id": mission_id,
        "update_id": update_id,
        "bot_id": 8986632054,
        "chat_id": chat_id,
        "masked_chat_id": f"***{str(chat_id)[-4:]}",
        "user_id": user_id,
        "original_message": text[:500],
        "normalized_query": _normalize_query(text),
        "selected_intent": None,
        "provider_calls": [],
        "source_count": 0,
        "research_result_id": None,
        "opportunity_ids": [],
        "response_message_ids": [],
        "timestamps": {
            "received_at": ts.isoformat(),
        },
        "retry_count": 0,
        "failure_reason": None,
        "status": "RECEIVED",
    }

    os.makedirs(ALPHA_MISSIONS_DIR, exist_ok=True)
    path = os.path.join(ALPHA_MISSIONS_DIR, f"{mission_id}.json")
    with open(path, "w") as f:
        json.dump(mission, f, indent=2)

    _log(f"Mission created: {mission_id} | update={update_id} | text={text[:60]}")
    return mission


def update_mission(mission, status, extra=None):
    """Update mission status and timestamps."""
    mission["status"] = status
    mission["timestamps"][f"{status.lower()}_at"] = datetime.now(timezone.utc).isoformat()
    if extra:
        mission.update(extra)

    path = os.path.join(ALPHA_MISSIONS_DIR, f"{mission['mission_id']}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(mission, f, indent=2)

    _log(f"Mission {mission['mission_id']} → {status}")
    return mission


def save_mission(mission):
    """Persist current mission state."""
    path = os.path.join(ALPHA_MISSIONS_DIR, f"{mission['mission_id']}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(mission, f, indent=2)

# ─── Intent Classification ──────────────────────────────

def classify_intent(text):
    """Classify incoming Alpha message into an intent."""
    t = text.lower().strip()
    # Strip optional prefixes
    t = re.sub(r'^(?:alpha|@alphahermes27bot)\s*[,:]*\s*', '', t)
    t = re.sub(r'^/(?:alpha|research)\s+', '', t)

    # Greeting
    if re.match(r'^(good\s+(?:morning|afternoon|evening|night)|hello|hey|hi\b|yo\b|what\'?s\s+up|howdy|greetings)', t):
        return "greeting", t

    # Research request
    if re.search(r'(?:find|search|research|look\s+up|discover|investigate|what\s+are\s+the\s+best|what\s+current|current\s+business)', t):
        return "research_request", t

    # Research status
    if re.search(r'(?:what\s+(?:are\s+you\s+)?(?:researching|working\s+on|found)|status\s+of\s+(?:research|mission)|what\s+did\s+you\s+find|show\s+(?:research|missions|results))', t):
        return "research_status", t

    # Opinion
    if re.search(r'(?:give\s+(?:me\s+)?(?:your\s+)?(?:independent\s+)?opinion|what\s+do\s+you\s+think|which\s+(?:is\s+)?(?:the\s+)?(?:best|strongest|top)|recommend|your\s+take|your\s+view)', t):
        return "opinion_request", t

    # Help
    if re.match(r'^(help|commands|what\s+can\s+you)', t):
        return "help", t

    # Default: treat as research if it looks like a question about business/money
    if re.search(r'(?:money|revenue|business|opportunity|grant|fund|credit|client|affiliate|income|sell|close)', t):
        return "research_request", t

    # Default fallback
    return "general", t


def _normalize_query(text):
    """Normalize a research query for deduplication."""
    q = text.lower().strip()
    q = re.sub(r'^(?:alpha|@alphahermes27bot)\s*[,:]*\s*', '', q)
    q = re.sub(r'^/(?:alpha|research)\s+', '', q)
    q = re.sub(r'[^a-z0-9\s]', '', q)
    q = re.sub(r'\s+', ' ', q).strip()
    return q

# ─── Research Pipeline ──────────────────────────────────

def execute_research(query, mission):
    """Execute live research via Brave Search and synthesize results."""
    # Import web search
    sys.path.insert(0, os.path.join(REPO_ROOT, "scripts", "hermes"))
    try:
        from hermes_web_search import web_search
        search_available = True
    except ImportError:
        search_available = False
        _log_error("hermes_web_search module not available")

    if not search_available:
        return {
            "status": "provider_unavailable",
            "results": [],
            "synthesis": "Web search is not configured. I cannot perform live research right now.",
            "sources": [],
        }

    update_mission(mission, "RESEARCH_STARTED")

    # Execute search
    search_result = web_search(query, max_results=6)

    if search_result.get("status") != "ok" or not search_result.get("results"):
        provider = search_result.get("provider", "none")
        notes = search_result.get("notes", [])
        return {
            "status": "provider_failed",
            "provider": provider,
            "results": [],
            "synthesis": f"Search completed but returned no results (provider: {provider}).",
            "sources": [],
            "notes": notes,
        }

    update_mission(mission, "SOURCES_RETRIEVED", {
        "provider_calls": [{"provider": search_result["provider"], "query": query, "result_count": len(search_result["results"])}],
        "source_count": len(search_result["results"]),
    })

    results = search_result["results"]

    # Synthesize results into opportunities
    opportunities = _synthesize_opportunities(query, results)

    update_mission(mission, "SYNTHESIS_STARTED")

    # Store research results
    result_id = f"alpha_result_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
    stored = {
        "result_id": result_id,
        "query": query[:200],
        "provider": search_result.get("provider", "unknown"),
        "source_count": len(results),
        "opportunities": opportunities,
        "raw_results": [{"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("snippet", "")[:200]} for r in results],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    os.makedirs(RESEARCH_RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESEARCH_RESULTS_DIR, f"{result_id}.json"), "w") as f:
        json.dump(stored, f, indent=2)

    # Store opportunities
    opp_ids = []
    for opp in opportunities:
        opp_id = f"opp_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_{len(opp_ids)}"
        opp["opportunity_id"] = opp_id
        opp["result_id"] = result_id
        opp_ids.append(opp_id)
        os.makedirs(OPPORTUNITIES_DIR, exist_ok=True)
        with open(os.path.join(OPPORTUNITIES_DIR, f"{opp_id}.json"), "w") as f:
            json.dump(opp, f, indent=2)

    update_mission(mission, "RESULT_STORED", {
        "research_result_id": result_id,
        "opportunity_ids": opp_ids,
    })

    # Compose readable response
    response_text = _compose_research_response(query, opportunities, results, search_result.get("provider", "unknown"))

    update_mission(mission, "RESPONSE_COMPOSED")

    return {
        "status": "ok",
        "result_id": result_id,
        "opportunities": opportunities,
        "response": response_text,
        "source_count": len(results),
        "provider": search_result.get("provider", "unknown"),
    }


def _synthesize_opportunities(query, results):
    """Score and rank search results as business opportunities."""
    opportunities = []
    topic = query.lower()

    for r in results:
        title = r.get("title", "")
        snippet = r.get("snippet", "")
        url = r.get("url", "")
        text = f"{title} {snippet}".lower()

        # Score dimensions
        speed = 5
        cost = 5
        relevance = 5
        ease = 5
        proof = 5

        # Speed signals
        if any(kw in text for kw in ["quick", "fast", "instant", "same day", "today", "24h", "immediate"]):
            speed = 8
        elif any(kw in text for kw in ["long", "months", "complex", "build", "develop"]):
            speed = 3

        # Cost signals
        if any(kw in text for kw in ["free", "no cost", "low-cost", "cheap", "$0", "open source"]):
            cost = 9
        elif any(kw in text for kw in ["paid", "subscription", "premium", "$99", "$199"]):
            cost = 4

        # Relevance to business/money
        biz_kw = ["business", "revenue", "money", "income", "profit", "client", "customer",
                   "credit", "funding", "grant", "affiliate", "sell", "close", "opportunity"]
        if any(kw in text for kw in biz_kw):
            relevance = 8

        # Ease
        if any(kw in text for kw in ["easy", "simple", "no-code", "plug", "one-click", "template"]):
            ease = 8
        elif any(kw in text for kw in ["complex", "custom", "develop", "engineer", "build"]):
            ease = 3

        # Proof
        if any(kw in text for kw in ["case study", "review", "rated", "testimonials", "proven", "success"]):
            proof = 8

        total = round((speed + cost + relevance + ease + proof) / 5, 1)

        # Determine fastest path
        if speed >= 7:
            fastest = "Start today, results within days"
        elif ease >= 7:
            fastest = "Low setup effort, quick deployment"
        else:
            fastest = "Requires planning but achievable this month"

        # Estimate value
        if relevance >= 7 and cost >= 7:
            value = "High — strong fit, low cost"
        elif relevance >= 6:
            value = "Medium — relevant but needs evaluation"
        else:
            value = "Moderate — general business intelligence"

        opportunities.append({
            "title": title[:150],
            "why_it_matters": snippet[:200] if snippet else "Relevant to current business goals",
            "fastest_path_to_revenue": fastest,
            "estimated_value": value,
            "effort": "Low" if ease >= 7 else ("Medium" if ease >= 4 else "High"),
            "risk": "Low" if cost >= 7 else "Medium",
            "source_url": url,
            "score": total,
        })

    # Sort by score
    opportunities.sort(key=lambda x: x["score"], reverse=True)
    return opportunities[:5]


def _compose_research_response(query, opportunities, raw_results, provider):
    """Compose a readable Alpha research response."""
    lines = [
        "ALPHA RESEARCH RESULT",
        "",
        f"Query: {query[:100]}",
        f"Sources: {len(raw_results)} (via {provider})",
        "",
    ]

    if not opportunities:
        lines.append("I searched but did not find strong opportunities matching your query.")
        lines.append("")
        lines.append("Try a more specific search or ask me to research a different topic.")
        return "\n".join(lines)

    lines.append("What I found")
    lines.append("")

    for i, opp in enumerate(opportunities[:5], 1):
        lines.append(f"{i}. {opp['title']}")
        lines.append(f"   Why it matters: {opp['why_it_matters'][:120]}")
        lines.append(f"   Fastest path: {opp['fastest_path_to_revenue']}")
        lines.append(f"   Value: {opp['estimated_value']}")
        lines.append(f"   Effort: {opp['effort']} | Risk: {opp['risk']}")
        lines.append(f"   Source: {opp['source_url'][:80]}")
        lines.append("")

    # Recommendation
    top = opportunities[0]
    lines.append("My recommendation")
    lines.append(f"Start with #{1}: {top['title'][:80]}")
    lines.append(f"It scores highest ({top['score']}/10) with the fastest path to revenue and lowest effort.")
    lines.append("")

    lines.append("Recommended next action")
    lines.append(f"Say 'give me your opinion on the strongest opportunity' for my independent take.")
    lines.append(f"Say 'show sources' to see all raw search results.")
    lines.append("")

    lines.append("Action required from Ray: YES — review and decide on approach")

    return "\n".join(lines)


def _compose_greeting():
    """Compose a natural Alpha greeting."""
    hour = datetime.now(timezone(timedelta(hours=-7))).hour
    if hour < 12:
        time_greeting = "Good morning"
    elif hour < 17:
        time_greeting = "Good afternoon"
    else:
        time_greeting = "Good evening"

    return (
        f"{time_greeting} Ray. Alpha is online and ready.\n\n"
        "I can:\n"
        "- Research current business opportunities\n"
        "- Give you an independent opinion on any topic\n"
        "- Find grants, funding, or affiliate programs\n"
        "- Analyze competitors and market trends\n\n"
        "Just tell me what you need."
    )


def _compose_research_status():
    """Compose a research status update."""
    # Count recent missions
    mission_count = 0
    completed_count = 0
    latest_mission = None

    if os.path.isdir(ALPHA_MISSIONS_DIR):
        missions = sorted(Path(ALPHA_MISSIONS_DIR).glob("alpha_mission_*.json"), reverse=True)
        mission_count = len(missions)
        for m_path in missions[:5]:
            try:
                with open(m_path) as f:
                    m = json.load(f)
                if m.get("status") == "COMPLETED":
                    completed_count += 1
                if latest_mission is None:
                    latest_mission = m
            except Exception:
                pass

    # Count research results
    result_count = 0
    if os.path.isdir(RESEARCH_RESULTS_DIR):
        result_count = len(list(Path(RESEARCH_RESULTS_DIR).glob("alpha_result_*.json")))

    lines = [
        "ALPHA RESEARCH STATUS",
        "",
        f"Missions processed: {mission_count}",
        f"Completed: {completed_count}",
        f"Research results stored: {result_count}",
    ]

    if latest_mission:
        status = latest_mission.get("status", "unknown")
        query = latest_mission.get("normalized_query", "unknown")[:60]
        lines.extend([
            "",
            f"Latest mission: {status}",
            f"Query: {query}",
        ])

    lines.extend([
        "",
        "Say 'research [topic]' to start a new search.",
        "Action required from Ray: NO",
    ])

    return "\n".join(lines)


def _compose_opinion_response(query):
    """Compose an independent opinion using internal context."""
    # Read Alpha conversation context for recent research
    conv_path = os.path.join(REPO_ROOT, "data", "runtime", "telegram_conversation_context.json")
    alpha_ctx = {}
    try:
        with open(conv_path) as f:
            ctx = json.load(f)
            alpha_ctx = ctx.get("1288928049", {})
    except Exception:
        pass

    recent_topic = alpha_ctx.get("last_topic", "Nexus operations")
    recent_recs = alpha_ctx.get("last_alpha_recommendations", [])

    lines = [
        "ALPHA INDEPENDENT OPINION",
        "",
        f"Topic: {query[:100]}",
        "",
    ]

    if recent_recs:
        lines.append("Based on my recent research, here is my independent assessment:")
        lines.append("")
        for i, rec in enumerate(recent_recs[:3], 1):
            lines.append(f"{i}. {rec.get('title', 'Unknown')}")
            lines.append(f"   Score: {rec.get('score', '?')}/10")
            lines.append("")

    lines.extend([
        "My assessment",
        f"The strongest opportunity depends on your current priorities.",
        f"If speed to revenue matters most, focus on the highest-scored item.",
        f"If building long-term value matters, consider the item with the best fit for Nexus capabilities.",
        "",
        "Recommended next action",
        "Pick one opportunity and I will do deeper research on it.",
        "Action required from Ray: YES — select a priority",
    ])

    return "\n".join(lines)


def _compose_help():
    """Compose help response."""
    return (
        "ALPHA — What I Can Do\n\n"
        "Natural language — no slash commands needed:\n\n"
        "Research:\n"
        "  'find current business opportunities for GoClear'\n"
        "  'research current small-business grants'\n"
        "  'what are the best affiliate programs'\n\n"
        "Opinion:\n"
        "  'give me your opinion on the strongest opportunity'\n"
        "  'what do you think about this approach'\n\n"
        "Status:\n"
        "  'what are you researching right now?'\n"
        "  'what did you find today?'\n\n"
        "Greeting:\n"
        "  'good morning'\n\n"
        "I use live web search for current information."
    )

# ─── Mission Watchdog ───────────────────────────────────

def check_stale_missions():
    """Check for missions that have stalled."""
    if not os.path.isdir(ALPHA_MISSIONS_DIR):
        return

    now = datetime.now(timezone.utc)
    stale_threshold = now - timedelta(seconds=MISSION_TIMEOUT_SECONDS)

    for m_path in Path(ALPHA_MISSIONS_DIR).glob("alpha_mission_*.json"):
        try:
            with open(m_path) as f:
                mission = json.load(f)

            status = mission.get("status", "")
            if status in MISSION_STATES and status not in ("COMPLETED", "RESPONSE_SENT"):
                received = mission.get("timestamps", {}).get("received_at", "")
                if received:
                    recv_dt = datetime.fromisoformat(received.replace("Z", "+00:00"))
                    if recv_dt < stale_threshold:
                        mission["status"] = "STALLED"
                        mission["failure_reason"] = f"Mission stalled at stage {status} after {MISSION_TIMEOUT_SECONDS}s"
                        save_mission(mission)
                        _log_error(f"Mission stalled: {mission['mission_id']} at {status}")

                        # Notify via Nexus if available
                        _notify_nexus_stalled(mission)
        except Exception as e:
            _log_error(f"Error checking stale mission: {e}")


def _notify_nexus_stalled(mission):
    """Notify Nexus Hermes about a stalled Alpha mission."""
    _log(f"STALL_NOTIFY: Mission {mission['mission_id']} stalled at {mission.get('status')}")

# ─── Runtime Status ─────────────────────────────────────

def write_status(pid, state, extra=None):
    """Write runtime status for Command Center visibility."""
    status = {
        "service": "alpha_telegram_worker",
        "state": state,
        "pid": pid,
        "heartbeat": datetime.now(timezone.utc).isoformat(),
        "bot_identity": {
            "name": "Alpha Hermes",
            "username": "@AlphaHermes27bot",
            "bot_id": 8986632054,
        },
        "polling_mode": "long_poll",
        "last_update_id": load_offset(),
        "last_incoming_message": None,
        "current_mission": None,
        "mission_stage": None,
        "provider_status": None,
        "source_count": 0,
        "response_delivery": None,
        "pending_retries": 0,
        "dead_letter_missions": 0,
        "last_failure": None,
    }
    if extra:
        status.update(extra)

    os.makedirs(os.path.dirname(ALPHA_STATUS_PATH), exist_ok=True)
    with open(ALPHA_STATUS_PATH, "w") as f:
        json.dump(status, f, indent=2)


def update_status_field(key, value):
    """Update a single field in the status file."""
    try:
        with open(ALPHA_STATUS_PATH) as f:
            status = json.load(f)
    except Exception:
        status = {
            "service": "alpha_telegram_worker",
            "pid": os.getpid(),
            "heartbeat": datetime.now(timezone.utc).isoformat(),
        }

    status[key] = value
    status["heartbeat"] = datetime.now(timezone.utc).isoformat()

    os.makedirs(os.path.dirname(ALPHA_STATUS_PATH), exist_ok=True)
    with open(ALPHA_STATUS_PATH, "w") as f:
        json.dump(status, f, indent=2)

# ─── Message Processing ─────────────────────────────────

def process_message(update):
    """Process a single incoming Telegram update through the full lifecycle."""
    message = update.get("message", {})
    chat = message.get("chat", {})
    user = message.get("from", {})
    chat_id = chat.get("id")
    user_id = user.get("id")
    username = user.get("username", "")
    text = message.get("text", "")
    update_id = update.get("update_id", 0)

    if not text or not chat_id:
        return

    _log(f"Incoming: update={update_id} chat={chat_id} user={username} text={text[:80]}")

    # Create mission
    mission = create_mission(update_id, chat_id, user_id, text)

    # Authorize
    if not is_authorized(chat_id, user_id, username):
        update_mission(mission, "UNAUTHORIZED", {"failure_reason": f"Unauthorized user: {username}"})
        tg_send_message(chat_id, "Unauthorized. This Alpha bot is for Ray only.")
        return

    update_mission(mission, "AUTHORIZED")
    update_status_field("last_incoming_message", datetime.now(timezone.utc).isoformat())

    # Classify intent
    intent, normalized = classify_intent(text)
    update_mission(mission, "ROUTED", {"selected_intent": intent})
    update_status_field("current_mission", mission["mission_id"])
    update_status_field("mission_stage", "ROUTED")

    # Route by intent
    response_text = None

    if intent == "greeting":
        response_text = _compose_greeting()

    elif intent == "research_request":
        update_status_field("mission_stage", "RESEARCH_STARTED")
        result = execute_research(normalized, mission)
        if result.get("status") == "ok":
            response_text = result["response"]
        else:
            response_text = (
                f"I attempted research on: {normalized[:80]}\n\n"
                f"Status: {result.get('status', 'unknown')}\n"
                f"{result.get('synthesis', 'No synthesis available.')}\n\n"
                "Try rephrasing your request or ask me to research a different topic."
            )

    elif intent == "research_status":
        response_text = _compose_research_status()

    elif intent == "opinion_request":
        response_text = _compose_opinion_response(normalized)

    elif intent == "help":
        response_text = _compose_help()

    else:
        # General: treat as research if it looks substantive
        if len(text) > 15:
            result = execute_research(normalized, mission)
            if result.get("status") == "ok":
                response_text = result["response"]
            else:
                response_text = (
                    f"I looked into: {normalized[:80]}\n\n"
                    "I did not find strong results. Try a more specific query."
                )
        else:
            response_text = (
                "I can help with research, opinions, or status updates.\n\n"
                "Try: 'find current business opportunities' or 'good morning'"
            )

    # Deliver response
    if response_text:
        update_status_field("mission_stage", "DELIVERING")

        msg_ids = tg_send_message(chat_id, response_text)

        if msg_ids:
            update_mission(mission, "COMPLETED", {
                "response_message_ids": msg_ids,
                "response_telegram_message_ids": msg_ids,
            })
            update_status_field("mission_stage", "COMPLETED")
            update_status_field("current_mission", None)
            update_status_field("response_delivery", "delivered")
            _log(f"Response delivered: mission={mission['mission_id']} msg_ids={msg_ids}")
        else:
            update_mission(mission, "DELIVERY_FAILED", {
                "failure_reason": "Telegram sendMessage failed after retry",
            })
            update_status_field("mission_stage", "DELIVERY_FAILED")
            update_status_field("last_failure", f"Delivery failed for mission {mission['mission_id']}")
            _log_error(f"Delivery failed: mission={mission['mission_id']}")

# ─── Main Loops ─────────────────────────────────────────

def run_once():
    """Single polling cycle: fetch updates, process, return."""
    _log("Alpha worker: --once cycle starting")
    write_status(os.getpid(), "RUNNING")

    offset = load_offset()
    result = _tg_api("getUpdates", {"offset": offset + 1, "limit": 10, "timeout": 0})

    if not result or not result.get("ok"):
        _log_error(f"getUpdates failed: {result}")
        write_status(os.getpid(), "API_ERROR")
        return "API_ERROR"

    updates = result.get("result", [])
    if not updates:
        _log("Alpha worker: no new updates")
        write_status(os.getpid(), "IDLE")
        return "NO_UPDATES"

    max_update_id = offset
    processed = 0

    for update in updates:
        uid = update.get("update_id", 0)
        if uid > max_update_id:
            max_update_id = uid

        try:
            process_message(update)
            processed += 1
        except Exception as e:
            _log_error(f"Error processing update {uid}: {e}")

    # Save offset after processing (not before)
    if max_update_id > offset:
        save_offset(max_update_id)

    _log(f"Alpha worker: processed {processed} updates, max_id={max_update_id}")
    write_status(os.getpid(), "IDLE")
    return f"PROCESSED {processed}"


def run_poll():
    """Persistent long-polling mode."""
    _log("Alpha worker: entering persistent long-poll mode")
    write_status(os.getpid(), "STARTING")

    # Handle signals gracefully
    running = True
    def _handle_signal(sig, frame):
        nonlocal running
        _log(f"Alpha worker: received signal {sig}, shutting down")
        running = False
        write_status(os.getpid(), "STOPPING")

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    last_heartbeat = time.time()
    last_stale_check = time.time()

    while running:
        try:
            # Heartbeat
            now = time.time()
            if now - last_heartbeat > HEARTBEAT_INTERVAL:
                write_status(os.getpid(), "ALIVE")
                last_heartbeat = now

            # Stale mission check
            if now - last_stale_check > 30:
                check_stale_missions()
                last_stale_check = now

            # Long poll — urllib timeout must exceed Telegram API timeout
            offset = load_offset()
            result = _tg_api("getUpdates", {
                "offset": offset + 1,
                "limit": 10,
                "timeout": POLL_TIMEOUT,
            }, timeout=POLL_TIMEOUT + 10)

            if not result or not result.get("ok"):
                _log_error(f"Poll error: {result}")
                write_status(os.getpid(), "POLL_ERROR")
                time.sleep(5)
                continue

            updates = result.get("result", [])
            if not updates:
                continue

            max_update_id = offset
            processed = 0

            for update in updates:
                uid = update.get("update_id", 0)
                if uid > max_update_id:
                    max_update_id = uid

                try:
                    process_message(update)
                    processed += 1
                except Exception as e:
                    _log_error(f"Error processing update {uid}: {e}")

            if max_update_id > offset:
                save_offset(max_update_id)

            if processed > 0:
                _log(f"Poll cycle: processed {processed} updates")
                write_status(os.getpid(), "ACTIVE")

        except Exception as e:
            err_msg = str(e)
            if "timed out" in err_msg.lower():
                # Normal long-poll timeout — no updates, keep polling
                continue
            _log_error(f"Poll loop error: {e}")
            write_status(os.getpid(), "ERROR")
            time.sleep(5)

    write_status(os.getpid(), "STOPPED")
    _log("Alpha worker: stopped")


def run_test():
    """Test mode: validate configuration and connectivity."""
    print("Alpha Telegram Worker — Test Mode")
    print("=" * 40)

    env = get_env()
    token = env.get("ALPHA_TELEGRAM_BOT_TOKEN", "")
    print(f"Token present: {'YES' if token else 'NO'}")

    if not token:
        print("FATAL: ALPHA_TELEGRAM_BOT_TOKEN not set")
        return False

    # getMe
    result = _tg_api("getMe")
    if result and result.get("ok"):
        bot = result["result"]
        print(f"Bot name: {bot.get('first_name')}")
        print(f"Bot username: @{bot.get('username')}")
        print(f"Bot ID: {bot.get('id')}")
    else:
        print(f"FATAL: getMe failed: {result}")
        return False

    # getWebhookInfo
    wh = _tg_api("getWebhookInfo")
    if wh and wh.get("ok"):
        info = wh["result"]
        print(f"Webhook URL: {info.get('url') or '(none — polling mode)'}")
        print(f"Pending updates: {info.get('pending_update_count', 0)}")
        if info.get("last_error_message"):
            print(f"Last webhook error: {info.get('last_error_message')}")

    # Check offset
    offset = load_offset()
    print(f"Current offset: {offset}")

    # Check authorization
    print(f"Ray chat ID: 1288928049")
    print(f"Authorized: {is_authorized(1288928049, 1288928049, 'rayscentro')}")

    # Check state dirs
    print(f"Missions dir: {ALPHA_MISSIONS_DIR} (exists: {os.path.isdir(ALPHA_MISSIONS_DIR)})")
    print(f"Research dir: {ALPHA_RESEARCH_DIR} (exists: {os.path.isdir(ALPHA_RESEARCH_DIR)})")

    print("\nTest PASSED — Alpha worker is ready to run.")
    return True


def main():
    args = sys.argv[1:]

    if "--test" in args:
        success = run_test()
        sys.exit(0 if success else 1)
    elif "--once" in args:
        result = run_once()
        print(f"Alpha worker: {result}")
    elif "--poll" in args:
        run_poll()
    else:
        print("Usage: alpha_telegram_worker.py [--once | --poll | --test]")


if __name__ == "__main__":
    main()
