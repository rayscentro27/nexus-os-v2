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

Governed read access (routed through shared certified capabilities):
  - get_runtime_capabilities — what Nova can access
  - get_client_count — live client profile counts
  - resolve_user_identity_by_email — exact email lookup across approved identity sources

Nova does NOT have access to:
  - Unrestricted Supabase writes
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
from nexus_agent_platform.connectors.nova_supabase import (
    detect_nova_write_request,
    execute_nova_capability,
    generate_nova_provenance_response,
    get_nova_capabilities,
)

log = logging.getLogger(__name__)

AGENT_ID = "hermes_nova"

# ─── SOUL ─────────────────────────────────────────────────

SOUL = """You are Hermes Nova — a thoughtful, conversational AI assistant.

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

Governed read access:
- You have read-only access to Supabase through three approved governed capabilities:
  1. get_runtime_capabilities — tells you what you can access
  2. get_client_count — live client profile counts
  3. resolve_user_identity_by_email — exact email lookup across approved identity sources
- This is governed, audited, read-only access — not unrestricted database access.
- When you use a capability, identify the source accurately (e.g., "from the Supabase source").
- You cannot create, edit, disable, invite, or delete users.
- You cannot execute arbitrary SQL or query arbitrary tables.
- When asked about Nexus internals beyond your reads, explain you are Nova with limited governed access.

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


def _check_supabase_capability(state: AgentState) -> AgentState:
    """Check if the user message is requesting a governed Supabase capability."""
    # Skip if utility already handled it
    if state.assistant_response:
        state.metadata["capability_used"] = None
        return state

    text = state.user_message

    # Check for write attempts first
    write_denial = detect_nova_write_request(text)
    if write_denial:
        # Optionally check if the email already exists before denying
        email = write_denial.get("arguments", {}).get("email")
        if email and write_denial.get("read_available"):
            result = execute_nova_capability(
                "resolve_user_identity_by_email",
                {"email": email},
            )
            existence_note = generate_nova_provenance_response(
                "resolve_user_identity_by_email", result
            )
            state.assistant_response = (
                "Write operations are not permitted — I have read-only access. "
                f"However, I can tell you that {existence_note}"
            )
        else:
            state.assistant_response = (
                "Write operations are not permitted. I have read-only access to Supabase — "
                "I can look up existing information but cannot create, modify, or delete anything."
            )
        state.metadata["capability_used"] = "write_denied"
        return state

    # Check for capability triggers
    lower = text.lower()
    capabilities = get_nova_capabilities()
    triggered = None

    for cap in capabilities:
        if cap["trigger"](lower):
            triggered = cap
            break

    if not triggered:
        state.metadata["capability_used"] = None
        return state

    # Extract arguments for the capability
    capability_id = triggered["id"]
    arguments = {}

    if capability_id == "resolve_user_identity_by_email":
        import re as _re
        email_match = _re.search(
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text
        )
        if email_match:
            arguments["email"] = email_match.group(0)

    # Execute the capability through the shared adapter
    result = execute_nova_capability(capability_id, arguments)

    # Build response with provenance
    response = generate_nova_provenance_response(capability_id, result)
    state.assistant_response = response
    state.metadata["capability_used"] = capability_id
    state.metadata["capability_result"] = result
    return state


def _build_context(state: AgentState) -> AgentState:
    """Build the model context with SOUL and conversation history."""
    chat_id = state.metadata.get("chat_id", 0)

    # Load conversation history
    history = load_memory(chat_id)
    state.metadata["conversation_turns"] = len(history) // 2

    # Build messages for the model
    messages = [{"role": "system", "content": SOUL}]

    # Add conversation history (bounded)
    for msg in history[-MEMORY_MAX_TURNS * 2:]:
        messages.append(msg)

    # Add current user message
    messages.append({"role": "user", "content": state.user_message})

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
    """Build and compile the Nova LangGraph."""
    graph = GraphAdapter(agent_id=AGENT_ID)
    graph.add_node("classify_intent", _classify_intent)
    graph.add_node("handle_utility", _handle_utility)
    graph.add_node("check_supabase", _check_supabase_capability)
    graph.add_node("build_context", _build_context)
    graph.add_node("generate_response", _generate_response)
    graph.add_node("validate_output", _validate_output)
    graph.add_node("compose_output", _compose_output)

    graph.add_edge("classify_intent", "handle_utility")
    graph.add_edge("handle_utility", "check_supabase")

    def _route_after_check(state: AgentState) -> str:
        if state.metadata.get("capability_used"):
            return "to_compose"
        return "to_context"

    graph.add_conditional_edge(
        "check_supabase",
        _route_after_check,
        {"to_compose": "compose_output", "to_context": "build_context"},
    )
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
