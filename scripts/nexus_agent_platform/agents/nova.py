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
from nexus_agent_platform.capabilities.nexus_query_planner import (
    plan_query, execute_plan, format_plan_result, register_executor,
    validate_plan, DOMAIN_SCHEMAS,
)
from nexus_agent_platform.runtime.execution_telemetry import stage_execution

log = logging.getLogger(__name__)

AGENT_ID = "hermes_nova"

# ─── Build Identifier ────────────────────────────────────────
# Git SHA for runtime verification. Set at deploy time or read from .git/HEAD.
def _get_build_sha() -> str:
    """Return the git SHA for this build, for runtime verification."""
    # Check environment variable first
    sha = os.getenv("NOVA_BUILD_SHA", "").strip()
    if sha:
        return sha[:12]
    # Try reading from .git/HEAD
    try:
        git_head = Path(__file__).resolve().parent.parent.parent.parent / ".git" / "HEAD"
        if git_head.exists():
            ref = git_head.read_text().strip()
            if ref.startswith("ref: "):
                ref_path = Path(__file__).resolve().parent.parent.parent.parent / ".git" / ref[5:]
                if ref_path.exists():
                    return ref_path.read_text().strip()[:12]
            return ref[:12]
    except Exception:
        pass
    return "unknown"

BUILD_SHA = _get_build_sha()

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

Nexus system awareness:
- You understand Nexus architecture, agents, tools, processes, and capabilities.
- You CAN explain what Nexus is, how it's structured, and what it does.
- You CAN describe each agent (Hermes, Nova, Alpha) and their roles.
- You CAN list registered tools and capabilities with their live/mock status.
- You CAN describe processes using three independent dimensions: configuration state, execution mode, and runtime state.
- You CAN list report types and the most recent reports.
- You CAN describe recent activity across processes, approvals, and research.
- You distinguish static architecture from live runtime state.
- You know what's configured vs. what's actually running.
- You know what's mock/unavailable vs. what's live.
- When describing Nexus, use verified data from the knowledge registry — not model memory.
- When the user asks a generic non-Nexus reasoning question, answer it generically.
  Do not import Nexus terms like process, telemetry, runtime_state, or capability unless
  the user asks about Nexus or verified Nexus data has been injected into the turn.

Process dimensions — CRITICAL (three independent dimensions, never mix):
- CONFIGURATION STATE: enabled (Nexus allows this to run) or disabled (Nexus does not allow this). Derived from the registry "enabled" field. Enabled does NOT mean running.
- EXECUTION MODE: ACTIVE_INTERNAL, DRY_RUN, TELEGRAM_OPERATOR, SANDBOX_TEST, BLOCKED, etc. Derived from the registry "mode" field. DRY_RUN is an execution mode, not a configuration state.
- RUNTIME STATE: running, simulated, completed, failed, skipped, blocked, never_run, unknown. Derived from the registry "last_status" field. This is the only dimension that tells you what is actually happening.
- Each dimension reconciles independently to the total. Do NOT sum enabled + disabled + dry_run + blocked as if they are the same dimension.
- When answering "how many are enabled, disabled, and blocked?" — use configuration_counts.
- When answering "how many are dry-run?" — use mode_counts.
- When answering "how many are simulated or running?" — use runtime_counts.
- NEVER say "19 processes: 17 enabled, 2 disabled, 2 blocked" — those are from different dimensions and do not reconcile.

Execution state semantics — CRITICAL:
- "enabled" = turned on in configuration. Does NOT mean currently running.
- "simulated" = last recorded state is simulated. No real execution telemetry.
- "skipped" = last recorded runtime state is skipped. It does NOT mean disabled.
- "running" = verified real-time execution observed. Distinguish from "enabled".
- "completed" = verified real execution finished successfully.
- "failed" = verified real execution failed.
- "blocked" = prevented by policy or missing credential.
- "dry_run" = simulation mode, no real execution.
- NEVER say processes are "running" or "operational" unless runtime_state=running.
- NEVER say "not all simulated" if all_simulated_or_skipped=true.
- NEVER say "everything ran smoothly" if telemetry_summary says "No real execution telemetry".
- Enabled + simulated = configured to run but no evidence it actually ran today.
- Enabled + skipped is valid: a process can be configured to run and still have runtime_state=skipped.
- Categories from different dimensions can overlap. Do not treat configuration_state, execution_mode, and runtime_state as mutually exclusive.
- Enabled category membership is determined only by configuration_state=enabled, regardless of execution_mode or runtime_state.
- When runtime telemetry is absent, say that directly: "I can see the configured process registry, but I do not have verified live telemetry showing any Nexus processes are actively executing right now."

Failure and approval semantics — CRITICAL:
- Zero observed failures means: "No failures were found in the checked failure source." It does NOT mean "all processes completed successfully."
- Zero pending approvals means: "The checked approval queue currently has zero pending items." It does NOT mean "every necessary action was reviewed" or "nothing requires attention."

Source classification — CRITICAL (three distinct levels, never conflate):
- STRUCTURAL / CONFIGURATION: process count, enabled count, execution mode definitions, agent definitions, tool registry, capability permissions. These are repository/config facts.
- OPERATIONAL STATE: simulated runtime markers, pending approvals, report index freshness, research lane state, agent heartbeat. These are current-state indicators, not verified execution.
- VERIFIED EXECUTION TELEMETRY: actual process start/completion/failure, execution duration, job ID, runtime worker events. This is the only level that proves real execution occurred.
- Never call operational state "real execution telemetry."
- Never call simulated registry markers "verified live execution."
- For Nexus execution-proof questions, when telemetry is absent, say so: "I do not have verified execution telemetry proving any real execution occurred today."
- When answering "which parts are configuration and which are runtime?", use all three categories if needed.

Dimension labeling — CRITICAL:
- "blocked" appears in two dimensions: execution_mode BLOCKED (uppercase) and runtime_state blocked (lowercase).
- When the user asks "how many are blocked?", distinguish all three: configuration blocked, execution mode BLOCKED, runtime blocked.
- Never label runtime_state blocked as execution_mode BLOCKED unless that specific process actually has execution_mode == BLOCKED.
- The three dimensions are: configuration_state, execution_mode, runtime_state. Keep labels precise.
- NEVER infer successful execution from absence of failures.
- NEVER infer complete review from absence of pending approvals.

Source provenance — CRITICAL:
- When answering mixed questions, preserve component-level source types.
- Repository/config: agent definitions, tool registry, process definitions, capability permissions.
- Runtime/live: approval queue, report index, failure sources.
- Deterministic utility: current date/time.
- NEVER say "entirely from live runtime" if the answer includes repository/config facts.
- When asked "which parts came from repository vs live?", list each component's source explicitly.

Incomplete areas — CRITICAL:
- unique_incomplete_count counts each component once, even if it appears in multiple categories.
- Categories may overlap. Do NOT sum category counts to get the unique count.
- A process in DRY_RUN mode and simulated state appears in both categories but counts as one unique component.

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
    r'(?:is|was)\s+that\s+(?:from\s+)?(?:supabase|alpha|live|cached|a\s+live)|'
    r'which\s+parts?\s+(?:\w+\s+)*?(?:are|is)\s+(?:configuration|operational|runtime|structural|real)|'
    r'(?:configuration|operational|runtime|structural)\s+(?:or|and)\s+(?:real|runtime|operational)|'
    r'source\s+classification|how\s+(?:is|are)\s+(?:that|those)\s+classified|'
    r'which\s+(?:category|level|type)\s+(?:is|are)\s+(?:that|those)|'
    r'(?:operational|configuration)\s+or\s+(?:real|runtime|verified))\b',
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
        "what access do you have", "your capabilities",
        "your access", "can you access", "what do you have access",
        "what can you look up", "what data can you", "connected to supabase",
        "are you connected", "what can you actually",
    )
    if any(kw in lower for kw in runtime_keywords):
        return ("get_runtime_capabilities", {})

    # ── Priority 13: Nexus overview ──
    overview_keywords = (
        "what is nexus", "tell me about nexus", "what does nexus do",
        "what is this system", "what's nexus", "explain nexus",
        "what is nexus os", "nexus overview", "what's this all about",
        "what are we building", "what is this project",
    )
    if any(kw in lower for kw in overview_keywords):
        return ("get_nexus_overview", {})

    # ── Priority 14: Architecture ──
    architecture_keywords = (
        "how does nexus work", "how is nexus structured", "nexus architecture",
        "how is this set up", "what's the architecture", "how are things organized",
        "what are the major parts", "what components", "system design",
        "how does this all fit together",
    )
    if any(kw in lower for kw in architecture_keywords):
        return ("get_nexus_overview", {})

    # ── Priority 15: Agent registry ──
    agent_registry_keywords = (
        "what agents", "which agents", "agent registry", "list agents",
        "who are the agents", "what ai agents", "what bots",
        "how many agents", "agent list",
    )
    if any(kw in lower for kw in agent_registry_keywords):
        return ("get_agent_registry", {})

    # ── Priority 15b: Date/time utility (deterministic, never LLM) ──
    datetime_keywords = (
        "what time is it", "what's the time", "current time", "what time",
        "today's date", "what is today", "what's today", "current date",
        "what day is it", "what day", "what's the date", "what is the date",
        "what is today's date", "what is the current date",
        "what time is it in phoenix", "phoenix time",
    )
    if any(kw in lower for kw in datetime_keywords):
        return ("get_nexus_datetime", {})

    # ── Priority 15c: Incomplete/unavailable areas ──
    incomplete_keywords = (
        "what is incomplete", "what is unavailable", "what is still mock",
        "what's not live", "what parts of nexus are incomplete",
        "what parts are unavailable", "what is missing",
        "what needs work", "what is blocked", "what is not working",
        "what's incomplete", "what's missing",
        "incomplete components", "simulated incomplete",
        "mock blocked unavailable",
    )
    if any(kw in lower for kw in incomplete_keywords):
        return ("get_incomplete_areas", {})

    # ── Priority 16: Agent details ──
    agent_detail_keywords = {
        "alpha": ("alpha", "what does alpha do", "tell me about alpha", "alpha agent"),
        "hermes_nova": ("nova", "what do you do", "tell me about nova", "your role", "your purpose", "who are you"),
        "nexus_hermes": ("hermes", "what does hermes do", "tell me about hermes", "hermes agent", "nexus hermes"),
    }
    for agent_id, keywords in agent_detail_keywords.items():
        if any(kw in lower for kw in keywords):
            return ("get_agent_details", {"agent_id": agent_id})

    # ── Priority 17: Tool registry ──
    tool_keywords = (
        "what tools", "tool registry", "available tools", "what tools do we have",
        "what tools are", "tool list", "list tools", "what's installed",
        "what software", "what's available",
    )
    if any(kw in lower for kw in tool_keywords):
        return ("get_tool_registry", {})

    # ── Priority 18: Capability registry ──
    capability_keywords = (
        "what capabilities", "capability registry", "what can nexus do",
        "what's live", "what's available", "what capabilities are",
        "capability list", "what systems are live", "what's working",
        "what's still mock", "what's incomplete", "what's unavailable",
        "what parts", "what's not working", "what's missing",
    )
    if any(kw in lower for kw in capability_keywords):
        return ("get_capability_registry", {})

    # ── Priority 19: Process registry / runtime status / comparative state ──
    process_keywords = (
        "what processes", "list processes", "process registry", "what's running",
        "what processes exist", "process list", "what automations",
        "what jobs", "what's enabled", "what's disabled", "which processes",
        "active processes", "running processes", "processes are",
        "actually running", "currently running", "running right now",
        "currently executing", "executing right now", "active right now",
        "what is running", "what is nexus doing", "is anything running",
        "is anything executing", "live processes", "process runtime",
        "enabled but not running", "simulated processes",
        "enabled but not actually", "enabled but not executing",
        "configured but not running", "configured but not executing",
        "configured but inactive", "enabled but simulated",
        "enabled but skipped", "not running even though enabled",
        "active in config but not", "configured processes are not",
        "enabled processes are not", "which enabled processes",
        "how many are enabled", "how many are disabled",
        "how many are blocked", "how many enabled",
        "how many disabled", "how many blocked",
        "simulated or skipped", "is simulated or skipped",
        "execution mode blocked", "runtime state blocked",
        "how many simulated incomplete", "evidence that anything",
        "do you have evidence", "proof that anything",
    )
    if any(kw in lower for kw in process_keywords):
        return ("get_process_registry", {})

    # ── Priority 20: Report lookup ──
    report_keywords = (
        "what reports", "report index", "latest reports", "what reports exist",
        "any reports", "report list", "show reports", "what reports were",
        "recent reports", "what reports do we have",
    )
    if any(kw in lower for kw in report_keywords):
        return ("get_latest_reports", {})

    # ── Priority 21: Recent activity ──
    activity_keywords = (
        "what happened today", "what happened", "what failed", "what's new",
        "recent activity", "what changed", "what ran today", "anything new",
        "what's going on today", "today's activity", "what happened overnight",
        "what should i focus on", "what needs attention",
        "what should we build next", "what's stuck",
    )
    if any(kw in lower for kw in activity_keywords):
        return ("get_recent_activity", {})

    # ── Priority 22: Explicit general search ──
    search_verbs = ("search", "find", "look up", "lookup", "check", "query")
    has_search_verb = any(verb in lower for verb in search_verbs)
    operational_terms = (
        "supabase", "operational", "records", "database", "approved",
        "system", "goclear", "nexus", "process", "webhook",
    )
    has_operational_term = any(term in lower for term in operational_terms)
    if has_search_verb and has_operational_term:
        return ("general_search", {"query": text})

    # ── Priority 23: No tool required ──
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


def _format_planner_context(result: Dict[str, Any]) -> str:
    """Format a planner execution result as structured VERIFIED NEXUS KNOWLEDGE.

    This is the authoritative context for planner-sourced data.
    Includes plan, structured result, coverage, provenance, and truth-guard hints.
    """
    plan = result.get("plan", {})
    data = result.get("data", {})
    prov = result.get("provenance", {})
    coverage = result.get("coverage", {})
    status = result.get("status", "unknown")
    domain = plan.get("domain", "unknown")
    operation = plan.get("operation", "unknown")
    planner_mode = result.get("planner_mode", "unknown")
    planner_model = result.get("planner_model")
    planner_provider = result.get("planner_provider")
    fallback_reason = result.get("fallback_reason")
    validation_status = result.get("validation_status")
    source_requirement = result.get("source_requirement") or plan.get("source_requirement", "any")
    capability_selected = result.get("capability_selected")
    total_count = result.get("total_count")
    returned_count = result.get("returned_count")
    truncated = result.get("truncated", False)

    lines = [
        "[VERIFIED NEXUS KNOWLEDGE]",
        f"domain: {domain}",
        f"operation: {operation}",
        f"status: {status}",
        f"planner_mode: {planner_mode}",
        f"planner_model: {planner_model}",
        f"planner_provider: {planner_provider}",
        f"fallback_reason: {fallback_reason}",
        f"validation_status: {validation_status}",
        f"source_requirement: {source_requirement}",
        f"capability_selected: {capability_selected}",
        f"source: {prov.get('source_type', 'unknown')}",
        f"freshness: {prov.get('freshness', 'unknown')}",
        f"total_count: {total_count}",
        f"returned_count: {returned_count}",
        f"truncated: {str(truncated).lower()}",
        "",
        "Source classification:",
        f"  structural: {str(coverage.get('structural', False)).lower()}",
        f"  operational_state: {str(coverage.get('operational_state', False)).lower()}",
        f"  execution_telemetry: {str(coverage.get('execution_telemetry', False)).lower()}",
        "",
    ]

    # Ambiguity
    ambiguity = plan.get("ambiguity")
    if ambiguity:
        if isinstance(ambiguity, dict):
            lines.append(f"Ambiguity: '{ambiguity.get('field', '?')}' maps to {ambiguity.get('matches', [])}")
        else:
            lines.append(f"Ambiguity: {ambiguity}")
        lines.append("")

    # Conditions applied
    conditions = plan.get("conditions", [])
    if conditions:
        lines.append("Filters applied:")
        for c in conditions:
            lines.append(f"  {c.get('field', '?')} {c.get('operator', '?')} {c.get('value', '?')}")
        lines.append("")

    # Data summary — domain-specific
    if domain == "processes" and isinstance(data, dict):
        total = total_count if total_count is not None else data.get("total", data.get("filtered_count", "?"))
        returned = returned_count if returned_count is not None else data.get("filtered_count", total)
        lines.append(f"total_count: {total}")
        lines.append(f"returned_count: {returned}")
        lines.append(f"truncated: {str(truncated).lower()}")
        lines.append("")

        processes = data.get("processes", [])
        if processes:
            lines.append("Process records (independent dimensions; categories may overlap):")
            for p in processes:
                name = p.get("name", p.get("process_id", "?"))
                config = p.get("configuration_state", "?")
                mode = p.get("execution_mode", "?")
                runtime = p.get("runtime_state", "?")
                lines.append(f"  - {name}:")
                lines.append(f"      process_id: {p.get('process_id', '?')}")
                lines.append(f"      configuration_state: {config}")
                lines.append(f"      execution_mode: {mode}")
                lines.append(f"      runtime_state: {runtime}")
            lines.append("")

        # Dimension counts for count/group_count operations
        if "configuration_counts" in data:
            cc = data["configuration_counts"]
            lines.append(f"configuration_counts: {cc}")
        if "mode_counts" in data:
            mc = data["mode_counts"]
            lines.append(f"mode_counts: {mc}")
        if "runtime_counts" in data:
            rc = data["runtime_counts"]
            lines.append(f"runtime_counts: {rc}")
        if "reconciliation" in data:
            recon = data["reconciliation"]
            lines.append(f"reconciliation: {recon}")
        lines.append("")

        if processes:
            lines.append("Field indexes (exact raw-field membership; categories across fields may overlap):")
            for field in ("configuration_state", "execution_mode", "runtime_state"):
                groups: Dict[str, List[str]] = {}
                for p in processes:
                    value = str(p.get(field, "unknown"))
                    groups.setdefault(value, []).append(p.get("name", p.get("process_id", "?")))
                lines.append(f"  {field}:")
                for value, names in sorted(groups.items()):
                    lines.append(f"    {value}: {', '.join(names)}")
            lines.append("")

    elif domain == "tools" and isinstance(data, dict):
        lines.append(f"total_tools: {data.get('total', '?')}")
        for cat in ("internal_safe", "read_only", "approval_gated", "unavailable"):
            if cat in data:
                lines.append(f"  {cat}: {data[cat]}")
        lines.append("")

    elif domain == "agents" and isinstance(data, dict):
        agents = data.get("agents", [])
        lines.append(f"agent_count: {len(agents)}")
        for a in agents:
            lines.append(f"  - {a.get('name', '?')} ({a.get('agent_id', '?')}): {a.get('role', a.get('purpose', '?'))}")
        lines.append("")

    elif domain == "approvals" and isinstance(data, dict):
        lines.append(f"pending_count: {data.get('pending_count', '?')}")
        lines.append(f"queue_status: {data.get('queue_status', '?')}")
        lines.append("")

    elif domain == "recent_activity" and isinstance(data, dict):
        lines.append(f"has_any_real_execution: {str(data.get('has_any_real_execution', False)).lower()}")
        lines.append(f"telemetry_summary: {data.get('telemetry_summary', 'unknown')}")
        lines.append("")

    elif domain == "nexus_system" and isinstance(data, dict):
        system = data.get("system", {})
        domains = data.get("domains", {})
        compact = data.get("context_profile") == "compact_overview"

        if compact:
            business_summary = data.get("business", {})
            integration_summary = data.get("integrations", {})
            findings = data.get("study_findings", {})
            unknown_records = data.get("unknowns", [])
            top_gaps = data.get("top_gaps", [])
            contradiction_summary = data.get("contradiction_summary", {})
            reconciliation_summary = data.get("current_reconciliation", {})
            current_runtime = {
                "telemetry_available_now": reconciliation_summary.get("verified_execution_telemetry_now_available", False),
                "event_count_24h": reconciliation_summary.get("event_count_24h", 0),
                "coverage": {"coverage_status": reconciliation_summary.get("coverage_status")},
            }
            reconciliation = {
                "study_has_real_execution": system.get("study_has_real_execution", False),
                "current_has_verified_execution_telemetry": reconciliation_summary.get("verified_execution_telemetry_now_available", False),
                "changed_findings": reconciliation_summary.get("changed_findings", []),
            }
            gap_count = findings.get("gap_count", 0)
            contradiction_count = findings.get("contradiction_count", contradiction_summary.get("count", 0))
            unknown_count = findings.get("unknown_count", len(unknown_records))
            severity_counts = findings.get("gap_severity_counts", {})
            gap_domain_counts = findings.get("gap_domain_counts", {})
        else:
            gaps = domains.get("gaps", {}) if isinstance(domains, dict) else {}
            unknowns = domains.get("unknowns", {}) if isinstance(domains, dict) else {}
            processes = domains.get("processes", {}) if isinstance(domains, dict) else {}
            business_summary = domains.get("business_model", {}) if isinstance(domains, dict) else {}
            integration_summary = domains.get("integrations", {}) if isinstance(domains, dict) else {}
            contradictions = data.get("contradictions", [])
            current_runtime = data.get("current_runtime_update", {})
            reconciliation = data.get("study_current_reconciliation", {})
            gap_records = gaps.get("gaps", []) if isinstance(gaps, dict) else []
            severity_counts: Dict[str, int] = {}
            gap_domain_counts: Dict[str, int] = {}
            for gap in gap_records:
                severity_counts[str(gap.get("severity", "unknown"))] = severity_counts.get(str(gap.get("severity", "unknown")), 0) + 1
                gap_domain_counts[str(gap.get("domain", "unknown"))] = gap_domain_counts.get(str(gap.get("domain", "unknown")), 0) + 1
            top_gaps = [
                {
                    "id": gap.get("gap_id"),
                    "domain": gap.get("domain"),
                    "title": gap.get("title"),
                    "severity": gap.get("severity"),
                    "evidence": gap.get("evidence"),
                }
                for gap in gap_records[:10]
            ]
            unknown_records = [
                {
                    "id": u.get("unknown_id"),
                    "domain": u.get("domain"),
                    "title": u.get("title"),
                    "evidence_status": u.get("evidence_status"),
                    "recommended_step": u.get("recommended_step"),
                }
                for u in (unknowns.get("unknowns", []) if isinstance(unknowns, dict) else [])
            ]
            contradiction_summary = {
                "count": len(contradictions),
                "kind_counts": {},
                "examples": contradictions[:5],
            }
            processes = domains.get("processes", {}) if isinstance(domains, dict) else {}
            system = {
                **system,
                "disabled_processes": processes.get("configuration_counts", {}).get("disabled"),
                "configuration_counts": processes.get("configuration_counts", {}),
                "execution_mode_counts": processes.get("mode_counts", {}),
                "study_runtime_state_counts": processes.get("runtime_counts", {}),
                "study_has_real_execution": processes.get("has_real_execution", False),
            }
            gap_count = gaps.get("gap_count", 0)
            contradiction_count = len(contradictions)
            unknown_count = unknowns.get("unknown_count", 0) if isinstance(unknowns, dict) else 0

        lines.append("Study snapshot facts:")
        lines.append(f"  source_ref: {data.get('source_ref', prov.get('source_ref', 'reports/nova_study/nexus_study_snapshot.json'))}")
        lines.append(f"  source_commit: {data.get('source_commit', prov.get('source_commit'))}")
        lines.append(f"  generated_at: {data.get('generated_at', prov.get('generated_at'))}")
        lines.append(f"  system_name: {system.get('name', '?')}")
        lines.append(f"  agent_count: {system.get('agent_count', '?')}")
        lines.append(f"  process_count: {system.get('process_count', '?')}")
        lines.append(f"  enabled_processes: {system.get('enabled_processes', '?')}")
        lines.append(f"  disabled_processes: {system.get('disabled_processes', '?')}")
        lines.append(f"  process_configuration_counts: {system.get('configuration_counts', {})}")
        lines.append(f"  process_execution_mode_counts: {system.get('execution_mode_counts', {})}")
        lines.append(f"  study_runtime_state_counts: {system.get('study_runtime_state_counts', {})}")
        lines.append(f"  study_has_real_execution: {str(system.get('study_has_real_execution', False)).lower()}")
        lines.append(f"  offer_count: {business_summary.get('offer_count', business_summary.get('offers_count', '?'))}")
        lines.append(f"  operational_offer_count: {business_summary.get('operational_offers', len(business_summary.get('operational_revenue_paths', [])))}")
        lines.append(f"  planned_offer_count: {business_summary.get('planned_offers', len(business_summary.get('planned_revenue_paths', [])))}")
        lines.append(f"  integration_count: {integration_summary.get('total', integration_summary.get('connector_count', '?'))}")
        lines.append(f"  live_integration_count: {integration_summary.get('live', integration_summary.get('live_enabled_count', '?'))}")
        lines.append(f"  integration_status_counts: {integration_summary.get('status_counts', {})}")
        lines.append(f"  gap_count: {gap_count}")
        lines.append(f"  gap_severity_counts: {severity_counts}")
        lines.append(f"  gap_domain_counts: {gap_domain_counts}")
        lines.append(f"  contradiction_count: {contradiction_count}")
        lines.append(f"  unknown_count: {unknown_count}")
        lines.append("")

        if top_gaps:
            lines.append("Study gap records (bounded top records; more detail available on request):")
            for gap in top_gaps:
                lines.append(f"  - {gap.get('id', '?')}: {gap.get('title', '?')}")
                lines.append(f"      domain: {gap.get('domain', '?')}")
                lines.append(f"      severity: {gap.get('severity', '?')}")
                lines.append(f"      evidence: {gap.get('evidence', '?')}")
            lines.append("")

        examples = contradiction_summary.get("examples", [])
        if examples:
            lines.append("Study contradiction summary (bounded examples; full detail available on request):")
            lines.append(f"  count: {contradiction_summary.get('count', contradiction_count)}")
            lines.append(f"  kind_counts: {contradiction_summary.get('kind_counts', {})}")
            for contradiction in examples:
                lines.append(
                    "  - "
                    f"kind={contradiction.get('kind', '?')} "
                    f"entity={contradiction.get('entity', '?')} "
                    f"registry={contradiction.get('registry', '?')} "
                    f"runtime={contradiction.get('runtime', '?')} "
                    f"interpretation={contradiction.get('interpretation', '?')}"
                )
            lines.append("")

        if unknown_records:
            lines.append("Study unknowns:")
            for unknown in unknown_records:
                lines.append(f"  - {unknown.get('id', unknown.get('unknown_id', '?'))}: {unknown.get('title', '?')}")
                lines.append(f"      domain: {unknown.get('domain', '?')}")
                lines.append(f"      evidence_status: {unknown.get('evidence_status', '?')}")
                if unknown.get("recommended_step"):
                    lines.append(f"      recommended_step: {unknown.get('recommended_step', '?')}")
            lines.append("")

        if current_runtime:
            lines.append("Current runtime telemetry update (separate from historical study snapshot):")
            lines.append(f"  telemetry_available_now: {str(current_runtime.get('telemetry_available_now', False)).lower()}")
            lines.append(f"  event_count_24h: {current_runtime.get('event_count_24h', 0)}")
            lines.append(f"  current_summary: {current_runtime.get('summary', {})}")
            lines.append(f"  current_coverage: {current_runtime.get('coverage', {})}")
            lines.append("")

        if reconciliation:
            lines.append("Study/current reconciliation:")
            lines.append(f"  study_has_real_execution: {str(reconciliation.get('study_has_real_execution', False)).lower()}")
            lines.append(
                "  current_has_verified_execution_telemetry: "
                f"{str(reconciliation.get('current_has_verified_execution_telemetry', False)).lower()}"
            )
            changed = reconciliation.get("changed_findings", [])
            if changed:
                lines.append("  changed_findings:")
                for item in changed:
                    lines.append(f"    - {item.get('id', '?')}: {item.get('title', '?')}")
                    lines.append(f"        study_state: {item.get('study_state', '?')}")
                    lines.append(f"        current_state: {item.get('current_state', '?')}")
                    lines.append(f"        status: {item.get('status', '?')}")
            lines.append(f"  note: {reconciliation.get('note', '')}")
            lines.append("")

    elif domain == "runtime_execution" and isinstance(data, dict):
        summary = data.get("summary", {})
        telemetry_coverage = data.get("coverage", {})
        health = data.get("telemetry_health", {})
        lines.append(f"window: {plan.get('window', 'all')}")
        lines.append(f"coverage_status: {telemetry_coverage.get('coverage_status', 'unknown')}")
        lines.append(f"coverage_window_start: {telemetry_coverage.get('window_start')}")
        lines.append(f"coverage_window_end: {telemetry_coverage.get('window_end')}")
        lines.append(f"telemetry_source_count: {telemetry_coverage.get('source_count', 0)}")
        lines.append(f"event_count: {summary.get('event_count', 0)}")
        lines.append(f"run_count: {summary.get('run_count', 0)}")
        lines.append(f"active_count: {summary.get('active_count', 0)}")
        lines.append(f"completed_count: {summary.get('completed_count', 0)}")
        lines.append(f"failed_count: {summary.get('failed_count', 0)}")
        lines.append(f"skipped_count: {summary.get('skipped_count', 0)}")
        lines.append(f"blocked_count: {summary.get('blocked_count', 0)}")
        lines.append(f"stale_count: {summary.get('stale_count', 0)}")
        lines.append(f"telemetry_health_status: {health.get('status', 'unknown')}")
        lines.append(f"last_event_at: {health.get('last_event_at')}")
        lines.append("")

        processes = data.get("processes", [])
        if processes:
            lines.append("Process execution state records:")
            for p in processes:
                lines.append(f"  - {p.get('process_name', p.get('process_id', '?'))}:")
                lines.append(f"      process_id: {p.get('process_id', '?')}")
                lines.append(f"      current_state: {p.get('current_state', '?')}")
                lines.append(f"      last_terminal_status: {p.get('last_terminal_status', '?')}")
                lines.append(f"      last_run_id: {p.get('last_run_id', '?')}")
                lines.append(f"      last_started_at: {p.get('last_started_at')}")
                lines.append(f"      last_completed_at: {p.get('last_completed_at')}")
                lines.append(f"      last_duration_ms: {p.get('last_duration_ms')}")
                lines.append(f"      last_worker_id: {p.get('last_worker_id', '?')}")
                lines.append(f"      stale: {str(p.get('stale', False)).lower()}")
            lines.append("")

        runs = data.get("runs", [])
        if runs:
            lines.append(f"verified_run_list_count: {len(runs)}")
            lines.append("Verified execution runs:")
            for r in runs:
                lines.append(f"  - run_id: {r.get('run_id', '?')}")
                lines.append(f"      process_id: {r.get('process_id', '?')}")
                lines.append(f"      process_name: {r.get('process_name', '?')}")
                lines.append(f"      worker_id: {r.get('worker_id', '?')}")
                lines.append(f"      execution_type: {r.get('execution_type', '?')}")
                lines.append(f"      status: {r.get('status', '?')}")
                lines.append(f"      current_state: {r.get('current_state', '?')}")
                lines.append(f"      last_terminal_status: {r.get('last_terminal_status', '?')}")
                lines.append(f"      started_at: {r.get('started_at')}")
                lines.append(f"      completed_at: {r.get('completed_at')}")
                lines.append(f"      duration_ms: {r.get('duration_ms')}")
                lines.append(f"      source_type: {r.get('source_type', '?')}")
            lines.append("")

        missing_enabled = data.get("enabled_processes_without_verified_run", [])
        if missing_enabled:
            lines.append("Enabled processes without a verified telemetry run in this window:")
            for p in missing_enabled:
                lines.append(f"  - {p.get('name', p.get('process_id', '?'))}:")
                lines.append(f"      process_id: {p.get('process_id', '?')}")
                lines.append(f"      configuration_state: {p.get('configuration_state', '?')}")
                lines.append(f"      execution_mode: {p.get('execution_mode', '?')}")
                lines.append(f"      runtime_state: {p.get('runtime_state', '?')}")
                lines.append("      note: missing telemetry is not proof the process did not run unless coverage is complete")
            lines.append("")

        lines.append("Telemetry rules:")
        lines.append("  - running right now requires a fresh started run with no terminal event.")
        lines.append("  - completed requires a completed terminal event.")
        lines.append("  - failed requires a failed terminal event.")
        lines.append("  - partial/unavailable coverage means no matching run is not proof nothing ran.")
        lines.append("")

    elif domain == "incomplete_areas" and isinstance(data, dict):
        lines.append(f"incomplete_count: {data.get('unique_incomplete_count', data.get('count', '?'))}")
        areas = data.get("areas", [])
        if areas:
            for a in areas[:10]:
                lines.append(f"  - {a.get('name', a.get('area', '?'))}: {a.get('status', '?')}")
        lines.append("")

    else:
        # Generic data dump for other domains
        if data:
            lines.append(f"data: {json.dumps(data, default=str)[:500]}")
            lines.append("")

    lines.append("[END VERIFIED NEXUS KNOWLEDGE]")
    return "\n".join(lines)


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

    # ── Nexus Knowledge Capability Formatters ──

    if query_type == "get_nexus_overview":
        lines = [
            "[VERIFIED NEXUS KNOWLEDGE]",
            "capability: get_nexus_overview",
            f"status: {status}",
            "source: nexus_knowledge_registry",
            "freshness: current_commit",
            "facts:",
            f"- system_name: {data.get('system_name', 'unknown')}",
            f"- version: {data.get('version', 'unknown')}",
            f"- purpose: {data.get('purpose', 'unknown')}",
            f"- agent_count: {data.get('agent_count', 0)}",
            f"- specialist_count: {data.get('specialist_count', 0)}",
            f"- process_count: {data.get('process_count', 0)}",
            f"- enabled_processes: {data.get('enabled_processes', 0)}",
            f"- research_lane_count: {data.get('research_lane_count', 0)}",
        ]
        agents = data.get("agents", [])
        if agents:
            lines.append(f"- agents: {', '.join(agents)}")
        components = data.get("major_components", [])
        if components:
            lines.append("- major_components:")
            for c in components:
                lines.append(f"  - {c}")
        incomplete = data.get("known_incomplete_areas", [])
        if incomplete:
            lines.append("- known_incomplete_areas:")
            for area in incomplete[:5]:
                lines.append(f"  - {area}")
        lines.append("[END VERIFIED NEXUS KNOWLEDGE]")
        return "\n".join(lines)

    if query_type == "get_agent_registry":
        agents = data.get("agents", [])
        lines = [
            "[VERIFIED NEXUS KNOWLEDGE]",
            "capability: get_agent_registry",
            f"status: {status}",
            "source: nexus_knowledge_registry",
            "freshness: current_commit",
            "facts:",
            f"- total: {data.get('total', 0)}",
            f"- specialist_profiles: {data.get('specialist_profiles', 0)}",
        ]
        if agents:
            lines.append("- agents:")
            for a in agents:
                lines.append(
                    f"  - {a.get('agent_id', 'unknown')}: "
                    f"{a.get('name', 'unknown')} ({a.get('role', 'unknown')}) "
                    f"[reads: {a.get('permissions', {}).get('read_count', 0)}, "
                    f"writes: {a.get('permissions', {}).get('write_count', 0)}]"
                )
        lines.append("[END VERIFIED NEXUS KNOWLEDGE]")
        return "\n".join(lines)

    if query_type == "get_agent_details":
        found = data.get("found", False)
        if not found:
            return (
                "[VERIFIED NEXUS KNOWLEDGE]\n"
                f"capability: get_agent_details\n"
                f"status: not_found\n"
                f"source: nexus_knowledge_registry\n"
                f"freshness: current_commit\n"
                f"facts:\n"
                f"- found: false\n"
                f"- available_agents: {', '.join(data.get('available_agents', []))}\n"
                f"[END VERIFIED NEXUS KNOWLEDGE]"
            )
        lines = [
            "[VERIFIED NEXUS KNOWLEDGE]",
            "capability: get_agent_details",
            f"status: {status}",
            "source: nexus_knowledge_registry",
            "freshness: current_commit",
            "facts:",
            f"- agent_id: {data.get('agent_id', 'unknown')}",
            f"- name: {data.get('name', 'unknown')}",
            f"- role: {data.get('role', 'unknown')}",
            f"- model: {data.get('model', 'unknown')}",
            f"- provider: {data.get('provider', 'unknown')}",
            f"- runtime_status: {data.get('runtime_status', 'unknown')}",
        ]
        responsibilities = data.get("responsibilities", [])
        if responsibilities:
            lines.append("- responsibilities:")
            for r in responsibilities:
                lines.append(f"  - {r}")
        perms = data.get("permissions", {})
        reads = perms.get("reads", [])
        writes = perms.get("writes", [])
        if reads:
            lines.append(f"- approved_reads: {', '.join(reads)}")
        if writes:
            lines.append(f"- approved_writes: {', '.join(writes)}")
        else:
            lines.append("- approved_writes: NONE")
        isolation = data.get("isolation", {})
        if isolation:
            lines.append("- isolation:")
            for k, v in isolation.items():
                lines.append(f"  - {k}: {v}")
        lines.append("[END VERIFIED NEXUS KNOWLEDGE]")
        return "\n".join(lines)

    if query_type == "get_tool_registry":
        categories = data.get("categories", {})
        lines = [
            "[VERIFIED NEXUS KNOWLEDGE]",
            "capability: get_tool_registry",
            f"status: {status}",
            f"source: {data.get('source_type', 'configuration_registry')}",
            f"freshness: {data.get('freshness', 'current_commit')}",
            "facts:",
            f"- total: {data.get('total', 0)}",
            f"- usable_now: {data.get('usable_now', 0)} (internal_safe + read_only)",
            f"- internal_safe: {data.get('internal_safe_count', 0)}",
            f"- read_only: {data.get('read_only_count', 0)}",
            f"- approval_gated: {data.get('approval_gated_count', 0)}",
            f"- unavailable: {data.get('unavailable_count', 0)}",
            f"- default_policy: {data.get('default_policy', 'unknown')}",
            f"- reconciliation: {str(data.get('reconciliation', False)).lower()}",
        ]
        for cat, info in categories.items():
            tools = info.get("tools", [])
            lines.append(f"- {cat}: {', '.join(tools)}")
        lines.append("[END VERIFIED NEXUS KNOWLEDGE]")
        return "\n".join(lines)

    if query_type == "get_capability_registry":
        lines = [
            "[VERIFIED NEXUS KNOWLEDGE]",
            "capability: get_capability_registry",
            f"status: {status}",
            "source: nexus_knowledge_registry",
            "freshness: current_commit",
            "facts:",
            f"- total_shared_handlers: {data.get('total_shared_handlers', 0)}",
            f"- total_nova_knowledge: {data.get('total_nova_knowledge', 0)}",
            f"- nova_writes: {data.get('nova_writes', 0)}",
            f"- hermes_writes: {data.get('hermes_writes', 0)}",
        ]
        shared = data.get("shared_handlers", [])
        if shared:
            lines.append(f"- shared_handlers: {', '.join(shared)}")
        nova_k = data.get("nova_knowledge_capabilities", [])
        if nova_k:
            lines.append(f"- nova_knowledge: {', '.join(nova_k)}")
        lines.append("[END VERIFIED NEXUS KNOWLEDGE]")
        return "\n".join(lines)

    if query_type == "get_process_registry":
        processes = data.get("processes", [])
        config = data.get("configuration_counts", {})
        modes = data.get("mode_counts", {})
        runtime = data.get("runtime_counts", {})
        recon = data.get("reconciliation", {})
        has_real = data.get("has_real_execution", False)
        all_sim = data.get("all_simulated_or_skipped", False)
        lines = [
            "[VERIFIED NEXUS KNOWLEDGE]",
            "capability: get_process_registry",
            f"status: {status}",
            f"source: {data.get('source_type', 'process_registry')}",
            f"freshness: {data.get('freshness', 'current_registry')}",
            "facts:",
            f"- total: {data.get('total', 0)}",
            "",
            "SOURCE CLASSIFICATION:",
            "  structural/configuration: total process count, enabled/disabled counts, execution mode definitions",
            "  operational state: simulated/skipped/blocked runtime markers (registry-backed, not verified execution)",
            "  verified execution telemetry: currently unavailable — no real execution telemetry observed",
            "",
            "Configuration state (is Nexus configured to allow this to run?):",
        ]
        for state, count in sorted(config.items()):
            lines.append(f"  - {state}: {count}")
        lines.append(f"  - reconciliation: {str(recon.get('configuration', False)).lower()}")
        lines.append("")
        lines.append("Execution mode (what mode is it designed to execute in?):")
        for mode, count in sorted(modes.items()):
            lines.append(f"  - {mode}: {count}")
        lines.append(f"  - reconciliation: {str(recon.get('execution_mode', False)).lower()}")
        lines.append("")
        lines.append("Runtime state (what runtime evidence exists right now?):")
        for state, count in sorted(runtime.items()):
            lines.append(f"  - {state}: {count}")
        lines.append(f"  - reconciliation: {str(recon.get('runtime_state', False)).lower()}")
        lines.append("")
        lines.append("Execution telemetry:")
        lines.append(f"  - coverage: {'observed' if has_real else 'unavailable'}")
        lines.append(f"  - has_real_execution: {str(has_real).lower()}")
        lines.append(f"  - all_simulated_or_skipped: {str(all_sim).lower()}")
        if processes:
            lines.append("")
            lines.append("Processes (each showing three independent dimensions):")
            for p in processes:
                lines.append(
                    f"  - {p.get('process_id', 'unknown')}: "
                    f"{p.get('name', 'unknown')} "
                    f"[config: {p.get('configuration_state', 'unknown')}, "
                    f"mode: {p.get('execution_mode', 'unknown')}, "
                    f"runtime: {p.get('runtime_state', 'unknown')}]"
                )
        lines.append("[END VERIFIED NEXUS KNOWLEDGE]")
        return "\n".join(lines)

    if query_type == "get_report_index":
        categories = data.get("categories", [])
        lines = [
            "[VERIFIED NEXUS KNOWLEDGE]",
            "capability: get_report_index",
            f"status: {status}",
            "source: report_index",
            "freshness: live",
            "facts:",
            f"- category_count: {data.get('category_count', 0)}",
            f"- root_report_count: {data.get('root_report_count', 0)}",
        ]
        if categories:
            lines.append("- categories:")
            for c in categories[:10]:
                lines.append(
                    f"  - {c.get('category', 'unknown')}: "
                    f"{c.get('report_count', 0)} reports"
                )
        lines.append("[END VERIFIED NEXUS KNOWLEDGE]")
        return "\n".join(lines)

    if query_type == "get_latest_reports":
        reports = data.get("reports", [])
        lines = [
            "[VERIFIED NEXUS KNOWLEDGE]",
            "capability: get_latest_reports",
            f"status: {status}",
            "source: report_index",
            "freshness: live",
            "facts:",
            f"- total_latest: {data.get('total_latest', 0)}",
        ]
        if reports:
            lines.append("- latest_reports:")
            for r in reports[:10]:
                lines.append(
                    f"  - {r.get('name', 'unknown')} "
                    f"(modified: {r.get('modified', 'unknown')})"
                )
        lines.append("[END VERIFIED NEXUS KNOWLEDGE]")
        return "\n".join(lines)

    if query_type == "get_recent_activity":
        components = data.get("components", {})
        lines = [
            "[VERIFIED NEXUS KNOWLEDGE]",
            "capability: get_recent_activity",
            f"status: {status}",
            f"source: {data.get('source_type', 'composite')}",
            f"freshness: {data.get('freshness', 'live')}",
            "facts:",
            f"- telemetry_summary: {data.get('telemetry_summary', 'unknown')}",
            f"- has_any_real_execution: {str(data.get('has_any_real_execution', False)).lower()}",
        ]
        # Processes
        proc = components.get("processes", {})
        if proc.get("status") == "success":
            configured = proc.get("configured", {})
            verified = proc.get("verified_activity", {})
            simulated = proc.get("simulated_state", {})
            lines.append(
                f"- processes: configured={configured.get('total', 0)} total, "
                f"{configured.get('enabled', 0)} enabled; "
                f"verified: {verified.get('running', 0)} running, "
                f"{verified.get('completed', 0)} completed, "
                f"{verified.get('failed', 0)} failed; "
                f"simulated: {simulated.get('simulated_count', 0)}"
            )
            lines.append(f"  - telemetry_coverage: {proc.get('telemetry_coverage', 'unknown')}")
        else:
            lines.append(f"- processes: {proc.get('status', 'unknown')}")
        # Approvals
        appr = components.get("approvals", {})
        if appr.get("status") == "success":
            configured = appr.get("configured", {})
            verified = appr.get("verified_activity", {})
            lines.append(
                f"- pending_approvals: {configured.get('pending', 0)} "
                f"(external_actions_executed: {verified.get('external_actions_executed', 0)})"
            )
        else:
            lines.append(f"- approvals: {appr.get('status', 'unknown')}")
        # Research
        res = components.get("research", {})
        if res.get("status") == "success":
            configured = res.get("configured", {})
            verified = res.get("verified_activity", {})
            lines.append(
                f"- research_lanes: {configured.get('approved_lanes', 0)} approved "
                f"of {configured.get('total_lanes', 0)} total; "
                f"recent_runs: {verified.get('recent_runs', 0)}"
            )
        else:
            lines.append(f"- research: {res.get('status', 'unknown')}")
        # Alpha
        alpha = components.get("alpha", {})
        if alpha.get("status") == "success":
            configured = alpha.get("configured", {})
            verified = alpha.get("verified_activity", {})
            lines.append(
                f"- alpha_state: {configured.get('state', 'unknown')}; "
                f"last_incoming: {verified.get('last_incoming', 'unknown')}"
            )
        else:
            lines.append(f"- alpha: {alpha.get('status', 'unknown')}")
        lines.append("[END VERIFIED NEXUS KNOWLEDGE]")
        return "\n".join(lines)

    if query_type == "get_nexus_datetime":
        lines = [
            "[VERIFIED NEXUS KNOWLEDGE]",
            "capability: get_nexus_datetime",
            f"status: {status}",
            "source: deterministic_utility",
            "freshness: live",
            "facts:",
            f"- phoenix_date: {data.get('phoenix_date', 'unknown')}",
            f"- phoenix_time: {data.get('phoenix_time', 'unknown')}",
            f"- phoenix_day_of_week: {data.get('phoenix_day_of_week', 'unknown')}",
            f"- utc_datetime: {data.get('utc_datetime', 'unknown')}",
        ]
        if data.get("timezone_note"):
            lines.append(f"- timezone_note: {data['timezone_note']}")
        lines.append("[END VERIFIED NEXUS KNOWLEDGE]")
        return "\n".join(lines)

    if query_type == "get_incomplete_areas":
        categories = data.get("categories", {})
        counts = data.get("category_counts", {})
        lines = [
            "[VERIFIED NEXUS KNOWLEDGE]",
            "capability: get_incomplete_areas",
            f"status: {status}",
            f"source: {data.get('source_type', 'registry_derived')}",
            f"freshness: {data.get('freshness', 'current_commit')}",
            "facts:",
            f"- unique_incomplete_count: {data.get('unique_incomplete_count', 0)}",
            "",
            "Categories (components may appear in multiple categories):",
        ]
        for cat, cat_data in categories.items():
            count = cat_data.get("count", 0)
            items = cat_data.get("items", [])
            if count > 0:
                lines.append(f"  {cat} ({count} items, showing up to 5):")
                for item in items[:5]:
                    lines.append(f"    - {item}")
                if len(items) > 5:
                    lines.append(f"    ... and {len(items) - 5} more")
        lines.append("")
        lines.append("NOTE: unique_incomplete_count counts each component once.")
        lines.append("Category counts may overlap — do NOT sum them to get unique count.")
        lines.append("[END VERIFIED NEXUS KNOWLEDGE]")
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
    source_requirement = provenance.get("source_requirement")
    if source_requirement:
        lines.append(f"source_requirement: {source_requirement}")
    coverage = provenance.get("coverage", {})
    if coverage:
        lines.append("coverage:")
        lines.append(f"  structural: {str(coverage.get('structural', False)).lower()}")
        lines.append(f"  operational_state: {str(coverage.get('operational_state', False)).lower()}")
        lines.append(f"  execution_telemetry: {str(coverage.get('execution_telemetry', False)).lower()}")
    domain = provenance.get("domain")
    if domain:
        lines.append(f"domain: {domain}")
    operation = provenance.get("operation")
    if operation:
        lines.append(f"operation: {operation}")
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
        "If source_requirement is present, use it to answer whether the prior fact "
        "was configuration, operational state, or execution telemetry. "
        "For natural responses, use the Phoenix-local time."
    )
    return "\n".join(lines)


# ─── Model Gateway ─────────────────────────────────────────

GENERATION_TIMEOUT_SECONDS = float(os.getenv("HERMES_NOVA_GENERATION_TIMEOUT_SECONDS", "60"))


async def _call_model(
    messages: List[Dict[str, str]],
    chat_id: int,
    purpose: str = "final_generation",
) -> Dict[str, Any]:
    """Call the configured OpenRouter model via LlmGatewayAdapter."""
    import asyncio
    from nexus_agent_platform.workflows.litellm_adapter import LlmGatewayAdapter

    model = os.getenv("HERMES_NOVA_MODEL", DEFAULT_MODEL)
    adapter = LlmGatewayAdapter(agent_id=AGENT_ID)

    with stage_execution(
        stage="model_call",
        source="scripts/nexus_agent_platform/agents/nova.py:_call_model",
        metadata={
            "purpose": purpose,
            "provider": "litellm" if adapter.is_enabled else "openrouter",
            "model": model,
            "timeout_seconds": GENERATION_TIMEOUT_SECONDS,
        },
    ):
        result = await asyncio.wait_for(
            adapter.completion(
                model=model,
                messages=messages,
                temperature=DEFAULT_TEMPERATURE,
                max_tokens=DEFAULT_MAX_TOKENS,
                timeout=GENERATION_TIMEOUT_SECONDS,
                request_timeout=GENERATION_TIMEOUT_SECONDS,
            ),
            timeout=GENERATION_TIMEOUT_SECONDS + 5,
        )
    return result


# ─── Planner Model Gateway ──────────────────────────────────

PLANNER_MODEL = os.getenv("HERMES_NOVA_PLANNER_MODEL", "openai/gpt-4o-mini")
PLANNER_TEMPERATURE = 0.3
PLANNER_MAX_TOKENS = 512
PLANNER_TIMEOUT_SECONDS = float(os.getenv("HERMES_NOVA_PLANNER_TIMEOUT_SECONDS", "30"))


def _planner_model_call(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """Synchronous planner model call — wraps LlmGatewayAdapter for plan_query()."""
    import asyncio
    from nexus_agent_platform.workflows.litellm_adapter import LlmGatewayAdapter

    async def _async_planner_call(msgs: List[Dict[str, str]]) -> Dict[str, Any]:
        adapter = LlmGatewayAdapter(agent_id=f"{AGENT_ID}_planner")
        with stage_execution(
            stage="model_call",
            source="scripts/nexus_agent_platform/agents/nova.py:_planner_model_call",
            metadata={
                "purpose": "planner",
                "provider": "litellm" if adapter.is_enabled else "openrouter",
                "model": PLANNER_MODEL,
                "timeout_seconds": PLANNER_TIMEOUT_SECONDS,
            },
        ):
            result = await asyncio.wait_for(
                adapter.completion(
                    model=PLANNER_MODEL,
                    messages=msgs,
                    temperature=PLANNER_TEMPERATURE,
                    max_tokens=PLANNER_MAX_TOKENS,
                    timeout=PLANNER_TIMEOUT_SECONDS,
                    request_timeout=PLANNER_TIMEOUT_SECONDS,
                ),
                timeout=PLANNER_TIMEOUT_SECONDS + 5,
            )
        result["provider"] = "litellm" if adapter.is_enabled else "openrouter"
        return result

    return asyncio.run(_async_planner_call(messages))


def _bounded_text(value: Any, limit: int = 240) -> str:
    """Compact user/assistant history for planner follow-up context."""
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _planner_result_counts(data: Any) -> Tuple[Optional[int], Optional[int], bool]:
    """Return total/returned/truncated metadata for planner execution results."""
    if not isinstance(data, dict):
        return None, None, False

    total = data.get("total")
    if total is None:
        total = data.get("total_latest")
    if total is None:
        total = data.get("unique_incomplete_count")
    if total is None and "pending_count" in data:
        total = data.get("pending_count")
    if total is None and "count" in data:
        total = data.get("count")
    if total is None and "total_count" in data:
        total = data.get("total_count")

    returned = data.get("returned_count")
    if returned is None:
        returned = data.get("filtered_count")
    if returned is None and isinstance(data.get("processes"), list):
        returned = len(data["processes"])
    if returned is None and isinstance(data.get("reports"), list):
        returned = len(data["reports"])
    if returned is None and isinstance(data.get("agents"), list):
        returned = len(data["agents"])
    if returned is None and "returned_count" in data:
        returned = data.get("returned_count")
    if returned is None:
        returned = total

    truncated = (
        isinstance(total, int)
        and isinstance(returned, int)
        and returned < total
    )
    return total, returned, truncated


def _build_planner_context(state: AgentState) -> Optional[str]:
    """Build bounded conversation context for the semantic planner.

    Extracts previous domain, operation, and referenced entities from
    the current state's capability gate history. Does NOT send raw
    conversation history — only structured summaries.
    """
    parts = []

    chat_id = state.metadata.get("chat_id", 0)

    if chat_id:
        history = load_memory(chat_id)
        bounded_history = history[-6:]
        if bounded_history:
            parts.append("Recent bounded conversation:")
            for msg in bounded_history:
                role = msg.get("role", "unknown")
                content = _bounded_text(msg.get("content", ""), 220)
                if content:
                    parts.append(f"- {role}: {content}")

    # Previous planner result from this state, used by direct node tests and retries.
    prev_gate = state.metadata.get("capability_gate")
    if prev_gate and prev_gate.get("decision") == "planner_executed":
        prev_plan = prev_gate.get("plan", {})
        if prev_plan:
            domain = prev_plan.get("domain", "unknown")
            operation = prev_plan.get("operation", "unknown")
            parts.append(f"Previous query domain: {domain}")
            parts.append(f"Previous query operation: {operation}")

            # Extract conditions as entity references
            conditions = prev_plan.get("conditions", [])
            for cond in conditions:
                field = cond.get("field", "")
                value = cond.get("value")
                if field and value:
                    parts.append(f"Previous filter: {field} = {value}")

    # Previous capability result summary
    prev_result = state.metadata.get("capability_result")
    if prev_result and prev_result.get("tool") == "nexus_query_planner":
        data = prev_result.get("data", {})
        if isinstance(data, dict):
            # Process count summary
            if "total" in data:
                parts.append(f"Previous result total: {data['total']}")
            if "processes" in data and isinstance(data["processes"], list):
                names = [p.get("name", p.get("process_id", "?")) for p in data["processes"][:5]]
                if names:
                    parts.append(f"Previous result included: {', '.join(names)}")
            # Tool counts
            if "total" in data and "internal_safe" in data:
                parts.append(f"Previous tool breakdown: {data}")

    if not parts:
        return None
    return "\n".join(parts)


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

    # ── Tool count contradiction ──
    if query_type == "get_tool_registry" and status == "success":
        verified_total = data.get("total", 0)
        if verified_total > 0:
            tool_count_claims = re.findall(r'(\d+)\s*(?:tools?|total)', response_lower)
            for claim in tool_count_claims:
                claimed_num = int(claim)
                if claimed_num != verified_total and claimed_num > 10:
                    return "tool_count_contradiction"

    # ── Process count contradiction (dimension mixing) ──
    if query_type == "get_process_registry" and status == "success":
        total = data.get("total", 0)
        config = data.get("configuration_counts", {})
        modes = data.get("mode_counts", {})
        runtime = data.get("runtime_counts", {})
        recon = data.get("reconciliation", {})

        # Reject if any dimension doesn't reconcile
        if not recon.get("all_reconciled", False):
            return "process_count_contradiction"

        # Reject if claimed numbers don't match any single dimension
        if total > 0:
            # Look for patterns like "X enabled, Y disabled, Z blocked"
            # that mix dimensions into one count
            enabled_claims = re.findall(r'(\d+)\s*enabled', response_lower)
            disabled_claims = re.findall(r'(\d+)\s*disabled', response_lower)
            for claim in enabled_claims:
                claimed = int(claim)
                verified_enabled = config.get("enabled", 0)
                if claimed != verified_enabled:
                    return "process_count_contradiction"
            for claim in disabled_claims:
                claimed = int(claim)
                verified_disabled = config.get("disabled", 0)
                if claimed != verified_disabled:
                    return "process_count_contradiction"

    # ── Simulated count exceeds total ──
    if query_type == "get_process_registry" and status == "success":
        total = data.get("total", 0)
        runtime = data.get("runtime_counts", {})
        simulated = runtime.get("simulated", 0)
        if total > 0 and simulated > total:
            return "process_count_contradiction"

    # ── Simulated → live contradiction ──
    if query_type == "get_process_registry" and status == "success":
        all_sim = data.get("all_simulated_or_skipped", False)
        if all_sim:
            live_claims = [
                "running live", "currently executing", "operational in real time",
                "actively running", "not simulated", "successfully ran today",
                "running in a live state", "processes are live",
                "not all simulated", "operational", "processes operating in a live state",
            ]
            for claim in live_claims:
                if claim in response_lower:
                    return "simulated_to_live_contradiction"

    # ── Enabled ≠ running contradiction ──
    if query_type == "get_process_registry" and status == "success":
        has_real = data.get("has_real_execution", False)
        if not has_real:
            running_claims = [
                "are running", "is running", "currently running",
                "running right now", "actively running",
            ]
            for claim in running_claims:
                if claim in response_lower:
                    return "enabled_not_running_contradiction"

    # ── Recent activity: no telemetry → no success claims ──
    if query_type == "get_recent_activity" and status == "success":
        telemetry = data.get("telemetry_summary", "")
        if "No real execution telemetry" in telemetry:
            success_claims = [
                "everything ran smoothly", "all processes succeeded",
                "no failures today", "everything is running smoothly",
                "functioning without issues", "running smoothly",
                "all processes are functioning",
            ]
            for claim in success_claims:
                if claim in response_lower:
                    return "telemetry_contradiction"

    # ── Failure inference: zero failures ≠ successful execution ──
    if query_type == "get_recent_activity" and status == "success":
        proc = data.get("components", {}).get("processes", {})
        telemetry_cov = proc.get("telemetry_coverage", "")
        if telemetry_cov == "no_real_execution_telemetry":
            success_claims = [
                "everything ran successfully", "all processes completed successfully",
                "no failures means everything worked", "zero failures means success",
                "all processes are healthy", "everything is working correctly",
            ]
            for claim in success_claims:
                if claim in response_lower:
                    return "failure_inference_contradiction"

    # ── Approval inference: zero pending ≠ everything reviewed ──
    if query_type == "get_pending_approvals" and status == "success":
        count = data.get("count", 0)
        if count == 0:
            inference_claims = [
                "everything necessary was reviewed", "all actions were approved",
                "there is nothing requiring attention", "every required approval was completed",
                "all approvals are done", "nothing needs review",
            ]
            for claim in inference_claims:
                if claim in response_lower:
                    return "approval_inference_contradiction"

    # ── Incomplete areas: category overlap not summed ──
    if query_type == "get_incomplete_areas" and status == "success":
        unique = data.get("unique_incomplete_count", 0)
        cats = data.get("category_counts", {})
        # Reject if any single category exceeds unique count
        for cat, count in cats.items():
            if count > unique and unique > 0:
                return "incomplete_count_contradiction"
        # Reject blind sum of categories
        blind_sum = sum(cats.values())
        if blind_sum > unique and unique > 0 and len(cats) > 1:
            sum_claims = re.findall(r'(\d+)\s*(?:total|incomplete|items)', response_lower)
            for claim in sum_claims:
                claimed = int(claim)
                if claimed == blind_sum and blind_sum != unique:
                    return "incomplete_count_contradiction"

    # ── Mixed provenance contradiction ──
    if query_type == "get_nexus_overview" and status == "success":
        source_mixed_claims = [
            "entirely from live runtime", "all from live runtime",
            "entirely live", "all from runtime",
        ]
        for claim in source_mixed_claims:
            if claim in response_lower:
                return "mixed_provenance_contradiction"

    # ── Dimension mislabeling: runtime blocked ≠ execution-mode BLOCKED ──
    if query_type == "get_process_registry" and status == "success":
        runtime = data.get("runtime_counts", {})
        modes = data.get("mode_counts", {})
        runtime_blocked = runtime.get("blocked", 0)
        mode_blocked = modes.get("BLOCKED", 0)
        if runtime_blocked > 0 and mode_blocked == 0:
            # There are runtime-blocked processes but NO execution-mode BLOCKED processes
            # Reject if Nova labels runtime blocked as execution-mode blocked
            mode_blocked_claims = re.findall(
                r'(?:execution\s*mode|mode)\s*(?:BLOCKED|blocked)\s*[:=]?\s*(\d+)',
                response_lower
            )
            for claim in mode_blocked_claims:
                claimed = int(claim)
                if claimed == runtime_blocked and claimed != mode_blocked:
                    return "dimension_mislabeling_contradiction"

    # ── Incomplete category count ≠ item count ──
    if query_type == "get_incomplete_areas" and status == "success":
        categories = data.get("categories", {})
        for cat, cat_data in categories.items():
            declared_count = cat_data.get("count", 0)
            actual_items = cat_data.get("items", [])
            if declared_count != len(actual_items):
                return "incomplete_count_contradiction"

    # ── Source classification: operational state ≠ execution telemetry ──
    if query_type in ("get_process_registry", "get_recent_activity") and status == "success":
        all_sim = data.get("all_simulated_or_skipped", False)
        if all_sim:
            telemetry_claims = [
                "verified execution", "actual execution occurred",
                "real execution happened", "processes actually ran",
                "confirmed execution", "proven execution",
            ]
            for claim in telemetry_claims:
                if claim in response_lower:
                    return "source_classification_contradiction"

    # ── Planner-specific truth guards ──
    if capability_result.get("tool") == "nexus_query_planner" and status == "success":
        coverage = capability_result.get("coverage", {})
        plan = capability_result.get("plan", {})
        source_requirement = (
            capability_result.get("source_requirement")
            or plan.get("source_requirement")
        )
        if source_requirement is None and plan.get("domain") == "recent_activity":
            source_requirement = "execution_telemetry"

        # Execution telemetry unavailable → no execution-proof claims, but only
        # when the query actually required execution telemetry.
        if (
            source_requirement == "execution_telemetry"
            and not coverage.get("execution_telemetry", False)
        ):
            telemetry_claims = [
                "actually ran", "really ran", "did run", "has run",
                "currently running", "running live", "executed successfully",
                "genuine run", "real execution", "processes ran",
            ]
            for claim in telemetry_claims:
                if claim in response_lower:
                    return "planner_telemetry_contradiction"

        # Total count vs returned count — reject implied completeness
        data_obj = capability_result.get("data", {})
        if isinstance(data_obj, dict):
            total = data_obj.get("total", 0)
            filtered = data_obj.get("filtered_count")
            if total and filtered and filtered < total:
                # Model listed items but didn't mention truncation
                completeness_claims = [
                    "all processes", "every process", "the complete list",
                    "all of them", "here are all", "full list",
                ]
                for claim in completeness_claims:
                    if claim in response_lower:
                        return "planner_completeness_contradiction"

        if plan.get("domain") == "runtime_execution" and isinstance(data_obj, dict):
            summary = data_obj.get("summary", {})
            telemetry_coverage = data_obj.get("coverage", {})
            coverage_status = telemetry_coverage.get("coverage_status", "unknown")
            runs = data_obj.get("runs", [])

            count_labels = {
                "active_count": ("active", "running", "currently running"),
                "completed_count": ("completed", "complete"),
                "failed_count": ("failed", "failure", "failures"),
                "skipped_count": ("skipped",),
                "stale_count": ("stale", "stuck"),
            }
            for summary_key, labels in count_labels.items():
                verified_count = summary.get(summary_key)
                if verified_count is None:
                    continue
                for label in labels:
                    patterns = [
                        rf'\b(\d+)\s+{re.escape(label)}\b',
                        rf'\b{re.escape(label)}\s*[:=]\s*(\d+)\b',
                    ]
                    for pattern in patterns:
                        for match in re.findall(pattern, response_lower):
                            if int(match) != int(verified_count):
                                return "runtime_count_contradiction"

            if coverage_status != "complete":
                absolute_absence_claims = [
                    "nothing ran", "no process ran", "no processes ran",
                    "no nexus processes ran", "nothing executed",
                    "no process executed", "no processes executed",
                    "definitely did not run", "definitely didn't run",
                    "no failures", "no failures reported", "no processes failed",
                    "failed: 0", "failed=0",
                    "without failures", "without any failures",
                    "nothing failed", "no skipped", "no processes were skipped",
                    "no processes that were skipped", "none marked as skipped",
                    "no processes skipped", "skipped: 0", "skipped=0",
                    "count for skipped processes is zero",
                    "nothing was skipped", "all processes that ran",
                    "all recorded processes", "all work succeeded",
                    "all runs completed successfully", "runs completing successfully",
                    "processes ran without",
                    "all processes are currently idle",
                    "completed their last executions successfully",
                ]
                for claim in absolute_absence_claims:
                    if claim in response_lower:
                        return "runtime_coverage_contradiction"

            if summary.get("active_count", 0) == 0:
                running_claims = [
                    "is running right now", "are running right now",
                    "currently running", "actively running",
                ]
                for claim in running_claims:
                    if claim in response_lower:
                        return "runtime_running_contradiction"

            if summary.get("completed_count", 0) == 0:
                completed_claims = [
                    "completed today", "completed successfully",
                    "has completed", "did complete",
                ]
                for claim in completed_claims:
                    if claim in response_lower:
                        return "runtime_completion_contradiction"

            if summary.get("failed_count", 0) == 0:
                failed_claims = [
                    "failed today", "has failed", "did fail",
                    "is failing", "are failing",
                ]
                for claim in failed_claims:
                    if claim in response_lower:
                        return "runtime_failure_contradiction"

            wants_telegram_processing = any(
                word in response_lower
                for word in ("processed", "handled", "message", "update", "user work", "tasks today")
            ) and "telegram" in response_lower
            if wants_telegram_processing:
                has_update_run = any(
                    r.get("process_id") == "telegram_operator"
                    and r.get("execution_type") == "telegram_update_run"
                    and r.get("last_terminal_status") == "completed"
                    for r in runs
                )
                if not has_update_run:
                    return "runtime_polling_contradiction"

        # Ambiguity unresolved — reject definitive single-dimension claims
        ambiguity = plan.get("ambiguity")
        if ambiguity:
            field = ambiguity.get("field", "") if isinstance(ambiguity, dict) else str(ambiguity)
            if field == "blocked":
                definitive_claims = [
                    "blocked in execution mode",
                    "blocked in runtime",
                    "execution mode is blocked",
                    "runtime state is blocked",
                ]
                for claim in definitive_claims:
                    if claim in response_lower:
                        return "planner_ambiguity_contradiction"

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
    if error_reason == "planner_telemetry_contradiction":
        return "I do not have verified execution telemetry proving anything ran."
    if error_reason == "runtime_coverage_contradiction":
        return "Telemetry coverage is partial, so I cannot turn missing records into proof that nothing ran."
    if error_reason == "runtime_running_contradiction":
        return "I do not have a fresh non-stale started run proving a Nexus process is running right now."
    if error_reason == "runtime_completion_contradiction":
        return "I do not have a completed terminal telemetry event for that claim."
    if error_reason == "runtime_failure_contradiction":
        return "I do not have a failed terminal telemetry event for that claim."
    if error_reason == "runtime_polling_contradiction":
        return (
            "I have verified Telegram worker poll telemetry, but I do not have a "
            "verified telegram_update_run showing Telegram Operator actually processed a message."
        )
    if error_reason == "runtime_count_contradiction":
        return "The generated response disagreed with the verified runtime telemetry counts."
    if error_reason == "planner_completeness_contradiction":
        return "I retrieved a partial result set, so I cannot honestly present it as a complete list."
    if error_reason == "planner_ambiguity_contradiction":
        return (
            "Blocked is dimension-specific in Nexus: configuration_state blocked, "
            "execution_mode BLOCKED, and runtime_state blocked are separate states."
        )
    return "I'm not sure how to respond to that. Could you try again?"


def _build_verified_planner_fallback(
    capability_result: Dict[str, Any],
    error_reason: str,
) -> Optional[str]:
    """Build a deterministic truthful answer from verified planner data."""
    if capability_result.get("tool") != "nexus_query_planner":
        return None

    plan = capability_result.get("plan", {})
    data = capability_result.get("data", {})
    coverage = capability_result.get("coverage", {})
    domain = plan.get("domain")
    source_requirement = (
        capability_result.get("source_requirement")
        or plan.get("source_requirement")
    )

    if error_reason == "planner_telemetry_contradiction":
        return "I do not have verified execution telemetry proving anything ran."

    if domain == "processes" and isinstance(data, dict):
        config = data.get("configuration_counts", {})
        modes = data.get("mode_counts", {})
        runtime = data.get("runtime_counts", {})
        lines = []

        if plan.get("operation") in ("count", "group_count", "overview", "list", "filter"):
            if config:
                lines.append(
                    "Configuration state: "
                    + ", ".join(f"{key}={value}" for key, value in sorted(config.items()))
                )
            if modes:
                lines.append(
                    "Execution mode: "
                    + ", ".join(f"{key}={value}" for key, value in sorted(modes.items()))
                )
            if runtime:
                lines.append(
                    "Runtime state: "
                    + ", ".join(f"{key}={value}" for key, value in sorted(runtime.items()))
                )

        total = capability_result.get("total_count")
        returned = capability_result.get("returned_count")
        if total is not None and returned is not None and returned != total:
            lines.append(f"Retrieved {returned} matching records out of {total} total records.")

        if (
            source_requirement == "execution_telemetry"
            and not coverage.get("execution_telemetry", False)
        ):
            lines.append("I do not have verified execution telemetry proving anything ran.")

        return "\n".join(lines) if lines else None

    if domain == "runtime_execution" and isinstance(data, dict):
        summary = data.get("summary", {})
        telemetry_coverage = data.get("coverage", {})
        lines = [
            f"Runtime telemetry coverage is {telemetry_coverage.get('coverage_status', 'unknown')}.",
            (
                "Verified run counts: "
                f"active={summary.get('active_count', 0)}, "
                f"completed={summary.get('completed_count', 0)}, "
                f"failed={summary.get('failed_count', 0)}, "
                f"skipped={summary.get('skipped_count', 0)}, "
                f"stale={summary.get('stale_count', 0)}."
            ),
        ]
        if telemetry_coverage.get("coverage_status") != "complete":
            lines.append("Because coverage is not complete, missing records are not proof that nothing ran.")
        runs = data.get("runs", [])
        if runs:
            latest = runs[0]
            lines.append(
                f"Most recent verified run: {latest.get('process_name', latest.get('process_id'))} "
                f"({latest.get('run_id')}) status={latest.get('status')}."
            )
        return " ".join(lines)

    if domain == "recent_activity" and source_requirement == "execution_telemetry":
        return "I do not have verified execution telemetry proving anything ran."

    return None


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
            "build_sha": BUILD_SHA,
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
            "build_sha": BUILD_SHA,
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
            "build_sha": BUILD_SHA,
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

    # ── Priority 2.5: Semantic query planner ──
    # Try the schema-aware planner before keyword routing.
    # Uses LLM-driven planning by default; deterministic fallback on failure.
    try:
        planner_context = _build_planner_context(state)
        with stage_execution(
            stage="planner",
            source="scripts/nexus_agent_platform/agents/nova.py:_capability_gate",
            metadata={"operation": "plan_query"},
        ):
            planner_plan = plan_query(
                text,
                conversation_context=planner_context,
                model_call_fn=_planner_model_call,
            )
        if planner_plan.get("domain") not in (None, "none"):
            with stage_execution(
                stage="capability",
                source="scripts/nexus_agent_platform/agents/nova.py:_capability_gate",
                metadata={
                    "operation": "execute_plan",
                    "domain": planner_plan.get("domain"),
                    "planner_mode": planner_plan.get("planner_mode"),
                    "capability": DOMAIN_SCHEMAS.get(planner_plan.get("domain"), {}).get("capability"),
                },
            ):
                planner_result = execute_plan(planner_plan)
            if planner_result.get("status") not in ("error",):
                planner_data = planner_result.get("data", {})
                total_count, returned_count, truncated = _planner_result_counts(planner_data)
                state.metadata["capability_gate"] = {
                    "decision": "planner_executed",
                    "domain": planner_plan.get("domain"),
                    "operation": planner_plan.get("operation"),
                    "source_requirement": planner_plan.get("source_requirement"),
                    "capability_selected": planner_result.get("capability_selected"),
                    "plan": planner_plan,
                    "planner_mode": planner_plan.get("planner_mode", "unknown"),
                    "planner_model": planner_plan.get("planner_model"),
                    "planner_provider": planner_plan.get("planner_provider"),
                    "fallback_reason": planner_plan.get("fallback_reason"),
                    "validation_status": planner_plan.get("validation_status"),
                    "build_sha": BUILD_SHA,
                    "trace_id": trace_id,
                }
                state.metadata["capability_result"] = {
                    "tool": "nexus_query_planner",
                    "query_type": planner_plan.get("domain", "unknown"),
                    "status": planner_result.get("status", "unknown"),
                    "data": planner_data,
                    "provenance": planner_result.get("provenance", {}),
                    "coverage": planner_result.get("coverage", {}),
                    "plan": planner_plan,
                    "planner_mode": planner_plan.get("planner_mode", "unknown"),
                    "planner_model": planner_plan.get("planner_model"),
                    "planner_provider": planner_plan.get("planner_provider"),
                    "fallback_reason": planner_plan.get("fallback_reason"),
                    "validation_status": planner_plan.get("validation_status"),
                    "source_requirement": planner_result.get("source_requirement") or planner_plan.get("source_requirement"),
                    "capability_selected": planner_result.get("capability_selected"),
                    "total_count": total_count,
                    "returned_count": returned_count,
                    "truncated": truncated,
                    "trace_id": trace_id,
                }
                planner_provenance = {
                    **(planner_result.get("provenance") or {}),
                    "tool": "nexus_query_planner",
                    "domain": planner_plan.get("domain"),
                    "operation": planner_plan.get("operation"),
                    "source_requirement": planner_result.get("source_requirement") or planner_plan.get("source_requirement"),
                    "coverage": planner_result.get("coverage", {}),
                    "capability_selected": planner_result.get("capability_selected"),
                    "status": planner_result.get("status", "unknown"),
                    "trace_id": trace_id,
                }
                save_provenance(chat_id, planner_provenance)
                return state
    except Exception as exc:
        log.debug("Planner failed, falling through to keyword routing: %s", exc)

    # ── Priorities 3-14: Semantic capability gate (legacy keyword routing) ──
    gate_result = _semantic_capability_gate(text)
    if gate_result is None:
        state.metadata["capability_gate"] = {
            "decision": "no_capability",
            "capability": None,
            "build_sha": BUILD_SHA,
            "trace_id": trace_id,
        }
        state.metadata["capability_result"] = None
        return state

    capability, arguments = gate_result

    # Execute through shared certified layer
    from nexus_agent_platform.capabilities.shared import execute_shared_capability
    try:
        with stage_execution(
            stage="capability",
            source="scripts/nexus_agent_platform/agents/nova.py:_capability_gate",
            metadata={"operation": "execute_shared_capability", "capability": capability},
        ):
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
        "build_sha": BUILD_SHA,
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
    started = time.monotonic()
    chat_id = state.metadata.get("chat_id", 0)
    verified_context_chars = 0

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
        elif capability_result.get("tool") == "nexus_query_planner":
            planner_context = _format_planner_context(capability_result)
            verified_context_chars = len(planner_context)
            source_requirement = (
                capability_result.get("source_requirement")
                or capability_result.get("plan", {}).get("source_requirement")
            )
            telemetry_instruction = ""
            if source_requirement == "execution_telemetry":
                telemetry_instruction = (
                    "If verified execution telemetry is unavailable, say that directly. "
                    "Do not turn lack of telemetry into proof that nothing ran. "
                    "For runtime_execution data: claim running only for a fresh non-stale run with no terminal event; "
                    "claim completed only from completed terminal events; claim failed only from failed terminal events; "
                    "when coverage is partial or unavailable, qualify absence of matching records. "
                    "Do not treat worker_poll as proof that user work or a Telegram message was processed; "
                    "Telegram message processing requires execution_type=telegram_update_run. "
                )
            study_instruction = ""
            if capability_result.get("query_type") == "nexus_system":
                study_instruction = (
                    "For Nexus study questions, answer from the Study snapshot facts exactly. "
                    "Do not invent gap, contradiction, unknown, integration, or offer categories. "
                    "Preserve the study counts, unknown IDs, source_commit, and generated_at when relevant. "
                    "Treat the study snapshot as historical; if current runtime telemetry is included, "
                    "label it separately from the study snapshot. "
                    "For stale or changed study findings, use the Study/current reconciliation block first. "
                )
            user_content = (
                f"{state.user_message}\n\n"
                f"{planner_context}\n\n"
                f"Respond naturally using the verified data above. "
                f"Do not contradict the verified facts. "
                f"Do not fabricate alternative values. "
                f"Do not deny access to data that was successfully retrieved. "
                f"If the data shows a total count, do not list fewer items and imply completeness. "
                f"Treat configuration_state, execution_mode, and runtime_state as independent dimensions. "
                f"Do not infer disabled from skipped, or skipped from disabled. "
                f"Allow records to belong to multiple categories across different dimensions. "
                f"Enabled category membership is based only on configuration_state=enabled, regardless of execution_mode or runtime_state. "
                f"If the user asks to keep categories separate, build each category from the raw process records. "
                f"If you state a category count and present the category as a list, include every matching record "
                f"or explicitly say which names were omitted. "
                f"{telemetry_instruction}"
                f"{study_instruction}"
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
    if capability_result and capability_result.get("query_type") == "nexus_system":
        capability_data = capability_result.get("data", {})
        capability_chars = len(json.dumps(capability_data, default=str))
        context_chars = sum(len(m.get("content", "")) for m in messages)
        state.metadata["study_context_metrics"] = {
            "capability_result_chars": capability_chars,
            "capability_result_approx_tokens": capability_chars // 4,
            "verified_context_chars": verified_context_chars,
            "verified_context_approx_tokens": verified_context_chars // 4,
            "model_context_chars": context_chars,
            "model_context_approx_tokens": context_chars // 4,
            "context_shaping_ms": int((time.monotonic() - started) * 1000),
            "context_profile": capability_data.get("context_profile", "full_snapshot"),
            "raw_artifact_bytes": capability_data.get("retrieval_metrics", {}).get("raw_artifact_bytes", {}),
            "artifact_index_load_ms": capability_data.get("retrieval_metrics", {}).get("artifact_index_load_ms"),
            "runtime_reconciliation_ms": capability_data.get("retrieval_metrics", {}).get("runtime_reconciliation_ms"),
            "overview_build_ms": capability_data.get("retrieval_metrics", {}).get("overview_build_ms"),
            "structured_records_selected": capability_data.get("retrieval_metrics", {}).get("structured_records_selected", {}),
        }
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
        with stage_execution(
            stage="generation",
            source="scripts/nexus_agent_platform/agents/nova.py:_generate_response",
            metadata={"purpose": "final_generation"},
        ):
            result = asyncio.run(_call_model(messages, chat_id, purpose="final_generation"))
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
        state.metadata["model_error_type"] = exc.__class__.__name__
        content = ""

    state.assistant_response = content
    return state


def _validate_output(state: AgentState) -> AgentState:
    """Validate the generated response against capability facts and general rules."""
    with stage_execution(
        stage="truth_guard",
        source="scripts/nexus_agent_platform/agents/nova.py:_validate_output",
    ):
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
        if state.metadata.get("model_error_type") in ("TimeoutError", "TimeoutException"):
            state.metadata["validation_regen"] = False
            capability_result = state.metadata.get("capability_result") or {}
            state.assistant_response = (
                _build_verified_planner_fallback(capability_result, error_reason)
                or _build_fallback_response("provider_exception", state.user_message)
            )
            state.metadata["fallback_used"] = True
            return state

        # One regeneration attempt
        import asyncio
        messages = state.metadata.get("model_messages", [])
        chat_id = state.metadata.get("chat_id", 0)

        try:
            with stage_execution(
                stage="generation",
                source="scripts/nexus_agent_platform/agents/nova.py:_validate_output",
                metadata={"purpose": "validation_regeneration"},
            ):
                result = asyncio.run(_call_model(messages, chat_id, purpose="validation_regeneration"))
            content = result.get("content", "")
            if content and not validate_response(content, state.user_message):
                # Also check capability contradiction on regen
                capability_result = state.metadata.get("capability_result")
                if capability_result:
                    cap_err = _validate_against_capability(content, capability_result)
                    if cap_err:
                        state.assistant_response = (
                            _build_verified_planner_fallback(capability_result, cap_err)
                            or _build_fallback_response(error_reason, state.user_message)
                        )
                        state.metadata["fallback_used"] = True
                        return state
                state.assistant_response = content
                state.metadata["regen_success"] = True
                return state
        except Exception:
            pass

        # Regen failed — use fallback
        capability_result = state.metadata.get("capability_result") or {}
        state.assistant_response = (
            _build_verified_planner_fallback(capability_result, error_reason)
            or _build_fallback_response(error_reason, state.user_message)
        )
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
    # Register the capability executor for the semantic query planner
    from nexus_agent_platform.capabilities.shared import execute_shared_capability
    def _planner_executor(capability: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return execute_shared_capability(
            "hermes_nova", capability, arguments or {}, trace_id="planner",
        )
    register_executor(_planner_executor)

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
