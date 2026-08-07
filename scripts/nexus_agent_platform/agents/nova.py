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

Supabase is an optional read-only information source.
Nova decides when to use it. The source never decides for Nova.

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
from typing import Any, Dict, List, Optional

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

Supabase access (read-only, when explicitly requested):
- You have governed read-only access to approved Supabase information.
- When Ray explicitly asks you to search or check Supabase, you can use
  your read-only tools to retrieve information.
- Available reads: client counts, identity lookups, runtime capabilities,
  and general approved-table discovery.
- You cannot create, update, delete, or alter records.
- You cannot execute arbitrary SQL.
- When you retrieve Supabase data, identify the source accurately.
- If a source fails or is unavailable, say so honestly — never claim
  "not found" when verification was incomplete.

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


# ─── Source-Directed Supabase Detection ────────────────────

_SUPABASE_SOURCE_PATTERN = re.compile(
    r'\b(?:search|check|query|look\s+(?:in|through|up)|inspect|find|verify|review|'
    r'research|pull|use)\b.*\bsupabase\b',
    re.I,
)

_SUPABASE_NAME_PATTERN = re.compile(r'\bsupabase\b', re.I)


def _detect_supabase_source(text: str) -> Optional[str]:
    """Detect if the user explicitly named Supabase as an information source.

    Returns the raw user request to pass to the Supabase tool, or None
    if Supabase was not explicitly named.

    This is source-directed detection — not an intent classifier.
    Its only purpose is: Ray explicitly named Supabase → give the request
    to Nova's Supabase information tool.
    """
    if _SUPABASE_SOURCE_PATTERN.search(text):
        return text
    return None


def _is_write_request(text: str) -> bool:
    """Detect if the user is requesting a write operation."""
    write_patterns = re.compile(
        r'\b(?:create|add|insert|update|delete|remove|disable|enable|invite|'
        r'edit|modify|set|change|revoke|approve|reject)\b.*'
        r'\b(?:user|account|profile|record|client)\b',
        re.I,
    )
    return bool(write_patterns.search(text))


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
    if _is_write_request(request):
        return {
            "tool": "nova_search_supabase",
            "status": "denied",
            "message": (
                "Write operations are not permitted. I have read-only access to Supabase. "
                "I can look up existing information but cannot create, modify, or delete anything."
            ),
            "trace_id": trace_id,
        }

    # Detect what kind of Supabase query is needed
    request_lower = request.lower()

    # Identity lookup (email present)
    email_match = re.search(
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', request
    )
    if email_match and any(w in request_lower for w in [
        "user", "account", "identity", "email", "who", "verify", "check",
        "exist", "registered", "profile",
    ]):
        result = execute_shared_capability(
            "hermes_nova",
            "resolve_user_identity_by_email",
            {"email": email_match.group(0)},
            trace_id=trace_id,
        )
        return {
            "tool": "nova_search_supabase",
            "query_type": "identity_lookup",
            "status": result.get("status", "unknown"),
            "data": result.get("data", {}),
            "provenance": result.get("provenance", {}),
            "trace_id": trace_id,
        }

    # Client count
    if any(w in request_lower for w in [
        "client count", "how many clients", "total clients",
        "number of clients", "client profiles", "production clients",
        "active clients", "customer total", "client total",
    ]):
        result = execute_shared_capability(
            "hermes_nova",
            "get_client_count",
            {},
            trace_id=trace_id,
        )
        return {
            "tool": "nova_search_supabase",
            "query_type": "client_count",
            "status": result.get("status", "unknown"),
            "data": result.get("data", {}),
            "provenance": result.get("provenance", {}),
            "trace_id": trace_id,
        }

    # Runtime capabilities
    if any(w in request_lower for w in [
        "what can you access", "your capabilities", "what do you have access",
        "what systems", "can you access", "your access", "what can you do",
    ]):
        result = execute_shared_capability(
            "hermes_nova",
            "get_runtime_capabilities",
            {},
            trace_id=trace_id,
        )
        return {
            "tool": "nova_search_supabase",
            "query_type": "runtime_capabilities",
            "status": result.get("status", "unknown"),
            "data": result.get("data", {}),
            "provenance": result.get("provenance", {}),
            "trace_id": trace_id,
        }

    # General search — route through shared layer
    result = execute_shared_capability(
        "hermes_nova",
        "general_search",
        {"query": request},
        trace_id=trace_id,
    )
    return {
        "tool": "nova_search_supabase",
        "query_type": "general_search",
        "status": result.get("status", "unknown"),
        "data": result.get("data", {}),
        "provenance": result.get("provenance", {}),
        "trace_id": trace_id,
    }


def _format_supabase_result(result: Dict[str, Any]) -> str:
    """Format a Supabase search result as natural context for Nova's brain."""
    status = result.get("status", "unknown")
    query_type = result.get("query_type", "unknown")

    if status == "denied":
        return result.get("message", "Write operations are not permitted.")

    if status == "unavailable":
        return result.get("message", "Supabase is not available right now.")

    if query_type == "client_count":
        data = result.get("data", {})
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo("America/Phoenix"))
        timestamp = now.strftime("%-I:%M %p Phoenix time on %B %-d, %Y")
        return (
            f"Supabase data (retrieved {timestamp}):\n"
            f"- Production clients: {data.get('production_clients', 'unknown')}\n"
            f"- Active: {data.get('active', 'unknown')}\n"
            f"- Onboarding: {data.get('onboarding', 'unknown')}\n"
            f"- Tester/certification: {data.get('tester_or_certification', 'unknown')}\n"
            f"- Total profiles: {data.get('all_profiles', 'unknown')}"
        )

    if query_type == "identity_lookup":
        data = result.get("data", {})
        email = data.get("normalized_email", "unknown")
        exists = data.get("exists_anywhere", False)
        complete = data.get("verification_complete", True)
        classifications = data.get("account_classifications", [])
        sources = data.get("sources", {})

        lines = [f"Identity lookup for {email}:"]
        if not complete:
            failed = [k for k, v in sources.items()
                      if v.get("status") in ("error", "incomplete")]
            lines.append(f"Verification incomplete. Sources with issues: {', '.join(failed)}")
        elif exists:
            lines.append(f"Found in approved identity sources.")
            if classifications:
                lines.append(f"Classifications: {', '.join(classifications)}")
            for src, info in sources.items():
                if info.get("exists"):
                    lines.append(f"  - {src}: found")
                else:
                    lines.append(f"  - {src}: not found")
        else:
            lines.append("Not found in any approved identity source.")
        return "\n".join(lines)

    if query_type == "runtime_capabilities":
        data = result.get("data", {})
        reads = data.get("available_reads", [])
        writes = data.get("available_actions", [])
        return (
            f"Supabase access status:\n"
            f"- Connected: {data.get('connected_systems', {}).get('supabase', {}).get('status', 'unknown')}\n"
            f"- Approved reads: {', '.join(sorted(reads))}\n"
            f"- Approved writes: {', '.join(sorted(writes)) if writes else 'none'}"
        )

    if query_type == "general_search":
        data = result.get("data", {})
        matches = data.get("matches", [])
        if not matches:
            sources_searched = data.get("sources_searched", [])
            return (
                f"I searched the approved Supabase tables ({', '.join(sources_searched)}) "
                f"but did not find an exact match for that query."
            )
        lines = [f"Supabase search results ({len(matches)} matches):"]
        for m in matches[:5]:
            source = m.get("source", "")
            match_val = m.get("match", "")
            mtype = m.get("type", "")
            detail = f" ({m.get('status', '')})" if m.get("status") else ""
            lines.append(f"  - [{source}] {match_val}{detail} — {mtype}")
        return "\n".join(lines)

    return f"Supabase result: {json.dumps(result, default=str)[:300]}"


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

    # Not a utility — pass through to model
    state.metadata["utility_used"] = None
    return state


def _prepare_context(state: AgentState) -> AgentState:
    """Prepare context for the model, including Supabase data if explicitly requested.

    This node runs AFTER handle_utility and BEFORE build_context.
    It detects explicit Supabase source mentions and fetches data
    to include as context for the model.

    This is NOT an intent classifier. It is source-directed detection:
    Ray explicitly named Supabase → fetch data → include in context.
    """
    if state.assistant_response:
        state.metadata["supabase_data"] = None
        return state

    text = state.user_message
    chat_id = state.metadata.get("chat_id", 0)

    # Source-directed detection: did Ray explicitly name Supabase?
    supabase_request = _detect_supabase_source(text)
    if supabase_request:
        trace_id = f"nova_{chat_id}_{int(time.time())}"
        result = _nova_search_supabase(
            supabase_request,
            chat_id=chat_id,
            trace_id=trace_id,
        )
        state.metadata["supabase_data"] = result
        state.metadata["supabase_trace_id"] = trace_id
    else:
        state.metadata["supabase_data"] = None

    return state


def _build_context(state: AgentState) -> AgentState:
    """Build the model context with SOUL, conversation history, and any Supabase data."""
    chat_id = state.metadata.get("chat_id", 0)

    # Load conversation history
    history = load_memory(chat_id)
    state.metadata["conversation_turns"] = len(history) // 2

    # Build messages for the model
    messages = [{"role": "system", "content": SOUL}]

    # Add conversation history (bounded)
    for msg in history[-MEMORY_MAX_TURNS * 2:]:
        messages.append(msg)

    # Build the user message, potentially with Supabase context
    user_content = state.user_message

    supabase_data = state.metadata.get("supabase_data")
    if supabase_data:
        supabase_context = _format_supabase_result(supabase_data)
        user_content = (
            f"{state.user_message}\n\n"
            f"[Supabase data retrieved for your reference — incorporate this naturally into your response]\n"
            f"{supabase_context}"
        )

    messages.append({"role": "user", "content": user_content})

    state.metadata["model_messages"] = messages
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
    """Validate the generated response."""
    error_reason = validate_response(state.assistant_response, state.user_message)

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
      classify_intent → handle_utility → prepare_context → build_context
      → generate_response → validate_output → compose_output

    Nova's original conversational brain always runs.
    Supabase data is fetched as context when explicitly requested.
    No pre-model capability interception.
    """
    graph = GraphAdapter(agent_id=AGENT_ID)
    graph.add_node("classify_intent", _classify_intent)
    graph.add_node("handle_utility", _handle_utility)
    graph.add_node("prepare_context", _prepare_context)
    graph.add_node("build_context", _build_context)
    graph.add_node("generate_response", _generate_response)
    graph.add_node("validate_output", _validate_output)
    graph.add_node("compose_output", _compose_output)

    graph.add_edge("classify_intent", "handle_utility")
    graph.add_edge("handle_utility", "prepare_context")
    graph.add_edge("prepare_context", "build_context")
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
