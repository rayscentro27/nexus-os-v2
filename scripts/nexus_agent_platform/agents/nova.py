"""Hermes Nova — isolated conversational Telegram agent.

Nova is a natural, multi-turn conversational agent. It is NOT the
Nexus operator and NOT a research-only tool. Nova talks like a thoughtful
person — creative when appropriate, direct, honest about being AI, and
able to disagree respectfully.

Nova has its own:
  - SOUL (personality and system prompt)
  - conversation memory (isolated namespace)
  - LangGraph graph
  - Telegram bot token
  - OpenRouter model
  - Langfuse trace namespace

Nova has governed read-only access to approved operational data through
a semantic pre-model capability gate. The gate determines whether an
approved capability can answer the request BEFORE the model generates.

Nova does NOT have access to:
  - Supabase writes
  - Oanda
  - Temporal
  - Nexus Hermes memory
  - Alpha memory
  - Business tools
  - Process registry
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from nexus_agent_platform.adapters.graph_adapter import GraphAdapter
from nexus_agent_platform.adapters.otel_adapter import OtelAdapter
from nexus_agent_platform.adapters.state_adapter import AgentState

log = logging.getLogger(__name__)

AGENT_ID = "hermes_nova"

# ─── SOUL ─────────────────────────────────────────────────

SOUL = """You are Hermes Nova — Ray Davis's independent strategic adviser and conversational partner.

Personality:
- You speak naturally, like a knowledgeable friend — not a menu or a bot.
- You are direct and honest. If you don't know something, say so.
- You can disagree respectfully and explain your reasoning.
- You are creative when the situation calls for it.
- You think before responding and give considered answers.
- You are honest about being an AI. You don't pretend to be human.

Behavior:
- Answer ordinary real-world questions helpfully and accurately.
- Preserve topic continuity across messages. Remember what we were discussing.
- Handle pronouns and numbered references naturally ("that idea", "number two").
- Give short, natural answers for simple questions. Go deeper when asked.
- Never fabricate business tools, system access, or data you don't have.
- Never claim unrestricted access to Supabase, Oanda, Temporal, or other Nexus systems.

Business context:
- Ray Davis is the founder of GoClear and Nexus OS.
- GoClear provides Credit and Funding Readiness Reviews ($97 entry offer).
- Nexus OS is the operational platform: CRM, client portal, workflow automation.
- Revenue streams: readiness reviews, outsourced credit-deletion fulfillment,
  business foundation and bankability services, business funding services.
- Referral partners: loan officers, real estate agents, auto salespeople,
  business owners needing funding preparation.
- Nova's role: independent strategic adviser grounded in GoClear and Nexus context.
- When Ray asks how to make money, default to his actual businesses and systems
  unless he explicitly asks for unrelated personal side-hutle ideas.

Operational data access (governed read-only):
- You have approved governed read-only access to specific operational data.
- Available reads: client counts, identity lookups by exact email, client profiles,
  funding readiness, system health, pending approvals, recent research,
  opportunities, operational summaries, runtime capability status, and general
  approved-table discovery.
- You CAN look up specific email addresses using your identity resolution tool.
- You CAN retrieve live client counts and breakdowns.
- You CAN pull up client profiles by exact email.
- You CAN check funding readiness for a specific client.
- You CAN check system health and failures.
- You CAN see pending approvals waiting for review.
- You CAN see recent research from Alpha.
- You CAN see current business opportunities.
- You CAN get a combined operational summary.
- You CAN check what systems and capabilities you have access to.
- You CAN search approved operational records by keyword.
- You CANNOT create, update, delete, or alter any records.
- You CANNOT execute arbitrary SQL or browse all user data.
- You CANNOT access Oanda, Temporal, or other Nexus systems.

Status semantics — CRITICAL:
- "success" = capability executed and returned verified data.
- "empty" = capability executed successfully and verified zero records exist.
- "unavailable" = data source could NOT be reached or queried.
- "partial" = some data sources succeeded, others did not.
- "error" = capability execution failed.
- "unknown" = insufficient evidence to determine status.
- NEVER treat "unavailable" as "zero" or "none". If research is unavailable,
  say "I couldn't retrieve research data" — NOT "there was no research."
- NEVER treat "partial" as "success". If health is partial, say "I can't
  fully verify system health" — NOT "everything is healthy."
- "not_yet_certified" means the system lacks sufficient canonical data to
  make a readiness determination. Say "I don't have enough certified data
  to determine funding readiness" — NOT "not ready."
- EMPTY means verified zero. "You have no pending approvals" is correct
  when status=success and count=0. UNAVAILABLE means unknown.

When you retrieve operational data, treat VERIFIED OPERATIONAL DATA as
  authoritative for the requested facts. Do not replace verified numeric
  values with estimates or model knowledge.
- If a capability fails or is unavailable, say so honestly — never fabricate
  operational values from memory.
- When asked about provenance (where data came from, was it live, which source),
  answer precisely using the capability name, source system, freshness, and
  retrieval time. Do not say "operational data" generically.

Technical explanations:
- Explain frameworks and tools as architecture, not just "combining things." Use concrete examples.
- When asked "what is X," explain what it does, why it exists, and how it compares to alternatives.
- Use structured format (bullets, numbered lists) for multi-part explanations.

Business advice:
- Give direct, honest judgment — not hedged non-answers. State your recommendation clearly.
- Quantify when possible: costs, timelines, trade-offs, probabilities.
- Identify the fastest action the user can take RIGHT NOW to move forward.
- Name the primary risk or failure mode for any recommendation.

Style:
- Conversational, not formal.
- Concise by default, detailed when the user asks for depth.
- Use plain language. Avoid jargon unless the user is technical.
- You may use humor naturally, but never force it."""

# ─── Model Configuration ──────────────────────────────────

DEFAULT_MODEL = "openai/gpt-4o-mini"
MODEL_TIMEOUT = 60
MAX_RETRIES = 1
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 1024

# ─── Conversation Memory ──────────────────────────────────

MEMORY_MAX_TURNS = 20
MEMORY_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "runtime", "nova_memory"
)
MEMORY_EXPIRY_SECONDS = 3600  # 1 hour

# ─── Provenance Store ──────────────────────────────────────
# Persists provenance across --once worker lifecycle for follow-up queries.
# Hardened: hashed filenames, proper permissions, atomic writes, schema validation.

import tempfile

PROVENANCE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "runtime", "nova_provenance"
)
_PROVENANCE_NAMESPACE = "hermes_nova_provenance"


def _provenance_hash(chat_id: int) -> str:
    """Derive a deterministic hashed filename from namespace + chat_id."""
    raw = f"{_PROVENANCE_NAMESPACE}:{chat_id}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _provenance_path(chat_id: int) -> str:
    """Return the hashed provenance file path for a chat."""
    return os.path.join(PROVENANCE_DIR, f"{_provenance_hash(chat_id)}.json")


def save_provenance(chat_id: int, provenance: Dict[str, Any]) -> None:
    """Persist the most recent capability provenance for a chat.

    Uses atomic write (tempfile + os.replace) and safe file permissions.
    Only safe provenance fields are persisted.
    """
    # Filter to safe fields only
    safe_fields = {
        "capability", "status", "source", "source_type", "freshness",
        "retrieved_at", "handler", "trace_id", "verification_complete",
        "sources_checked", "source_statuses",
    }
    safe_prov = {k: v for k, v in provenance.items() if k in safe_fields}

    path = _provenance_path(chat_id)
    os.makedirs(PROVENANCE_DIR, mode=0o700, exist_ok=True)

    data = {
        "provenance": safe_prov,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": time.time() + MEMORY_EXPIRY_SECONDS,
        "schema_version": 1,
    }

    # Atomic write with restricted permissions
    fd, tmp_path = tempfile.mkstemp(dir=PROVENANCE_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.chmod(tmp_path, 0o600)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


def load_provenance(chat_id: int) -> Optional[Dict[str, Any]]:
    """Load the most recent provenance for a chat, or None if expired/missing."""
    path = _provenance_path(chat_id)
    try:
        with open(path) as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return None
        # Schema validation
        if data.get("schema_version") != 1:
            return None
        expires_at = data.get("expires_at", 0)
        if expires_at and time.time() > expires_at:
            return None
        prov = data.get("provenance")
        if not isinstance(prov, dict):
            return None
        return prov
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return None


def _clear_provenance(chat_id: int) -> None:
    """Clear provenance for a chat."""
    path = _provenance_path(chat_id)
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def _conversation_key(chat_id: int) -> str:
    """Isolated namespace key per chat."""
    return f"nova_{chat_id}"


def load_memory(chat_id: int) -> List[Dict[str, str]]:
    """Load conversation history for a chat."""
    key = _conversation_key(chat_id)
    path = os.path.join(MEMORY_DIR, f"{key}.json")
    try:
        with open(path) as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return []
        messages = data.get("messages", [])
        expires_at = data.get("expires_at", 0)
        if expires_at and time.time() > expires_at:
            return []
        return messages[-MEMORY_MAX_TURNS * 2:]
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return []


def save_memory(chat_id: int, messages: List[Dict[str, str]]) -> None:
    """Save conversation history for a chat."""
    key = _conversation_key(chat_id)
    path = os.path.join(MEMORY_DIR, f"{key}.json")
    os.makedirs(MEMORY_DIR, exist_ok=True)
    trimmed = messages[-MEMORY_MAX_TURNS * 2:]
    data = {
        "chat_id": chat_id,
        "messages": trimmed,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": time.time() + MEMORY_EXPIRY_SECONDS,
        "turn_count": len(trimmed) // 2,
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def reset_memory(chat_id: int) -> None:
    """Clear conversation history for a chat."""
    key = _conversation_key(chat_id)
    path = os.path.join(MEMORY_DIR, f"{key}.json")
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def _conversation_hash(messages: List[Dict[str, str]]) -> str:
    """Deterministic hash of conversation for tracing."""
    text = json.dumps(messages, sort_keys=True)[:500]
    return hashlib.sha256(text.encode()).hexdigest()[:12]


# ─── Response Mode Classification ──────────────────────────

_MODE_PATTERNS = {
    "TIME_REQUEST": r"\b(what\s+time|current\s+time|time\s+is\s+it|what\s+day|what\s+date|today(?:'s)?\s+date)\b",
    "ARITHMETIC": r"\b(\d+\s*[\+\-\*\/\%]\s*\d+|calculate|what\s+is\s+\d+|math)\b",
    "CONVERSATION_RESET": r"\b(reset\s+conversation|start\s+over|new\s+topic|forget\s+that|clear\s+memory)\b",
    "GREETING": r"\b(hello|hi|hey|good\s+(morning|afternoon|evening)|yo|howdy|greetings|what'?s\s+up)\b",
    "HOW_ARE_YOU": r"\b(how\s+are\s+you|how(?:'re| are) (?:you|things)|what(?:'s| is) going on|how(?:'s| is) it going)\b",
    "OPINION": r"\b(what\s+do\s+you\s+think|your\s+(?:opinion|thoughts|take|view)|how\s+do\s+you\s+feel|do\s+you\s+(?:agree|think))\b",
}


def classify_response_mode(text: str) -> str:
    """Classify the user message into a response mode."""
    lower = text.lower().strip()
    for mode, pattern in _MODE_PATTERNS.items():
        if re.search(pattern, lower):
            return mode
    return "CONVERSATION"


# ─── Simple Utilities ──────────────────────────────────────

def _get_phoenix_time() -> str:
    """Get current Phoenix time as a natural string."""
    from zoneinfo import ZoneInfo
    now = datetime.now(ZoneInfo("America/Phoenix"))
    hour = now.hour
    if hour < 12:
        greeting = "morning"
    elif hour < 17:
        greeting = "afternoon"
    else:
        greeting = "evening"
    return now.strftime(f"It's %I:%M %p on %A, %B %-d — {greeting} time in Phoenix.")


def _get_phoenix_date() -> str:
    """Get current Phoenix date."""
    from zoneinfo import ZoneInfo
    now = datetime.now(ZoneInfo("America/Phoenix"))
    return now.strftime("Today is %A, %B %-d, %Y in Phoenix.")


def _evaluate_arithmetic(text: str) -> Optional[str]:
    """Safely evaluate simple arithmetic expressions."""
    match = re.search(r'(\d+(?:\.\d+)?)\s*([\+\-\*\/\%])\s*(\d+(?:\.\d+)?)', text)
    if not match:
        return None
    a, op, b = float(match.group(1)), match.group(2), float(match.group(3))
    try:
        if op == '+':
            result = a + b
        elif op == '-':
            result = a - b
        elif op == '*':
            result = a * b
        elif op == '/':
            if b == 0:
                return "I can't divide by zero."
            result = a / b
        elif op == '%':
            if b == 0:
                return "I can't modulo by zero."
            result = a % b
        else:
            return None
        if result == int(result):
            return f"{int(result)}"
        return f"{result:.4g}"
    except Exception:
        return None


# ─── Semantic Capability Gate ──────────────────────────────
# Replaces source-directed Supabase detection with meaning-based
# intent matching. Maps user requests to approved capabilities
# by semantic intent, not by keyword.

_EMAIL_PATTERN = re.compile(
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
)


def _extract_email(text: str) -> Optional[str]:
    """Extract the first email address from text."""
    match = _EMAIL_PATTERN.search(text)
    return match.group(0) if match else None


_PROVENANCE_FOLLOWUP_PATTERNS = re.compile(
    r'\b(?:where\s+(?:did|do)\s+(?:you\s+)?(?:get|find|pull|retrieve|look\s+up)|'
    r'which\s+(?:capability|tool|source|system)|'
    r'(?:was|is)\s+that\s+(?:live|cached|real[- ]time)|'
    r'when\s+(?:did|was)\s+(?:you\s+)?(?:retrieve|get|pull|check)|'
    r'how\s+(?:fresh|recent|old)\s+is\s+(?:that|the|this)|'
    r'(?:did\s+that\s+)?come\s+(?:from|directly)\s+(?:from\s+)?(?:supabase|the\s+database|alpha)|'
    r'which\s+(?:source|database|table)\s+(?:did|was)|'
    r'where\s+did\s+(?:those|the|that|these)\s+(?:numbers?|data|results?)|'
    r'(?:is|was)\s+that\s+(?:from\s+)?(?:supabase|alpha|live|cached|a\s+live))\b',
    re.IGNORECASE,
)


def _detect_provenance_followup(text: str) -> bool:
    """Detect if the user is asking about the provenance of a prior result."""
    return bool(_PROVENANCE_FOLLOWUP_PATTERNS.search(text))


def _detect_write_request(text: str) -> Optional[Dict[str, Any]]:
    """Detect if the user is requesting a write operation.

    Returns a dict with requested_action and arguments if write detected,
    None if the request is read-only.
    """
    write_patterns = re.compile(
        r'\b(?:create|add|insert|update|delete|remove|disable|enable|invite|'
        r'edit|modify|set|change|revoke|approve|reject)\b.*'
        r'\b(?:user|account|profile|record|client)\b',
        re.I,
    )
    if write_patterns.search(text):
        email = _extract_email(text)
        return {
            "requested_action": "create_test_user",
            "arguments": {"email": email},
            "execution_allowed": False,
        }
    return None


def _semantic_capability_gate(text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Semantic pre-model capability gate.

    Inspects the user's request and determines whether one of Nova's
    approved capabilities can answer it. Returns (capability_name, arguments)
    or None if no capability applies.

    Precedence:
      1. provenance follow-up (handled separately in capability_gate node)
      2. write request detection (handled separately in capability_gate node)
      3. exact identity resolution (email present)
      4. exact client profile (email present + profile keywords)
      5. funding readiness (email present + readiness keywords)
      6. client count
      7. pending approvals
      8. system health
      9. recent research
      10. opportunities
      11. operational summary
      12. runtime capabilities
      13. explicit general search
      14. no tool required
    """
    lower = text.lower().strip()

    # ── Priority 3: Identity resolution (email present) ──
    email = _extract_email(text)
    if email:
        # Check client profile and funding readiness FIRST (more specific)
        profile_keywords = (
            "pull up", "show", "profile", "tell me about",
            "client profile", "client info",
        )
        if any(kw in lower for kw in profile_keywords):
            return ("get_client_profile", {"email": email})

        readiness_keywords = (
            "funding readiness", "funding ready", "ready for funding",
            "what's this client", "what are they missing", "what's blocking",
            "how close", "what should they fix", "readiness",
            "score", "funding", "credit readiness",
        )
        if any(kw in lower for kw in readiness_keywords):
            return ("get_funding_readiness", {"email": email})

        identity_keywords = (
            "look", "lookup", "look up", "check", "verify", "who",
            "account", "identity", "email", "exist", "registered",
            "find", "search", "is this", "kind of account", "type of account",
            "login", "associated", "belongs",
        )
        if any(kw in lower for kw in identity_keywords):
            return ("resolve_user_identity_by_email", {"email": email})

    # ── Priority 6: Client count ──
    client_count_keywords = (
        "how many clients", "client count", "total clients", "number of clients",
        "production clients", "active clients", "tester", "certification",
        "onboarding", "client breakdown", "client profiles", "client total",
        "production versus", "production vs", "how many production",
        "how many tester", "how many active", "how many onboarding",
        "breakdown of client", "count of client", "profiles do we have",
    )
    if any(kw in lower for kw in client_count_keywords):
        return ("get_client_count", {})

    # ── Priority 7: Pending approvals ──
    approval_keywords = (
        "pending approval", "anything to approve", "approve", "waiting for me",
        "needs my approval", "ray review", "review queue", "what's pending",
        "anything waiting", "anything pending",
        "approve anything", "approval", "approvals",
    )
    if any(kw in lower for kw in approval_keywords):
        return ("get_pending_approvals", {})

    # ── Priority 8: System health ──
    health_keywords = (
        "how is nexus doing", "system healthy", "is the system", "anything broken",
        "anything wrong", "system health", "are all services", "what needs attention",
        "technically", "failures", "anything down", "system status",
        "how's the system", "how is the system", "nexus doing",
        "anything to worry about", "any issues", "system running",
    )
    if any(kw in lower for kw in health_keywords):
        return ("get_system_health", {})

    # ── Priority 9: Recent research ──
    research_keywords = (
        "research came in", "what has alpha been researching", "any new research",
        "latest research", "recent research", "research findings", "research history",
        "what research", "alpha researching", "research runs",
    )
    if any(kw in lower for kw in research_keywords):
        return ("get_recent_research", {})

    # ── Priority 10: Opportunities ──
    opportunity_keywords = (
        "what opportunities", "any opportunities", "opportunities worth",
        "what should i review", "show current opportunities",
        "money-making opportunities", "business opportunities",
        "opportunity", "opportunities in nexus", "look at first",
    )
    if any(kw in lower for kw in opportunity_keywords):
        return ("get_opportunities", {})

    # ── Priority 11: Operational summary ──
    summary_keywords = (
        "what needs my attention", "status update", "operational summary",
        "what's going on", "what should i look at", "nexus briefing",
        "today's briefing", "give me an update", "give me a summary",
        "operational update", "what's happening", "briefing",
    )
    if any(kw in lower for kw in summary_keywords):
        return ("get_operational_summary", {})

    # ── Priority 12: Runtime capability query ──
    runtime_keywords = (
        "what can you access", "what can you read", "what systems",
        "what access do you have", "what tools", "your capabilities",
        "your access", "can you access", "what do you have access",
        "what can you look up", "what data can you", "connected to supabase",
        "are you connected", "what can you actually",
    )
    if any(kw in lower for kw in runtime_keywords):
        return ("get_runtime_capabilities", {})

    # ── Priority 13: Explicit general search ──
    search_verbs = ("search", "find", "look up", "lookup", "check", "query")
    has_search_verb = any(verb in lower for verb in search_verbs)
    operational_terms = (
        "supabase", "operational", "records", "database", "approved",
        "system", "goclear", "nexus", "process", "webhook",
    )
    has_operational_term = any(term in lower for term in operational_terms)
    if has_search_verb and has_operational_term:
        return ("general_search", {"query": text})

    # ── Priority 14: No tool required ──
    return None


# ─── Nova-Owned Supabase Tool ──────────────────────────────

def _nova_search_supabase(
    request: str,
    *,
    chat_id: int = 0,
    trace_id: str = "",
) -> Dict[str, Any]:
    """Nova-owned read-only Supabase search tool.

    This tool belongs to Nova's toolbox. It delegates to shared
    technical infrastructure for the actual queries, but Nova
    decides when to use it.

    Returns a result envelope that Nova's brain can incorporate
    into its natural response.
    """
    from nexus_agent_platform.capabilities.shared import (
        execute_shared_capability,
        detect_write_request,
    )

    if not trace_id:
        trace_id = f"nova_search_{int(time.time())}"

    # Write denial
    if _detect_write_request(request):
        return {
            "tool": "nova_search_supabase",
            "status": "denied",
            "message": (
                "Write operations are not permitted. I have read-only access. "
                "I can look up existing information but cannot create, modify, or delete anything."
            ),
            "trace_id": trace_id,
        }

    # Detect what kind of query is needed
    gate_result = _semantic_capability_gate(request)
    if gate_result is None:
        return {
            "tool": "nova_search_supabase",
            "query_type": "none",
            "status": "no_capability",
            "data": {},
            "provenance": {},
            "trace_id": trace_id,
        }

    capability, arguments = gate_result
    result = execute_shared_capability(
        "hermes_nova",
        capability,
        arguments,
        trace_id=trace_id,
    )
    return {
        "tool": "nova_search_supabase",
        "query_type": capability,
        "status": result.get("status", "unknown"),
        "data": result.get("data", {}),
        "provenance": result.get("provenance", {}),
        "trace_id": trace_id,
    }


def _format_verified_context(result: Dict[str, Any]) -> str:
    """Format a capability result as a structured VERIFIED OPERATIONAL DATA block.

    This is the authoritative context injected into the model request.
    The model must treat these facts as ground truth.
    """
    status = result.get("status", "unknown")
    query_type = result.get("query_type", "unknown")
    prov = result.get("provenance", {})

    if status == "denied":
        return result.get("message", "Write operations are not permitted.")

    if status in ("unavailable", "error"):
        error_msg = result.get("error", "Capability unavailable")
        return (
            f"[VERIFIED OPERATIONAL DATA]\n"
            f"capability: {query_type}\n"
            f"status: {status}\n"
            f"error: {error_msg}\n"
            f"[END VERIFIED OPERATIONAL DATA]\n\n"
            f"NOTE: The operational data capability returned an error. "
            f"Do NOT fabricate operational values from memory. "
            f"Tell the user the data could not be retrieved right now."
        )

    if status == "unauthorized":
        return (
            f"[VERIFIED OPERATIONAL DATA]\n"
            f"capability: {query_type}\n"
            f"status: unauthorized\n"
            f"[END VERIFIED OPERATIONAL DATA]\n\n"
            f"NOTE: This capability is not authorized. "
            f"Do NOT claim you can access data you cannot."
        )

    data = result.get("data", {})

    if query_type == "get_client_count":
        return (
            f"[VERIFIED OPERATIONAL DATA]\n"
            f"capability: get_client_count\n"
            f"status: success\n"
            f"source: supabase\n"
            f"freshness: live\n"
            f"facts:\n"
            f"- production_clients: {data.get('production_clients', 'unknown')}\n"
            f"- active: {data.get('active', 'unknown')}\n"
            f"- onboarding: {data.get('onboarding', 'unknown')}\n"
            f"- tester_or_certification: {data.get('tester_or_certification', 'unknown')}\n"
            f"- all_profiles: {data.get('all_profiles', 'unknown')}\n"
            f"[END VERIFIED OPERATIONAL DATA]"
        )

    if query_type == "resolve_user_identity_by_email":
        email = data.get("normalized_email", "unknown")
        exists = data.get("exists_anywhere", False)
        complete = data.get("verification_complete", True)
        classifications = data.get("account_classifications", [])
        sources = data.get("sources", {})

        lines = [
            f"[VERIFIED OPERATIONAL DATA]",
            f"capability: resolve_user_identity_by_email",
            f"status: {status}",
            f"source: supabase",
            f"freshness: live",
            f"normalized_email: {email}",
            f"exists_anywhere: {str(exists).lower()}",
            f"verification_complete: {str(complete).lower()}",
        ]
        if classifications:
            lines.append("account_classifications:")
            for c in classifications:
                lines.append(f"- {c}")
        if not complete:
            failed = [k for k, v in sources.items()
                      if v.get("status") in ("error", "incomplete")]
            if failed:
                lines.append(f"sources_with_errors: {', '.join(failed)}")
        lines.append("[END VERIFIED OPERATIONAL DATA]")

        if not complete:
            lines.append("")
            lines.append(
                "NOTE: Verification was incomplete. "
                "Do NOT claim the user does not exist if verification failed. "
                "Say verification was partial and which sources had issues."
            )
        elif not exists:
            lines.append("")
            lines.append(
                "NOTE: The email was not found in any approved identity source. "
                "You may state this fact clearly."
            )
        else:
            lines.append("")
            lines.append(
                "NOTE: This email exists in the approved identity sources. "
                "State the classification factually. Do not deny access to this lookup."
            )

        return "\n".join(lines)

    if query_type == "get_runtime_capabilities":
        reads = data.get("available_reads", [])
        writes = data.get("available_actions", [])
        connected = data.get("connected_systems", {}).get("supabase", {}).get("status", "unknown")
        return (
            f"[VERIFIED OPERATIONAL DATA]\n"
            f"capability: get_runtime_capabilities\n"
            f"status: success\n"
            f"source: runtime\n"
            f"freshness: live\n"
            f"facts:\n"
            f"- supabase_connected: {connected}\n"
            f"- approved_reads: {', '.join(sorted(reads))}\n"
            f"- approved_writes: {', '.join(sorted(writes)) if writes else 'none'}\n"
            f"[END VERIFIED OPERATIONAL DATA]"
        )

    if query_type == "general_search":
        matches = data.get("matches", [])
        sources_searched = data.get("sources_searched", [])
        if not matches:
            return (
                f"[VERIFIED OPERATIONAL DATA]\n"
                f"capability: general_search\n"
                f"status: not_found\n"
                f"source: supabase\n"
                f"freshness: live\n"
                f"facts:\n"
                f"- sources_searched: {', '.join(sources_searched)}\n"
                f"- match_count: 0\n"
                f"[END VERIFIED OPERATIONAL DATA]\n\n"
                f"NOTE: The search returned no matches. "
                f"Do not fabricate results."
            )
        lines = [
            f"[VERIFIED OPERATIONAL DATA]",
            f"capability: general_search",
            f"status: success",
            f"source: supabase",
            f"freshness: live",
            f"facts:",
            f"- match_count: {len(matches)}",
            f"- sources_searched: {', '.join(sources_searched)}",
        ]
        for m in matches[:5]:
            src = m.get("source", "")
            match_val = m.get("match", "")
            mtype = m.get("type", "")
            lines.append(f"- [{src}] {match_val} — {mtype}")
        lines.append("[END VERIFIED OPERATIONAL DATA]")
        return "\n".join(lines)

    if query_type == "get_system_health":
        overall = data.get("overall_status", "unknown")
        active = data.get("active_services", 0)
        degraded = data.get("degraded_services", 0)
        failed = data.get("failed_services", 0)
        unknown_svc = data.get("unknown_services", 0)
        verification = data.get("verification_complete", False)
        source_statuses = data.get("source_statuses", {})
        failures = data.get("recent_failures", [])
        warnings = data.get("important_warnings", [])
        sources = data.get("sources_checked", [])
        lines = [
            "[VERIFIED OPERATIONAL DATA]",
            "capability: get_system_health",
            f"status: {status}",
            "source: composite",
            "freshness: live",
            "facts:",
            f"- overall_status: {overall}",
            f"- active_services: {active}",
            f"- degraded_services: {degraded}",
            f"- failed_services: {failed}",
            f"- unknown_services: {unknown_svc}",
            f"- verification_complete: {str(verification).lower()}",
            f"- sources_checked: {', '.join(sources)}",
        ]
        if source_statuses:
            lines.append("- source_statuses:")
            for src, st in source_statuses.items():
                lines.append(f"  - {src}: {st}")
        if failures:
            lines.append("- recent_failures:")
            for f in failures[:5]:
                lines.append(f"  - {f}")
        if warnings:
            lines.append("- important_warnings:")
            for w in warnings[:5]:
                lines.append(f"  - {w}")
        lines.append("[END VERIFIED OPERATIONAL DATA]")
        return "\n".join(lines)

    if query_type == "get_pending_approvals":
        count = data.get("count", 0)
        items = data.get("items", [])
        lines = [
            "[VERIFIED OPERATIONAL DATA]",
            "capability: get_pending_approvals",
            "status: success",
            "source: local_json",
            "freshness: live",
            "facts:",
            f"- count: {count}",
        ]
        if items:
            lines.append("- items:")
            for item in items[:5]:
                title = item.get("title", "untitled")
                item_type = item.get("type", "unknown")
                created = item.get("created_at", "unknown")
                lines.append(f"  - [{item_type}] {title} (created: {created})")
        else:
            lines.append("- items: none pending")
        lines.append("[END VERIFIED OPERATIONAL DATA]")
        return "\n".join(lines)

    if query_type == "get_recent_research":
        runs = data.get("runs", {})
        results = data.get("results", {})
        run_items = runs.get("items", [])
        result_items = results.get("items", [])
        lines = [
            "[VERIFIED OPERATIONAL DATA]",
            "capability: get_recent_research",
            "status: success",
            "source: supabase",
            "freshness: live",
            "facts:",
            f"- total_runs: {runs.get('total', 0)}",
            f"- completed_runs: {runs.get('completed', 0)}",
            f"- total_results: {results.get('total', 0)}",
        ]
        if run_items:
            lines.append("- recent_runs:")
            for r in run_items[:5]:
                query = r.get("query", "unknown")
                status = r.get("status", "unknown")
                category = r.get("category", "unknown")
                lines.append(f"  - [{status}] {query} ({category})")
        if result_items:
            lines.append("- recent_results:")
            for r in result_items[:5]:
                title = r.get("title", "unknown")
                source = r.get("source", "unknown")
                lines.append(f"  - {title} (source: {source})")
        lines.append("[END VERIFIED OPERATIONAL DATA]")
        return "\n".join(lines)

    if query_type == "get_opportunities":
        total = data.get("total", 0)
        by_state = data.get("by_state", {})
        items = data.get("items", [])
        lines = [
            "[VERIFIED OPERATIONAL DATA]",
            "capability: get_opportunities",
            "status: success",
            "source: supabase",
            "freshness: live",
            "facts:",
            f"- total: {total}",
            f"- active: {by_state.get('active', 0)}",
            f"- reviewed: {by_state.get('reviewed', 0)}",
            f"- rejected: {by_state.get('rejected', 0)}",
        ]
        if items:
            lines.append("- opportunities:")
            for o in items[:5]:
                title = o.get("title", "unknown")
                action = o.get("action_state", "unknown")
                revenue = o.get("revenue_potential", "unknown")
                lines.append(f"  - {title} (state: {action}, revenue: {revenue})")
        lines.append("[END VERIFIED OPERATIONAL DATA]")
        return "\n".join(lines)

    if query_type == "get_client_profile":
        found = data.get("found", False)
        ambiguous = data.get("ambiguous", False)
        if not found:
            return (
                "[VERIFIED OPERATIONAL DATA]\n"
                "capability: get_client_profile\n"
                "status: success\n"
                "source: supabase\n"
                "freshness: live\n"
                "facts:\n"
                "- found: false\n"
                "[END VERIFIED OPERATIONAL DATA]\n\n"
                "NOTE: No client profile was found for the given lookup. "
                "Do not fabricate client data."
            )
        if ambiguous:
            matches = data.get("matches", [])
            lines = [
                "[VERIFIED OPERATIONAL DATA]",
                "capability: get_client_profile",
                "status: success",
                "source: supabase",
                "freshness: live",
                "facts:",
                "- found: true",
                "- ambiguous: true",
                f"- match_count: {data.get('match_count', 0)}",
            ]
            for m in matches[:3]:
                lines.append(f"  - {m.get('client_label', 'unknown')} ({m.get('classification', 'unknown')})")
            lines.append("[END VERIFIED OPERATIONAL DATA]")
            return "\n".join(lines)
        classification = data.get("classification", "unknown")
        status_val = data.get("status", "unknown")
        onboarding = data.get("onboarding_step", "unknown")
        lines = [
            "[VERIFIED OPERATIONAL DATA]",
            "capability: get_client_profile",
            "status: success",
            "source: supabase",
            "freshness: live",
            "facts:",
            f"- found: true",
            f"- client_id: {data.get('client_id', 'unknown')}",
            f"- status: {status_val}",
            f"- classification: {classification}",
            f"- onboarding_step: {onboarding}",
            f"- business_name: {data.get('business_name', 'unknown')}",
        ]
        lines.append("[END VERIFIED OPERATIONAL DATA]")
        return "\n".join(lines)

    if query_type == "get_funding_readiness":
        readiness = data.get("funding_readiness_status", "unknown")
        identifier = data.get("client_identifier", "unknown")
        client_found = data.get("client_found", False)
        verification = data.get("verification_complete", False)
        lines = [
            "[VERIFIED OPERATIONAL DATA]",
            "capability: get_funding_readiness",
            f"status: {status}",
            "source: supabase",
            "freshness: live",
            "facts:",
            f"- client_identifier: {identifier}",
            f"- client_found: {str(client_found).lower()}",
            f"- funding_readiness_status: {readiness}",
            f"- verification_complete: {str(verification).lower()}",
        ]
        if client_found:
            lines.append(f"- classification: {data.get('classification', 'unknown')}")
            lines.append(f"- client_status: {data.get('client_status', 'unknown')}")
            lines.append(f"- onboarding_step: {data.get('onboarding_step', 'unknown')}")
            available = data.get("available_signals", [])
            if available:
                lines.append(f"- available_signals: {', '.join(available)}")
            missing = data.get("missing_signals", [])
            if missing:
                lines.append("- missing_signals:")
                for m in missing:
                    lines.append(f"  - {m}")
        lines.append("[END VERIFIED OPERATIONAL DATA]")
        return "\n".join(lines)

    if query_type == "get_operational_summary":
        components = data
        comp_statuses = result.get("data", {}).get("component_statuses", {})
        # Also check the top-level component_statuses from the handler
        if not comp_statuses:
            comp_statuses = {}
            for name in ["system_health", "client_counts", "pending_approvals",
                         "recent_research", "opportunities"]:
                comp = components.get(name, {})
                comp_statuses[name] = comp.get("status", "unknown")
        lines = [
            "[VERIFIED OPERATIONAL DATA]",
            "capability: get_operational_summary",
            f"status: {status}",
            "source: composite",
            "freshness: live",
            "facts:",
        ]
        # System health
        sh = components.get("system_health", {})
        sh_status = sh.get("status", "unknown")
        sh_data = sh.get("data", {})
        if sh_status in ("unavailable", "error"):
            lines.append(f"- system_health: {sh_status} (data unavailable)")
        else:
            lines.append(f"- system_health: {sh_data.get('overall_status', 'unknown')} "
                          f"({sh_data.get('active_services', 0)} active, "
                          f"verification: {sh_data.get('verification_complete', False)})")
        # Client counts
        cc = components.get("client_counts", {})
        cc_status = cc.get("status", "unknown")
        cc_data = cc.get("data", {})
        if cc_status in ("unavailable", "error"):
            lines.append(f"- client_counts: {cc_status} (data unavailable)")
        else:
            lines.append(f"- production_clients: {cc_data.get('production_clients', 'unknown')}")
            lines.append(f"- tester_or_certification: {cc_data.get('tester_or_certification', 'unknown')}")
        # Pending approvals
        pa = components.get("pending_approvals", {})
        pa_status = pa.get("status", "unknown")
        pa_data = pa.get("data", {})
        if pa_status in ("unavailable", "error"):
            lines.append(f"- pending_approvals: {pa_status} (data unavailable)")
        else:
            count = pa_data.get("count", 0)
            data_avail = pa_data.get("data_available", True)
            lines.append(f"- pending_approvals: {count} (verified, data_available: {data_avail})")
        # Recent research
        rr = components.get("recent_research", {})
        rr_status = rr.get("status", "unknown")
        rr_data = rr.get("data", {})
        if rr_status in ("unavailable", "error"):
            lines.append(f"- recent_research: {rr_status} (data unavailable)")
        else:
            runs_total = rr_data.get("runs", {}).get("total", 0) if rr_data.get("runs") else 0
            lines.append(f"- recent_research_runs: {runs_total} (verified)")
        # Opportunities
        opp = components.get("opportunities", {})
        opp_status = opp.get("status", "unknown")
        opp_data = opp.get("data", {})
        if opp_status in ("unavailable", "error"):
            lines.append(f"- opportunities: {opp_status} (data unavailable)")
        else:
            opp_total = opp_data.get("total", 0) if opp_data.get("total") is not None else 0
            active = opp_data.get("by_state", {}).get("active", 0) if opp_data.get("by_state") else 0
            lines.append(f"- opportunities: {opp_total} ({active} active, verified)")
        lines.append("[END VERIFIED OPERATIONAL DATA]")
        return "\n".join(lines)

    # Fallback
    return (
        f"[VERIFIED OPERATIONAL DATA]\n"
        f"capability: {query_type}\n"
        f"status: {status}\n"
        f"[END VERIFIED OPERATIONAL DATA]"
    )


def _format_provenance_context(provenance: Dict[str, Any]) -> str:
    """Format stored provenance as a context block for follow-up questions."""
    if not provenance:
        return (
            "[PROVENANCE]\n"
            "status: no_recent_capability\n"
            "error: No recent operational capability was used in this conversation.\n"
            "[END PROVENANCE]"
        )

    # Convert UTC retrieval time to Phoenix-local for natural display
    retrieved_at = provenance.get("retrieved_at", "unknown")
    phoenix_time = ""
    if retrieved_at and retrieved_at != "unknown":
        try:
            from zoneinfo import ZoneInfo
            utc_dt = datetime.fromisoformat(retrieved_at.replace("Z", "+00:00"))
            phoenix_dt = utc_dt.astimezone(ZoneInfo("America/Phoenix"))
            phoenix_time = phoenix_dt.strftime("%I:%M %p Phoenix time on %A, %B %-d")
        except Exception:
            phoenix_time = ""

    lines = [
        "[PROVENANCE]",
        f"capability: {provenance.get('capability', 'unknown')}",
        f"status: {provenance.get('status', 'unknown')}",
        f"source: {provenance.get('source', 'unknown')}",
        f"source_type: {provenance.get('source_type', 'unknown')}",
        f"freshness: {provenance.get('freshness', 'unknown')}",
        f"retrieved_at_utc: {retrieved_at}",
    ]
    if phoenix_time:
        lines.append(f"retrieved_at_phoenix: {phoenix_time}")
    handler = provenance.get("handler", "")
    if handler:
        lines.append(f"handler: {handler}")
    sources_checked = provenance.get("sources_checked", [])
    if sources_checked:
        lines.append(f"sources_checked: {', '.join(sources_checked)}")
    source_statuses = provenance.get("source_statuses", {})
    if source_statuses:
        lines.append("source_statuses:")
        for src, st in source_statuses.items():
            lines.append(f"  - {src}: {st}")
    verification = provenance.get("verification_complete")
    if verification is not None:
        lines.append(f"verification_complete: {str(verification).lower()}")
    lines.append("[END PROVENANCE]")
    lines.append("")
    lines.append(
        "NOTE: Answer the user's provenance question using the data above. "
        "Be specific about capability name, source, freshness, and retrieval time. "
        "For natural responses, use the Phoenix-local time."
    )
    return "\n".join(lines)


# ─── Model Gateway ─────────────────────────────────────────

async def _call_model(messages: List[Dict[str, str]], chat_id: int) -> Dict[str, Any]:
    """Call the configured OpenRouter model via LlmGatewayAdapter."""
    from nexus_agent_platform.workflows.litellm_adapter import LlmGatewayAdapter

    model = os.getenv("HERMES_NOVA_MODEL", DEFAULT_MODEL)
    adapter = LlmGatewayAdapter(agent_id=AGENT_ID)

    result = await adapter.completion(
        model=model,
        messages=messages,
        temperature=DEFAULT_TEMPERATURE,
        max_tokens=DEFAULT_MAX_TOKENS,
    )
    return result


# ─── Response Validation ───────────────────────────────────

_VALIDATION_PATTERNS = [
    # Provider exception text leaked into response
    (re.compile(r'(?:openrouter|openai|anthropic|API\s+error|rate\s+limit|timeout|500|502|503)', re.I),
     "provider_exception"),
    # Leaked system prompt
    (re.compile(r'you are (?:Hermes|Nexus|Alpha|a system|an AI (?:system|designed))', re.I),
     "system_prompt_leak"),
    # False tool claims — unrestricted access (NOT governed reads)
    (re.compile(r'(?:I\s+(?:have\s+)?access(?:ed|ing)?\s+(?:your|the)\s+(?:Supabase|database|Oanda|trading|Temporal|calendar|email))', re.I),
     "false_tool_claim"),
    # False Nexus write claims
    (re.compile("(?:I['\u2019]ll|I will)\\s+(?:create|add|insert|update|delete|remove|disable|enable|invite)\\s+(?:a\\s+)?(?:new\\s+)?(?:user|account|profile)", re.I),
     "false_nexus_claim"),
    # Generic capability menu
    (re.compile(r'(?:here\s+(?:is|are)\s+(?:a\s+)?(?:list|menu)\s+of\s+(?:my\s+)?(?:capabilities|things?\s+I\s+can))', re.I),
     "capability_menu"),
]


def _validate_against_capability(
    response: str,
    capability_result: Optional[Dict[str, Any]],
) -> Optional[str]:
    """Validate model response against verified capability facts.

    Returns error reason if the response contradicts verified data,
    None if the response is consistent.
    """
    if not capability_result:
        return None

    status = capability_result.get("status", "unknown")
    query_type = capability_result.get("query_type", "unknown")
    data = capability_result.get("data", {})

    # Only validate successful results
    if status != "success":
        return None

    response_lower = response.lower()

    if query_type == "get_client_count":
        # Check that the model didn't fabricate different numbers
        verified_production = data.get("production_clients")
        verified_tester = data.get("tester_or_certification")
        verified_total = data.get("all_profiles")

        if verified_production is not None:
            # Look for fabricated production numbers that differ from verified
            number_claims = re.findall(
                r'(\d+)\s*(?:production|client)', response_lower
            )
            for claim in number_claims:
                claimed_num = int(claim)
                if claimed_num != verified_production and claimed_num > 50:
                    return "capability_contradiction"

        if verified_tester is not None:
            number_claims = re.findall(
                r'(\d+)\s*(?:tester|certification)', response_lower
            )
            for claim in number_claims:
                claimed_num = int(claim)
                if claimed_num != verified_tester and claimed_num > 50:
                    return "capability_contradiction"

    if query_type == "resolve_user_identity_by_email":
        exists = data.get("exists_anywhere", False)
        complete = data.get("verification_complete", True)

        # If capability says email exists, reject denial of lookup
        if exists and complete:
            denial_phrases = [
                "can't look up", "cannot look up",
                "can't access", "cannot access",
                "don't have access", "do not have access",
                "unable to look up", "not able to look up",
                "can't check", "cannot check",
            ]
            for phrase in denial_phrases:
                if phrase in response_lower:
                    return "capability_contradiction"

        # If capability says email exists, reject "does not exist" claim
        if exists and complete:
            nonexistent_claims = [
                "does not exist", "doesnt exist", "doesn't exist",
                "not found", "no account",
                "not registered", "no user",
            ]
            for claim in nonexistent_claims:
                if claim in response_lower:
                    return "capability_contradiction"

    # ── Status semantics validation ──
    # Prevent model from treating unavailable/error as empty/zero

    # For any capability with unavailable/error status, reject claims of zero/none
    if status in ("unavailable", "error"):
        zero_claims = [
            "no research", "no recent research", "there was no research",
            "no opportunities", "there are no opportunities", "there were no opportunities",
            "no approvals", "no pending approvals",
            "no failures", "no issues", "everything is healthy", "system is healthy",
            "all services", "everything is running",
        ]
        for claim in zero_claims:
            if claim in response_lower:
                return "status_contradiction"

    # For system health with overall_status=unknown, reject "degraded" or "unhealthy"
    if query_type == "get_system_health" and status == "success":
        overall = data.get("overall_status", "unknown")
        if overall == "unknown":
            degraded_claims = [
                "is degraded", "is unhealthy", "is failing", "is down",
                "facing challenges", "having issues", "services are failing",
                "system is degraded", "system is unhealthy",
            ]
            for claim in degraded_claims:
                if claim in response_lower:
                    return "status_contradiction"

    # For funding readiness with not_yet_certified, reject ready/not_ready verdicts
    if query_type == "get_funding_readiness":
        readiness = data.get("funding_readiness_status", "unknown")
        if readiness == "not_yet_certified":
            verdict_claims = [
                "is ready", "is not ready", "is almost ready",
                "funding ready", "not funding ready",
                "credit ready", "not credit ready",
            ]
            for claim in verdict_claims:
                if claim in response_lower:
                    return "status_contradiction"

    # For operational summary with partial status, reject "everything is fine"
    if query_type == "get_operational_summary" and status == "partial":
        all_ok_claims = [
            "everything is", "all systems", "everything looks good",
            "all operational", "everything is running",
        ]
        for claim in all_ok_claims:
            if claim in response_lower:
                return "status_contradiction"

    return None


def validate_response(text: str, user_message: str) -> Optional[str]:
    """Validate a response. Returns error reason if invalid, None if OK."""
    if not text or not text.strip():
        return "empty_response"

    for pattern, reason in _VALIDATION_PATTERNS:
        if pattern.search(text):
            return reason

    # Check for leaked secrets (bot tokens, API keys)
    if re.search(r'\d{9,10}:[A-Za-z0-9_-]{35}', text):
        return "leaked_secret"
    if re.search(r'sk-or-v1-[A-Za-z0-9]{20,}', text):
        return "leaked_secret"

    return None


def _build_fallback_response(error_reason: str, user_message: str) -> str:
    """Build a degraded-mode response when the model fails."""
    if error_reason == "empty_response":
        return "I'm not sure how to respond to that. Could you rephrase?"
    if error_reason in ("provider_exception", "leaked_secret"):
        return "I had trouble generating a response. Let me try again — could you rephrase?"
    if error_reason in ("false_tool_claim", "false_nexus_claim"):
        return "I don't have access to those systems. I'm Nova — I'm here to talk, not operate tools."
    if error_reason == "system_prompt_leak":
        return "Let me rephrase that more naturally. What else would you like to know?"
    if error_reason == "capability_menu":
        return "I'm Nova — I just like to have conversations. What's on your mind?"
    if error_reason == "capability_contradiction":
        return (
            "I need to correct myself — the verified operational data shows something "
            "different from what I just said. Let me give you the accurate information."
        )
    return "I'm not sure how to respond to that. Could you try again?"


# ─── Graph Node Functions ──────────────────────────────────

def _classify_intent(state: AgentState) -> AgentState:
    """Classify the user message into a response mode."""
    mode = classify_response_mode(state.user_message)
    state.intent = mode
    state.metadata["nova_mode"] = mode
    return state


def _handle_utility(state: AgentState) -> AgentState:
    """Handle simple utility requests that don't need the model."""
    mode = state.intent or "CONVERSATION"
    text = state.user_message

    if mode == "TIME_REQUEST":
        lower = text.lower()
        if any(w in lower for w in ["day", "date"]):
            state.assistant_response = _get_phoenix_date()
        else:
            state.assistant_response = _get_phoenix_time()
        state.metadata["utility_used"] = "time"
        return state

    if mode == "ARITHMETIC":
        result = _evaluate_arithmetic(text)
        if result:
            state.assistant_response = result
            state.metadata["utility_used"] = "arithmetic"
            return state

    if mode == "CONVERSATION_RESET":
        state.metadata["reset_requested"] = True
        state.assistant_response = "Got it — fresh start. What would you like to talk about?"
        state.metadata["utility_used"] = "reset"
        return state

    # Not a utility — pass through to capability gate
    state.metadata["utility_used"] = None
    return state


def _capability_gate(state: AgentState) -> AgentState:
    """Semantic pre-model capability gate.

    This node runs AFTER handle_utility and BEFORE build_context.
    It inspects the user's request and determines whether an approved
    capability can answer it — WITHOUT requiring the user to say "Supabase."

    The gate:
      1. Checks for provenance follow-ups → answer from stored provenance
      2. Checks for write requests → denied
      3. Matches semantic intent to an approved capability
      4. Executes the capability through the shared certified layer
      5. Stores the normalized result and provenance in state
      6. Persists provenance for follow-up queries
      7. The conversational model still generates the natural-language response

    Capability precedence:
      1. provenance follow-up
      2. write request detection
      3. exact identity resolution (email present)
      4. exact client profile
      5. funding readiness
      6. client count
      7. pending approvals
      8. system health
      9. recent research
      10. opportunities
      11. operational summary
      12. runtime capabilities
      13. explicit general search
      14. no tool required
    """
    # Skip if utility already handled it
    if state.assistant_response:
        state.metadata["capability_gate"] = {
            "decision": "skip_utility",
            "capability": None,
        }
        return state

    text = state.user_message
    chat_id = state.metadata.get("chat_id", 0)
    trace_id = f"nova_gate_{chat_id}_{int(time.time())}"

    # ── Priority 1: Provenance follow-up ──
    if _detect_provenance_followup(text):
        stored = load_provenance(chat_id)
        state.metadata["capability_gate"] = {
            "decision": "provenance_followup",
            "capability": "provenance_followup",
            "trace_id": trace_id,
        }
        state.metadata["capability_result"] = {
            "tool": "nova_search_supabase",
            "query_type": "provenance_followup",
            "status": "success",
            "data": {"stored_provenance": stored},
            "provenance": stored or {},
            "trace_id": trace_id,
        }
        return state

    # ── Priority 2: Write detection ──
    write_request = _detect_write_request(text)
    if write_request:
        email = write_request["arguments"].get("email")

        # Optionally perform the approved identity read first
        identity_result = None
        if email:
            from nexus_agent_platform.capabilities.shared import execute_shared_capability
            identity_result = execute_shared_capability(
                "hermes_nova",
                "resolve_user_identity_by_email",
                {"email": email},
                trace_id=trace_id,
            )

        state.metadata["capability_gate"] = {
            "decision": "write_denied",
            "capability": "write_request",
            "arguments": write_request,
            "trace_id": trace_id,
        }
        state.metadata["capability_result"] = {
            "tool": "nova_search_supabase",
            "query_type": "write_denied",
            "status": "denied",
            "message": (
                "Write operations are not permitted. I have read-only access. "
                "I can look up existing information but cannot create, modify, or delete anything."
            ),
            "identity_check": identity_result,
            "trace_id": trace_id,
        }
        return state

    # ── Priorities 3-14: Semantic capability gate ──
    gate_result = _semantic_capability_gate(text)
    if gate_result is None:
        state.metadata["capability_gate"] = {
            "decision": "no_capability",
            "capability": None,
            "trace_id": trace_id,
        }
        state.metadata["capability_result"] = None
        return state

    capability, arguments = gate_result

    # Execute through shared certified layer
    from nexus_agent_platform.capabilities.shared import execute_shared_capability
    try:
        result = execute_shared_capability(
            "hermes_nova",
            capability,
            arguments,
            trace_id=trace_id,
        )
    except Exception as exc:
        log.error("Capability gate execution failed for %s: %s", capability, exc)
        result = {
            "status": "error",
            "capability": capability,
            "source": "capability_gate",
            "source_type": "local_runtime_read",
            "freshness": "unknown",
            "data": {},
            "error": str(exc),
            "provenance": {"capability": capability, "status": "error", "trace_id": trace_id},
        }

    state.metadata["capability_gate"] = {
        "decision": "capability_executed",
        "capability": capability,
        "arguments": arguments,
        "status": result.get("status", "unknown"),
        "trace_id": trace_id,
    }
    state.metadata["capability_result"] = {
        "tool": "nova_search_supabase",
        "query_type": capability,
        "status": result.get("status", "unknown"),
        "data": result.get("data", {}),
        "provenance": result.get("provenance", {}),
        "trace_id": trace_id,
    }

    # Persist provenance for follow-up queries
    prov = result.get("provenance", {})
    if prov:
        save_provenance(chat_id, prov)

    return state


def _build_context(state: AgentState) -> AgentState:
    """Build the model context with SOUL, conversation history, and verified operational data."""
    chat_id = state.metadata.get("chat_id", 0)

    # Load conversation history
    history = load_memory(chat_id)
    state.metadata["conversation_turns"] = len(history) // 2

    # Build messages for the model
    messages = [{"role": "system", "content": SOUL}]

    # Add conversation history (bounded)
    for msg in history[-MEMORY_MAX_TURNS * 2:]:
        messages.append(msg)

    # Build the user message, potentially with verified operational data
    user_content = state.user_message

    capability_result = state.metadata.get("capability_result")
    if capability_result:
        query_type = capability_result.get("query_type", "")

        if query_type == "provenance_followup":
            stored = capability_result.get("data", {}).get("stored_provenance")
            provenance_context = _format_provenance_context(stored)
            user_content = (
                f"{state.user_message}\n\n"
                f"{provenance_context}"
            )
        else:
            verified_context = _format_verified_context(capability_result)
            user_content = (
                f"{state.user_message}\n\n"
                f"{verified_context}\n\n"
                f"Respond naturally using the verified data above. "
                f"Do not contradict the verified facts. "
                f"Do not fabricate alternative values. "
                f"Do not deny access to data that was successfully retrieved."
            )

    messages.append({"role": "user", "content": user_content})

    state.metadata["model_messages"] = messages
    state.metadata["model_received_verified_context"] = capability_result is not None
    return state


def _generate_response(state: AgentState) -> AgentState:
    """Generate a response using the configured model."""
    # Skip if utility already handled it
    if state.assistant_response:
        return state

    import asyncio

    messages = state.metadata.get("model_messages", [])
    chat_id = state.metadata.get("chat_id", 0)

    try:
        result = asyncio.run(_call_model(messages, chat_id))
        content = result.get("content", "")
        model_used = result.get("model", os.getenv("HERMES_NOVA_MODEL", DEFAULT_MODEL))
        usage = result.get("usage", {})

        state.metadata["model_used"] = model_used
        state.metadata["model_usage"] = usage
        state.metadata["model_provider"] = "openrouter"
        state.metadata["provider_latency_ms"] = result.get("latency_ms", 0)
    except Exception as exc:
        log.error("Nova model call failed: %s", exc)
        state.metadata["model_error"] = str(exc)
        content = ""

    state.assistant_response = content
    return state


def _validate_output(state: AgentState) -> AgentState:
    """Validate the generated response against capability facts and general rules."""
    # Standard validation
    error_reason = validate_response(state.assistant_response, state.user_message)

    # Capability contradiction validation
    if not error_reason:
        capability_result = state.metadata.get("capability_result")
        if capability_result:
            error_reason = _validate_against_capability(
                state.assistant_response, capability_result
            )

    if error_reason:
        state.metadata["validation_error"] = error_reason
        state.metadata["validation_regen"] = True

        # One regeneration attempt
        import asyncio
        messages = state.metadata.get("model_messages", [])
        chat_id = state.metadata.get("chat_id", 0)

        try:
            result = asyncio.run(_call_model(messages, chat_id))
            content = result.get("content", "")
            if content and not validate_response(content, state.user_message):
                # Also check capability contradiction on regen
                capability_result = state.metadata.get("capability_result")
                if capability_result:
                    cap_err = _validate_against_capability(content, capability_result)
                    if cap_err:
                        state.assistant_response = _build_fallback_response(error_reason, state.user_message)
                        state.metadata["fallback_used"] = True
                        return state
                state.assistant_response = content
                state.metadata["regen_success"] = True
                return state
        except Exception:
            pass

        # Regen failed — use fallback
        state.assistant_response = _build_fallback_response(error_reason, state.user_message)
        state.metadata["fallback_used"] = True

    return state


def _compose_output(state: AgentState) -> AgentState:
    """Final composition — save memory and update context."""
    chat_id = state.metadata.get("chat_id", 0)

    if not state.assistant_response:
        state.assistant_response = "I'm not sure how to respond to that. Could you try again?"

    # Skip saving if this is a reset — the worker handles file deletion
    if state.metadata.get("reset_requested"):
        _clear_provenance(chat_id)
        state.metadata["response_mode"] = state.intent
        state.metadata["conversation_hash"] = _conversation_hash(
            state.metadata.get("model_messages", [])
        )
        return state

    # Save conversation to memory
    if chat_id and state.user_message:
        history = load_memory(chat_id)
        history.append({"role": "user", "content": state.user_message})
        history.append({"role": "assistant", "content": state.assistant_response})
        save_memory(chat_id, history)

    # Update metadata
    state.metadata["response_mode"] = state.intent
    state.metadata["conversation_hash"] = _conversation_hash(
        state.metadata.get("model_messages", [])
    )

    return state


# ─── Graph Builder ─────────────────────────────────────────

def build_nova_graph() -> GraphAdapter:
    """Build and compile the Nova LangGraph.

    Graph flow:
      classify_intent → handle_utility → capability_gate → build_context
      → generate_response → validate_output → compose_output

    The capability_gate runs before model generation. It semantically
    inspects the user's request and executes approved capabilities
    through the shared certified layer. The conversational model
    generates the final natural-language response using verified data.
    """
    graph = GraphAdapter(agent_id=AGENT_ID)
    graph.add_node("classify_intent", _classify_intent)
    graph.add_node("handle_utility", _handle_utility)
    graph.add_node("capability_gate", _capability_gate)
    graph.add_node("build_context", _build_context)
    graph.add_node("generate_response", _generate_response)
    graph.add_node("validate_output", _validate_output)
    graph.add_node("compose_output", _compose_output)

    graph.add_edge("classify_intent", "handle_utility")
    graph.add_edge("handle_utility", "capability_gate")
    graph.add_edge("capability_gate", "build_context")
    graph.add_edge("build_context", "generate_response")
    graph.add_edge("generate_response", "validate_output")
    graph.add_edge("validate_output", "compose_output")

    graph.set_entry_point("classify_intent")
    graph.set_finish_point("compose_output")
    return graph.compile()


# ─── Singleton Instances ───────────────────────────────────

_graph: Optional[GraphAdapter] = None
_otel: Optional[OtelAdapter] = None


def get_nova_graph() -> GraphAdapter:
    global _graph
    if _graph is None:
        _graph = build_nova_graph()
    return _graph


def get_nova_otel() -> OtelAdapter:
    global _otel
    if _otel is None:
        _otel = OtelAdapter(AGENT_ID)
    return _otel
