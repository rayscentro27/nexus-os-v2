"""Hermes agent — internal operator / chief-of-staff.

Hermes has its own LangGraph graph, SOUL instructions, capability
registry, context store, and Telegram worker.  The graph is compiled
at module import time (when the feature flag is on) so that
``HermesGraphAdapter.invoke`` is ready immediately.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from nexus_agent_platform.adapters.graph_adapter import GraphAdapter
from nexus_agent_platform.adapters.otel_adapter import OtelAdapter
from nexus_agent_platform.state import AgentState
from nexus_agent_platform.capabilities.registry import CapabilityRegistry
from nexus_agent_platform.context.resolver import get_active_context, update_active_context
from nexus_agent_platform.reports.ceo_formatter import format_ceo_report

log = logging.getLogger(__name__)

AGENT_ID = "hermes"

SOUL = """You are Nexus Hermes — the internal operator and chief-of-staff.
You manage operations, coordinate across tools, and surface only
actionable information to Ray.  You speak in plain language with
executive clarity.  You do NOT give external-facing advice to
clients — you run the business.  Safety boundaries are enforced
by the capability registry and blocked-action guard."""


# ─── Intent Classification ──────────────────────────────────

_INTENT_PATTERNS = {
    # Multi-intent patterns MUST come before single-intent patterns
    "multi_intent_report_email": r"\b(show\s+.*report.*email|report\s+and\s+email|email.*report)\b",
    "greeting": r"\b(hello|hi|good\s+(morning|afternoon|evening)|hey|greetings)\b",
    "current_time": r"\b(what\s+time|current\s+time|time\s+is\s+it|clock)\b",
    "client_count": r"\b(how\s+many\s+clients|client\s+count|number\s+of\s+clients)\b",
    "client_acquisition": r"\b(how\s+can\s+we\s+get\s+more\s+clients|get\s+more\s+clients|acquire\s+clients|find\s+clients|new\s+clients)\b",
    "send_email": r"\b(send\s+an?\s+email|email\s+to|email\s+ray|send\s+mail)\b",
    "schedule_report": r"\b(run\s+(this|the)\s+(same\s+)?report\s+(tomorrow|in\s+\d+|daily|again)|schedule\s+(a\s+)?report)\b",
    "create_prompt": r"\b(create\s+(a\s+)?prompt|write\s+(a\s+)?prompt|prompt\s+for\s+opencode|opencode\s+prompt)\b",
    "system_status": r"\b(system\s+(status|report)|running\s+processes|process\s+report|what(?:'s| is)\s+running)\b",
    "failure_report": r"\b(what\s+failed|failures?\s+today|errors?\s+today|what(?:'s| is)\s+broke|issues?\s+today)\b",
    "alpha_status": r"\b(what\s+is\s+alpha|alpha\s+doing|alpha\s+status|alpha\s+research)\b",
}


def _classify_intent(text: str) -> str:
    lower = text.lower().strip()
    for intent, pattern in _INTENT_PATTERNS.items():
        if re.search(pattern, lower):
            return intent
    return "general_advisory"


# ─── Graph Node Functions ───────────────────────────────────

def _classify_intent_node(state: AgentState) -> AgentState:
    """Classify the user message intent."""
    state.intent = _classify_intent(state.user_message)
    state.metadata["classified_intent"] = state.intent
    return state


def _resolve_context(state: AgentState) -> AgentState:
    """Resolve active context, follow-ups, and slot filling."""
    active = get_active_context(AGENT_ID)
    state.active_context = active

    # Check for follow-up references
    lower = state.user_message.lower()
    if any(w in lower for w in ["that report", "this report", "the same", "same report", "tomorrow"]):
        # Try to resolve prior context
        if "last_report" in active:
            state.context["prior_report"] = active["last_report"]
            state.metadata["context_resolved"] = "prior_report"

    return state


def _route_to_capability(state: AgentState) -> AgentState:
    """Route to the appropriate capability based on intent."""
    intent = state.intent or "general_advisory"

    # Multi-intent detection
    if state.metadata.get("classified_intent") == "multi_intent_report_email":
        state.metadata["multi_intent"] = True
        state.metadata["intents"] = ["system_status", "send_email"]
        state.slot_fill_target = "email_recipient"
        return state

    # Slot filling for email
    if intent == "send_email":
        # Check if recipient already known
        email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', state.user_message)
        if email_match:
            state.slots["email_recipient"] = email_match.group(0)
        else:
            state.slot_fill_target = "email_recipient"

    # Schedule report — check if we have a prior report reference
    if intent == "schedule_report":
        if "prior_report" not in state.context:
            state.slot_fill_target = "report_reference"

    # Client count — no slot filling needed
    # Client acquisition — advisory only, no tool
    # Greeting + time — combine
    if intent == "greeting":
        lower = state.user_message.lower()
        if any(w in lower for w in ["time", "what time", "clock"]):
            state.intent = "greeting_time"
            state.metadata["classified_intent"] = "greeting_time"

    return state


def _execute_capability(state: AgentState) -> AgentState:
    """Execute the selected capability."""
    intent = state.intent or "general_advisory"

    if intent == "greeting" or intent == "greeting_time":
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo("America/Phoenix"))
        time_str = now.strftime("%I:%M %p")
        greeting = "Good afternoon" if 12 <= now.hour < 17 else ("Good morning" if now.hour < 12 else "Good evening")
        if intent == "greeting_time":
            state.assistant_response = f"{greeting}, Ray. It's {time_str} Phoenix time."
        else:
            state.assistant_response = f"{greeting}, Ray. How can I help?"

    elif intent == "current_time":
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo("America/Phoenix"))
        state.assistant_response = f"It's {now.strftime('%I:%M %p')} Phoenix time."

    elif intent == "client_count":
        count = _get_client_count()
        state.assistant_response = f"We have {count} active clients."
        state.metadata["capability_used"] = "get_client_count"

    elif intent == "client_acquisition":
        state.assistant_response = (
            "Here are the current client acquisition channels:\n\n"
            "1. Referrals from existing clients\n"
            "2. LinkedIn outreach to qualified prospects\n"
            "3. Content marketing and SEO\n"
            "4. Partnerships with complementary agencies\n\n"
            "Want me to dive deeper into any of these?"
        )
        state.metadata["capability_used"] = "client_acquisition_advisory"
        # No client-count tool used
        state.metadata["tool_used"] = None

    elif intent == "send_email":
        recipient = state.slots.get("email_recipient")
        if recipient:
            state.assistant_response = (
                f"Ready to send an email to {recipient}.\n\n"
                "I need:\n"
                "- Subject line\n"
                "- Body text\n\n"
                "What should the email say?"
            )
            state.metadata["capability_used"] = "send_email"
            state.metadata["slot_filled"] = {"email_recipient": recipient}
        else:
            state.assistant_response = "Who should I send the email to?"
            state.metadata["capability_used"] = "send_email"
            state.metadata["slot_fill_needed"] = "email_recipient"

    elif intent == "schedule_report":
        prior = state.context.get("prior_report")
        if prior:
            state.assistant_response = (
                f"I'll schedule that report to run again.\n\n"
                "What time should I run it? Default is 8:00 AM Phoenix time."
            )
            state.metadata["capability_used"] = "schedule_report"
            state.metadata["prior_report_resolved"] = True
        else:
            state.assistant_response = (
                "Which report would you like me to schedule?\n"
                "You can reference it by name or describe what it covers."
            )
            state.metadata["capability_used"] = "schedule_report"
            state.metadata["slot_fill_needed"] = "report_reference"

    elif intent == "create_prompt":
        task = state.active_context.get("current_task", {}).get("value", "")
        if task:
            state.assistant_response = f"Here's a prompt for OpenCode based on your current task:\n\n```\n{task}\n```\n\nWant me to refine it?"
        else:
            state.assistant_response = "What task should the prompt be for? Describe what you want OpenCode to do."
        state.metadata["capability_used"] = "create_opencode_prompt"

    elif intent == "system_status":
        status = _get_system_status()
        state.assistant_response = format_ceo_report(
            headline="System Status",
            working=status.get("working", "All systems operational"),
            needs_attention=status.get("needs_attention", ""),
            detail=status.get("detail", ""),
        )
        state.metadata["capability_used"] = "system_status"

    elif intent == "failure_report":
        failures = _get_failure_report()
        state.assistant_response = format_ceo_report(
            headline="Today's Failures",
            working= failures.get("working", "No active failures"),
            needs_attention=failures.get("needs_attention", ""),
            detail=failures.get("detail", ""),
        )
        state.metadata["capability_used"] = "failure_report"

    elif intent == "alpha_status":
        alpha_status = _get_alpha_status()
        state.assistant_response = alpha_status
        state.metadata["capability_used"] = "alpha_status"

    elif intent == "multi_intent_report_email":
        status = _get_system_status()
        state.assistant_response = (
            f"Here's the system report:\n\n"
            f"{status.get('detail', 'All systems operational')}\n\n"
            "Who should I email this to? I have rayscentro@yahoo.com on file."
        )
        state.metadata["capability_used"] = "multi_intent_report_email"
        state.metadata["intents_executed"] = ["system_status"]
        state.slot_fill_target = "email_recipient"

    else:
        # General advisory fallback
        state.assistant_response = (
            "I can help with system status, client counts, scheduling, "
            "email, or operational questions. What do you need?"
        )
        state.metadata["capability_used"] = "general_advisory"

    return state


def _compose_response(state: AgentState) -> AgentState:
    """Compose the final executive response."""
    # Update active context with what we just handled
    if state.intent:
        update_active_context(AGENT_ID, "last_intent", state.intent, ttl=600)
    if state.assistant_response:
        update_active_context(AGENT_ID, "last_response_preview", state.assistant_response[:100], ttl=600)
    return state


# ─── Capability Helpers ─────────────────────────────────────

def _get_client_count() -> int:
    """Read live client count from Supabase or local registry."""
    try:
        registry_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "data", "operations", "nexus_process_registry.json"
        )
        with open(registry_path) as f:
            data = json.load(f)
        # Count processes marked as "client"
        clients = [p for p in data if p.get("type") == "client" or p.get("category") == "client"]
        return len(clients) if clients else 0
    except Exception:
        return 0


def _get_system_status() -> Dict[str, str]:
    """Read live system status from process registry and runtime files."""
    try:
        registry_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "data", "operations", "nexus_process_registry.json"
        )
        with open(registry_path) as f:
            data = json.load(f)
        running = [p for p in data if p.get("status") == "running"]
        total = len(data)
        return {
            "working": f"{len(running)}/{total} processes active",
            "needs_attention": "",
            "detail": "\n".join(f"- {p.get('name', 'unknown')}: {p.get('status', 'unknown')}" for p in running[:10]),
        }
    except Exception as e:
        return {"working": "Unable to read process registry", "needs_attention": str(e), "detail": ""}


def _get_failure_report() -> Dict[str, str]:
    """Read today's failures from runtime logs."""
    try:
        heartbeat_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "reports", "runtime", "nexus_active_operator_heartbeat_latest.json"
        )
        with open(heartbeat_path) as f:
            data = json.load(f)
        failures = data.get("failures", [])
        if not failures:
            return {"working": "No failures recorded today", "needs_attention": "", "detail": ""}
        return {
            "working": f"{len(failures)} failures today",
            "needs_attention": "\n".join(f"- {f.get('description', 'unknown')}" for f in failures[:5]),
            "detail": json.dumps(failures[:5], indent=2),
        }
    except Exception as e:
        return {"working": "Unable to read failure log", "needs_attention": str(e), "detail": ""}


def _get_alpha_status() -> str:
    """Read Alpha's current status."""
    try:
        status_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "data", "runtime", "alpha_telegram_status.json"
        )
        with open(status_path) as f:
            data = json.load(f)
        state = data.get("State", "unknown")
        mission = data.get("current_mission", "none")
        last_msg = data.get("last_incoming_message", "never")
        return (
            f"Alpha status: {state}\n"
            f"Current mission: {mission}\n"
            f"Last incoming: {last_msg}"
        )
    except Exception:
        return "Alpha status unavailable"


# ─── Graph Builder ──────────────────────────────────────────

def build_hermes_graph() -> GraphAdapter:
    """Build and compile the Hermes LangGraph."""
    graph = GraphAdapter(agent_id=AGENT_ID)
    graph.add_node("classify_intent", _classify_intent_node)
    graph.add_node("resolve_context", _resolve_context)
    graph.add_node("route_to_capability", _route_to_capability)
    graph.add_node("execute_capability", _execute_capability)
    graph.add_node("compose_response", _compose_response)

    graph.add_edge("classify_intent", "resolve_context")
    graph.add_edge("resolve_context", "route_to_capability")
    graph.add_edge("route_to_capability", "execute_capability")
    graph.add_edge("execute_capability", "compose_response")

    graph.set_entry_point("classify_intent")
    graph.set_finish_point("compose_response")
    return graph.compile()


# ─── Singleton Instances ────────────────────────────────────

_graph: GraphAdapter | None = None
_capabilities: CapabilityRegistry | None = None
_otel: OtelAdapter | None = None


def get_hermes_graph() -> GraphAdapter:
    global _graph
    if _graph is None:
        _graph = build_hermes_graph()
    return _graph


def get_hermes_capabilities() -> CapabilityRegistry:
    global _capabilities
    if _capabilities is None:
        _capabilities = CapabilityRegistry(AGENT_ID)
        # Register standard capabilities
        _capabilities.register("get_client_count", "Get live client count", _get_client_count)
        _capabilities.register("client_acquisition_advisory", "Client acquisition advice", lambda: None)
        _capabilities.register("send_email", "Send email to recipient", lambda: None, requires_approval=True)
        _capabilities.register("schedule_report", "Schedule a report", lambda: None, requires_approval=True)
        _capabilities.register("create_opencode_prompt", "Create OpenCode prompt", lambda: None)
        _capabilities.register("system_status", "System status report", _get_system_status)
        _capabilities.register("failure_report", "Today's failure report", _get_failure_report)
        _capabilities.register("alpha_status", "Alpha agent status", _get_alpha_status)
    return _capabilities


def get_hermes_otel() -> OtelAdapter:
    global _otel
    if _otel is None:
        _otel = OtelAdapter(AGENT_ID)
    return _otel
