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
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from nexus_agent_platform.adapters.graph_adapter import GraphAdapter
from nexus_agent_platform.adapters.otel_adapter import OtelAdapter
from nexus_agent_platform.state import AgentState
from nexus_agent_platform.capabilities.registry import CapabilityRegistry
from nexus_agent_platform.context.resolver import get_active_context, update_active_context
from nexus_agent_platform.reports.ceo_formatter import format_ceo_report
from nexus_agent_platform.runtime.paths import get_nexus_repo_root

log = logging.getLogger(__name__)

AGENT_ID = "hermes"

SOUL = """You are Nexus Hermes — the internal operator and chief-of-staff.
You manage operations, coordinate across tools, and surface only
actionable information to Ray.  You speak in plain language with
executive clarity.  You do NOT give external-facing advice to
clients — you run the business.  Safety boundaries are enforced
by the capability registry and blocked-action guard."""


def _store_report_context(state: AgentState, report_type: str, result: Dict[str, Any]) -> None:
    """Store a typed report context for follow-up scheduling."""
    from nexus_agent_platform.context.resolver import update_active_context
    context_obj = {
        "context_id": state.mission_id or state.user_message[:50],
        "context_type": "report",
        "report_definition_id": report_type,
        "capability_id": report_type,
        "semantic_definition_id": f"{report_type}@v1",
        "normalized_result": result,
        "rendered_format": state.assistant_response or "",
        "source_mission_id": state.mission_id,
        "agent": AGENT_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "ttl": 900,
    }
    update_active_context(AGENT_ID, "last_report", context_obj, ttl=900)


def _resolve_time_expression(text: str) -> Optional[Dict[str, Any]]:
    """Parse 'in five minutes', 'tomorrow at 8am', etc."""
    lower = text.lower()
    now = datetime.now(timezone.utc)

    if "tomorrow" in lower:
        return {
            "delay_minutes": 1440,
            "timezone": "America/Phoenix",
            "display": "tomorrow",
            "scheduled_time": (now.replace(hour=8, minute=0, second=0, microsecond=0) + timedelta(days=1)).isoformat(),
        }

    in_match = re.search(r"in\s+(\d+|\w+)\s+(\w+)", lower)
    if in_match:
        number_word = in_match.group(1)
        unit = in_match.group(2)
        word_map = {
            "five": 5, "ten": 10, "fifteen": 15,
            "thirty": 30, "sixty": 60, "an": 1, "one": 1,
            "two": 2, "three": 3, "four": 4, "six": 6,
            "seven": 7, "eight": 8, "nine": 9,
        }
        minutes = int(number_word) if number_word.isdigit() else word_map.get(number_word)
        if minutes and unit in ("minutes", "minute", "mins", "min"):
            return {
                "delay_minutes": minutes,
                "timezone": "America/Phoenix",
                "display": f"in {minutes} minutes",
                "scheduled_time": (now + timedelta(minutes=minutes)).isoformat(),
            }

    return None


# ─── Intent Classification ──────────────────────────────────

_INTENT_PATTERNS = {
    # Multi-intent patterns MUST come before single-intent patterns
    "multi_intent_report_email": r"\b(show\s+.*report.*email|report\s+and\s+email|email.*report)\b",
    "greeting": r"\b(hello|hi|good\s+(morning|afternoon|evening)|hey|greetings)\b",
    "current_time": r"\b(what\s+time|current\s+time|time\s+is\s+it|clock)\b",
    "client_count": r"\b(how\s+many\s+clients|client\s+count|number\s+of\s+clients)\b",
    "client_acquisition": r"\b(how\s+can\s+we\s+get\s+more\s+clients|get\s+more\s+clients|acquire\s+clients|find\s+clients|new\s+clients)\b",
    "send_email": r"\b(send\s+an?\s+email|email\s+to|email\s+ray|send\s+mail)\b",
    "schedule_report": r"\b(run\s+(this|the)\s+(same\s+)?report\s+(tomorrow|in\s+\w+|daily|again)|schedule\s+(a\s+)?report)\b",
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


# ─── Graph Node Functions (Conversational Front Brain) ───────

def _front_brain_classify_node(state: AgentState) -> AgentState:
    """LLM-powered front brain classification — determines mode and capability."""
    from nexus_agent_platform.agents.front_brain import classify_message, resolve_references

    active = state.active_context or {}
    decision = classify_message(state.user_message, active)

    state.intent = decision["mode"]
    state.metadata["front_brain_mode"] = decision["mode"]
    state.metadata["front_brain_capability"] = decision.get("capability")
    state.metadata["front_brain_confidence"] = decision.get("confidence", 0.0)
    state.metadata["front_brain_reason"] = decision.get("reason", "")

    # Resolve references in the user message
    resolved = resolve_references(state.user_message, active)
    if resolved != state.user_message:
        state.metadata["resolved_message"] = resolved

    return state


def _resolve_context_enhanced(state: AgentState) -> AgentState:
    """Resolve active context, follow-ups, numbered references, and slot filling."""
    from nexus_agent_platform.agents.front_brain import resolve_references
    from nexus_agent_platform.context.resolver import get_active_context

    active = get_active_context(AGENT_ID)
    state.active_context = active

    # Detect follow-up references
    lower = state.user_message.lower()
    if any(w in lower for w in ["that report", "this report", "the same", "same report", "tomorrow"]):
        if "last_report" in active:
            state.context["prior_report"] = active["last_report"]
            state.metadata["context_resolved"] = "prior_report"

    # Detect "number N" references
    import re
    num_match = re.search(r'\b(?:number|option|#)\s*(\d+)|(?:the\s+)?(second|third|first|2nd|3rd|1st)\b', lower)
    if num_match:
        from nexus_agent_platform.agents.front_brain import extract_numbered_options
        numbered = active.get("numbered_options", {})
        if numbered:
            state.metadata["numbered_reference"] = True
            state.context["numbered_options"] = numbered

    # Detect "do it" / "run it" references
    if re.search(r'\b(do|run|schedule|execute)\s+(it|that|this)\b', lower):
        last_report = active.get("last_report")
        if last_report:
            state.context["prior_report"] = last_report
            state.metadata["context_resolved"] = "prior_report"

    return state


def _route_by_mode(state: AgentState) -> AgentState:
    """Route based on front-brain mode classification."""
    mode = state.intent or "conversation"
    capability = state.metadata.get("front_brain_capability")

    state.metadata["routed_mode"] = mode
    state.metadata["routed_capability"] = capability

    return state


def _execute_by_mode(state: AgentState) -> AgentState:
    """Execute based on the classified mode."""
    from nexus_agent_platform.agents.front_brain import (
        generate_conversation_response,
        generate_advisory_response,
        execute_operational_read,
        synthesize_operational_response,
        update_active_context_for_hermes,
        CERTIFIED_ACTIONS,
    )

    mode = state.intent or "conversation"
    capability = state.metadata.get("front_brain_capability")
    active = state.active_context or {}
    auth_ctx = {}
    if state.metadata.get("ray_authorized"):
        auth_ctx["is_ray"] = True
        auth_ctx["is_admin"] = True

    if mode == "conversation":
        response = generate_conversation_response(state.user_message, active)
        state.assistant_response = response
        state.metadata["capability_used"] = "conversation"
        state.metadata["model_used"] = HERMES_MODEL

    elif mode == "advisory":
        # Gather supporting data if capability is specified
        supporting_data = None
        if capability:
            read_result = execute_operational_read(capability, state.user_message, auth_ctx)
            supporting_data = read_result.get("data")

        response = generate_advisory_response(state.user_message, supporting_data, active)
        state.assistant_response = response
        state.metadata["capability_used"] = f"advisory:{capability or 'general'}"
        state.metadata["model_used"] = HERMES_MODEL
        if supporting_data:
            state.metadata["supporting_data"] = supporting_data

    elif mode == "operational_read":
        if not capability:
            state.assistant_response = "I'm not sure which data source to query. Could you be more specific?"
            state.metadata["capability_used"] = "operational_read_no_capability"
        else:
            result = execute_operational_read(capability, state.user_message, auth_ctx)
            response = synthesize_operational_response(capability, result, state.user_message)
            state.assistant_response = response
            state.metadata["capability_used"] = capability
            state.metadata["capability_result"] = result

            # Store report context for follow-up scheduling
            if result.get("status") == "ok":
                _store_report_context(state, capability, result.get("data", {}))

    elif mode == "governed_action":
        if not capability:
            state.assistant_response = "I'm not sure what action you want. Could you clarify?"
            state.metadata["capability_used"] = "governed_action_no_capability"
        elif capability in CERTIFIED_ACTIONS:
            action_info = CERTIFIED_ACTIONS[capability]
            if action_info.get("requires_confirmation"):
                state.assistant_response = (
                    f"I can {action_info['description'].lower()}.\n\n"
                    "Please confirm: should I proceed with this action?"
                )
                state.metadata["capability_used"] = capability
                state.metadata["pending_confirmation"] = True
                state.metadata["action_request"] = {
                    "capability": capability,
                    "user_message": state.user_message[:200],
                }
            else:
                state.assistant_response = f"I'll proceed with {capability.replace('_', ' ')}."
                state.metadata["capability_used"] = capability
        else:
            state.assistant_response = f"I don't have a certified action for '{capability}'."
            state.metadata["capability_used"] = "unknown_action"

    else:
        # Fallback — should never reach here
        state.assistant_response = "I'm not sure how to handle that. Could you try again?"
        state.metadata["capability_used"] = "fallback"

    # Update active context
    from nexus_agent_platform.agents.front_brain import update_active_context_for_hermes
    state.active_context = update_active_context_for_hermes(
        active,
        state.user_message,
        state.assistant_response or "",
        mode,
        capability,
        state.metadata.get("capability_result"),
    )

    return state


def _compose_response_final(state: AgentState) -> AgentState:
    """Compose the final executive response and update context."""
    from nexus_agent_platform.context.resolver import update_active_context

    # Update persistent active context
    if state.intent:
        update_active_context(AGENT_ID, "last_mode", state.intent, ttl=900)
    if state.assistant_response:
        update_active_context(AGENT_ID, "last_response_preview", state.assistant_response[:200], ttl=900)
    if state.metadata.get("front_brain_capability"):
        update_active_context(AGENT_ID, "last_capability", state.metadata["front_brain_capability"], ttl=900)

    # Merge in-memory active_context changes back to persistent store
    if state.active_context:
        for key in ["last_topic", "numbered_options", "last_report", "last_mode", "last_capability", "pending_action"]:
            if key in state.active_context:
                update_active_context(AGENT_ID, key, state.active_context[key], ttl=900)

    return state


# ─── Legacy Graph Node Functions (kept for rollback) ───────

def _classify_intent(text: str) -> str:
    lower = text.lower().strip()
    for intent, pattern in _INTENT_PATTERNS.items():
        if re.search(pattern, lower):
            return intent
    return "general_advisory"


def _classify_intent_node_legacy(state: AgentState) -> AgentState:
    """Classify the user message intent (legacy regex)."""
    state.intent = _classify_intent(state.user_message)
    state.metadata["classified_intent"] = state.intent
    return state


def _route_to_capability_legacy(state: AgentState) -> AgentState:
    """Route to the appropriate capability based on intent (legacy)."""
    intent = state.intent or "general_advisory"

    if state.metadata.get("classified_intent") == "multi_intent_report_email":
        state.metadata["multi_intent"] = True
        state.metadata["intents"] = ["system_status", "send_email"]
        state.slot_fill_target = "email_recipient"
        return state

    if intent == "send_email":
        email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', state.user_message)
        if email_match:
            state.slots["email_recipient"] = email_match.group(0)
        else:
            state.slot_fill_target = "email_recipient"

    if intent == "schedule_report":
        if "prior_report" not in state.context:
            state.slot_fill_target = "report_reference"

    if intent == "greeting":
        lower = state.user_message.lower()
        if any(w in lower for w in ["time", "what time", "clock"]):
            state.intent = "greeting_time"
            state.metadata["classified_intent"] = "greeting_time"

    return state


def _execute_capability_legacy(state: AgentState) -> AgentState:
    """Execute the selected capability (legacy path)."""
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
        counts = _get_client_count()
        if counts.get("error"):
            state.assistant_response = f"Client count query encountered an issue: {counts['error']}. Please check Supabase connectivity."
        elif counts["production_total"] == 0:
            state.assistant_response = "No production client profiles found in the GoClear tenant."
        else:
            parts = [
                f"GoClear currently has {counts['production_total']} production client profiles.",
                "",
                f"\u2022 {counts['active']} active",
                f"\u2022 {counts['onboarding']} onboarding",
            ]
            if counts["inactive"] > 0:
                parts.append(f"\u2022 {counts['inactive']} inactive")
            if counts["hidden"] > 0:
                parts.append(f"\n{counts['hidden']} profiles are hidden from client view.")
            if counts["tester_or_certification"] > 0:
                parts.append(f"\nThere are also {counts['tester_or_certification']} demo or certification profiles, which are not included in the production total.")
            state.assistant_response = "\n".join(parts)
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

    elif intent == "send_email":
        recipient = state.slots.get("email_recipient")
        if recipient:
            state.assistant_response = f"Ready to send an email to {recipient}.\n\nI need:\n- Subject line\n- Body text\n\nWhat should the email say?"
            state.metadata["capability_used"] = "send_email"
        else:
            state.assistant_response = "Who should I send the email to?"
            state.metadata["capability_used"] = "send_email"

    elif intent == "schedule_report":
        prior = state.context.get("prior_report")
        if prior:
            time_info = _resolve_time_expression(state.user_message)
            if time_info:
                from nexus_agent_platform.contracts.typed import TaskSpec
                from nexus_agent_platform.contracts.dispatcher import dispatch
                taskspec = TaskSpec(
                    operation="schedule_action", entity="report",
                    metric_definition=prior.get("report_definition_id", "system_status"),
                    filters={"report_definition": prior.get("report_definition_id", "system_status"), "execution_time": time_info["scheduled_time"], "timezone": time_info["timezone"]},
                    side_effect_requested=True, confidence=1.0,
                )
                auth_ctx = {}
                if state.metadata.get("ray_authorized"):
                    auth_ctx["is_ray"] = True
                    auth_ctx["is_admin"] = True
                result = dispatch(taskspec, authenticated_context=auth_ctx, mission_context={"mission_id": state.mission_id or ""}, trace_id=state.mission_id or "")
                if result.status == "ok":
                    state.assistant_response = f"Report scheduled successfully.\n\n\u2022 Report: {prior.get('report_definition_id', 'system_status')}\n\u2022 Time: {time_info['display']} (Phoenix timezone)"
                else:
                    state.assistant_response = f"Failed to schedule report: {result.error}"
                state.metadata["capability_used"] = "schedule_report"
                state.metadata["prior_report_resolved"] = True
            else:
                state.assistant_response = "What time should I run it? Default is 8:00 AM Phoenix time."
                state.metadata["capability_used"] = "schedule_report"
                state.metadata["prior_report_resolved"] = True
        else:
            state.assistant_response = "Which report would you like me to schedule?"
            state.metadata["capability_used"] = "schedule_report"
            state.metadata["slot_fill_needed"] = "report_reference"

    elif intent == "system_status":
        status = _get_system_status()
        state.assistant_response = format_ceo_report(headline="System Status", working=status.get("working", "All systems operational"), needs_attention=status.get("needs_attention", ""), detail=status.get("detail", ""))
        state.metadata["capability_used"] = "system_status"
        _store_report_context(state, "system_status", status)

    elif intent == "failure_report":
        failures = _get_failure_report()
        state.assistant_response = format_ceo_report(headline="Today's Failures", working=failures.get("working", "No active failures"), needs_attention=failures.get("needs_attention", ""), detail=failures.get("detail", ""))
        state.metadata["capability_used"] = "failure_report"
        _store_report_context(state, "failure_report", failures)

    elif intent == "alpha_status":
        state.assistant_response = _get_alpha_status()
        state.metadata["capability_used"] = "alpha_status"

    elif intent == "multi_intent_report_email":
        status = _get_system_status()
        state.assistant_response = f"Here's the system report:\n\n{status.get('detail', 'All systems operational')}\n\nWho should I email this to?"
        state.metadata["capability_used"] = "multi_intent_report_email"
        state.slot_fill_target = "email_recipient"

    else:
        state.assistant_response = "I can help with system status, client counts, scheduling, email, or operational questions. What do you need?"
        state.metadata["capability_used"] = "general_advisory"

    return state


# Backward-compatible aliases for tests and external callers
_execute_capability = _execute_capability_legacy
_route_to_capability = _route_to_capability_legacy
_classify_intent_node = _classify_intent_node_legacy


# ─── Capability Helpers ─────────────────────────────────────

# Production tenant — matches Supabase tenant_id for GoClear production clients
_PRODUCTION_TENANT = "goclear"

# Demo/certification tenant prefixes to exclude from production counts
_NON_PRODUCTION_TENANT_PREFIXES = ("tenant_demo_", "tenant-cert-")

# Sources that indicate tester or synthetic records
_TESTER_SOURCES = ("tester_invitation", "static_import", "synthetic_certification")


def _supabase_client():
    """Return a requests session configured for Supabase REST API, or None."""
    try:
        import requests as _req
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            return None
        session = _req.Session()
        session.headers.update({
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Prefer": "count=exact",
        })
        session._supabase_url = url.rstrip("/")
        return session
    except Exception:
        return None


def _get_client_count() -> dict:
    """Query Supabase client_profiles for authoritative production counts.

    Returns a structured dict with production metrics. Never reads the
    process registry. No PII is included in the response.
    """
    empty = {
        "production_total": 0, "active": 0, "onboarding": 0, "inactive": 0,
        "hidden": 0, "tester_or_certification": 0, "all_profiles": 0,
        "tenant": _PRODUCTION_TENANT, "retrieved_at": "", "error": None,
    }
    try:
        from zoneinfo import ZoneInfo
        empty["retrieved_at"] = datetime.now(ZoneInfo("America/Phoenix")).strftime("%I:%M %p MT")

        session = _supabase_client()
        if session is None:
            empty["error"] = "Supabase credentials not configured"
            return empty

        resp = session.get(
            f"{session._supabase_url}/rest/v1/client_profiles",
            params={"select": "tenant_id,status,client_visible,source"},
            timeout=10,
        )
        if not resp.ok:
            empty["error"] = f"Supabase query failed: {resp.status_code}"
            return empty

        rows = resp.json()
        empty["all_profiles"] = len(rows)

        # Classify each row
        production = []
        tester_or_cert = 0
        for row in rows:
            tenant = row.get("tenant_id", "")
            source = row.get("source", "")

            # Exclude non-production tenants
            if tenant != _PRODUCTION_TENANT:
                if any(tenant.startswith(p) for p in _NON_PRODUCTION_TENANT_PREFIXES):
                    tester_or_cert += 1
                continue

            # Production tenant — check if tester/synthetic
            if source in _TESTER_SOURCES:
                tester_or_cert += 1
                continue

            production.append(row)

        # Group production profiles by status
        active = 0
        onboarding = 0
        inactive = 0
        hidden = 0
        for row in production:
            status = (row.get("status") or "").lower()
            if status == "active":
                active += 1
            elif status == "onboarding":
                onboarding += 1
            else:
                inactive += 1
            if not row.get("client_visible", True):
                hidden += 1

        empty.update({
            "production_total": len(production),
            "active": active,
            "onboarding": onboarding,
            "inactive": inactive,
            "hidden": hidden,
            "tester_or_certification": tester_or_cert,
        })
        return empty

    except Exception as exc:
        empty["error"] = str(exc)
        return empty


def _get_system_status() -> Dict[str, str]:
    """Read live system status from process registry and runtime files."""
    try:
        registry_path = get_nexus_repo_root() / "data" / "operations" / "nexus_process_registry.json"
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
        heartbeat_path = get_nexus_repo_root() / "reports" / "runtime" / "nexus_active_operator_heartbeat_latest.json"
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
        status_path = get_nexus_repo_root() / "data" / "runtime" / "alpha_telegram_status.json"
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


def _get_process_status() -> Dict[str, Any]:
    """Query Supabase for process definitions and runs status."""
    try:
        client = _supabase_client()
        if not client:
            return {"status": "unavailable", "error": "Supabase not configured"}

        defs = client.table("nexus_process_definitions").select(
            "id,name,status,schedule,created_at"
        ).execute()
        runs = client.table("nexus_process_runs").select(
            "id,definition_id,status,last_run_at,error_message"
        ).order("last_run_at", desc=True).limit(40).execute()

        definitions = defs.data or []
        run_list = runs.data or []

        running_runs = [r for r in run_list if r.get("status") == "RUNNING"]
        completed_runs = [r for r in run_list if r.get("status") == "COMPLETED"]
        failed_runs = [r for r in run_list if r.get("status") in ("FAILED", "BLOCKED", "TIMED_OUT", "CANCELLED", "PARTIAL")]

        enabled_defs = [d for d in definitions if d.get("status") == "enabled"]
        disabled_defs = [d for d in definitions if d.get("status") != "enabled"]

        return {
            "status": "ok",
            "definitions": {
                "total": len(definitions),
                "enabled": len(enabled_defs),
                "disabled": len(disabled_defs),
                "items": [
                    {"id": d.get("id"), "name": d.get("name"), "status": d.get("status"), "schedule": d.get("schedule")}
                    for d in definitions[:10]
                ],
            },
            "runs": {
                "total": len(run_list),
                "running": len(running_runs),
                "completed": len(completed_runs),
                "failed": len(failed_runs),
                "recent": [
                    {
                        "id": r.get("id"),
                        "definition_id": r.get("definition_id"),
                        "status": r.get("status"),
                        "last_run_at": r.get("last_run_at"),
                        "error": r.get("error_message"),
                    }
                    for r in run_list[:10]
                ],
            },
        }
    except Exception as exc:
        return {"status": "unavailable", "error": str(exc)}


def _get_process_failures() -> Dict[str, Any]:
    """Query Supabase for failed process runs in the last 24 hours."""
    try:
        client = _supabase_client()
        if not client:
            return {"status": "unavailable", "error": "Supabase not configured"}

        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

        runs = client.table("nexus_process_runs").select(
            "id,definition_id,status,last_run_at,error_message,duration_ms"
        ).in_(
            "status", ["FAILED", "BLOCKED", "TIMED_OUT", "CANCELLED", "PARTIAL"]
        ).gte("last_run_at", cutoff).order("last_run_at", desc=True).limit(30).execute()

        failures = runs.data or []

        by_status = {}
        for f in failures:
            s = f.get("status", "unknown")
            by_status[s] = by_status.get(s, 0) + 1

        return {
            "status": "ok",
            "period": "last_24_hours",
            "total": len(failures),
            "by_status": by_status,
            "failures": [
                {
                    "id": f.get("id"),
                    "definition_id": f.get("definition_id"),
                    "status": f.get("status"),
                    "last_run_at": f.get("last_run_at"),
                    "error": f.get("error_message"),
                    "duration_ms": f.get("duration_ms"),
                }
                for f in failures[:10]
            ],
        }
    except Exception as exc:
        return {"status": "unavailable", "error": str(exc)}


def _get_research_history() -> Dict[str, Any]:
    """Query Supabase for recent research runs and results."""
    try:
        client = _supabase_client()
        if not client:
            return {"status": "unavailable", "error": "Supabase not configured"}

        runs = client.table("nexus_research_runs").select(
            "id,query,status,category,created_at,completed_at"
        ).order("created_at", desc=True).limit(25).execute()

        results = client.table("nexus_research_results").select(
            "id,run_id,source,title,url,created_at"
        ).order("created_at", desc=True).limit(40).execute()

        run_list = runs.data or []
        result_list = results.data or []

        completed_runs = [r for r in run_list if r.get("status") == "completed"]
        failed_runs = [r for r in run_list if r.get("status") == "failed"]

        return {
            "status": "ok",
            "runs": {
                "total": len(run_list),
                "completed": len(completed_runs),
                "failed": len(failed_runs),
                "items": [
                    {
                        "id": r.get("id"),
                        "query": r.get("query"),
                        "status": r.get("status"),
                        "category": r.get("category"),
                        "created_at": r.get("created_at"),
                        "completed_at": r.get("completed_at"),
                    }
                    for r in run_list[:10]
                ],
            },
            "results": {
                "total": len(result_list),
                "items": [
                    {
                        "id": r.get("id"),
                        "run_id": r.get("run_id"),
                        "source": r.get("source"),
                        "title": r.get("title"),
                        "url": r.get("url"),
                        "created_at": r.get("created_at"),
                    }
                    for r in result_list[:10]
                ],
            },
        }
    except Exception as exc:
        return {"status": "unavailable", "error": str(exc)}


def _get_opportunities() -> Dict[str, Any]:
    """Query Supabase for current business opportunities."""
    try:
        client = _supabase_client()
        if not client:
            return {"status": "unavailable", "error": "Supabase not configured"}

        opps = client.table("business_opportunities").select(
            "id,title,description,status,revenue_potential,action_state,updated_at"
        ).order("updated_at", desc=True).limit(8).execute()

        opportunities = opps.data or []

        active = [o for o in opportunities if o.get("action_state") == "active"]
        reviewed = [o for o in opportunities if o.get("action_state") == "reviewed"]
        rejected = [o for o in opportunities if o.get("action_state") == "rejected"]

        return {
            "status": "ok",
            "total": len(opportunities),
            "by_state": {
                "active": len(active),
                "reviewed": len(reviewed),
                "rejected": len(rejected),
            },
            "opportunities": [
                {
                    "id": o.get("id"),
                    "title": o.get("title"),
                    "description": o.get("description"),
                    "status": o.get("status"),
                    "revenue_potential": o.get("revenue_potential"),
                    "action_state": o.get("action_state"),
                    "updated_at": o.get("updated_at"),
                }
                for o in opportunities
            ],
        }
    except Exception as exc:
        return {"status": "unavailable", "error": str(exc)}


def _get_trading_status() -> Dict[str, Any]:
    """Read current Oanda practice trading engine status."""
    try:
        status_path = get_nexus_repo_root() / "reports" / "runtime" / "oanda_practice_engine_status_latest.json"
        with open(status_path) as f:
            data = json.load(f)

        return {
            "status": "ok",
            "engine_state": data.get("engine_state", "unknown"),
            "mode": data.get("mode", "unknown"),
            "kill_switch": data.get("kill_switch", False),
            "open_positions": data.get("open_positions", []),
            "pending_orders": data.get("pending_orders", []),
            "last_signal": data.get("last_signal"),
            "practice_account": True,
        }
    except FileNotFoundError:
        return {"status": "unavailable", "error": "Trading status file not found"}
    except Exception as exc:
        return {"status": "unavailable", "error": str(exc)}


def _get_pending_approvals() -> Dict[str, Any]:
    """Read pending approvals from the review queue."""
    try:
        queue_path = get_nexus_repo_root() / "reports" / "runtime" / "ray_review_queue_latest.json"
        with open(queue_path) as f:
            data = json.load(f)

        items = data if isinstance(data, list) else data.get("items", [])
        pending = [i for i in items if i.get("status") == "pending"]

        return {
            "status": "ok",
            "total": len(items),
            "pending_count": len(pending),
            "items": [
                {
                    "id": i.get("id"),
                    "type": i.get("type"),
                    "title": i.get("title"),
                    "created_at": i.get("created_at"),
                }
                for i in pending[:10]
            ],
        }
    except FileNotFoundError:
        return {"status": "unavailable", "error": "Review queue file not found"}
    except Exception as exc:
        return {"status": "unavailable", "error": str(exc)}


# ─── Graph Builder ──────────────────────────────────────────

def build_hermes_graph() -> GraphAdapter:
    """Build and compile the Hermes LangGraph with conversational front brain."""
    graph = GraphAdapter(agent_id=AGENT_ID)

    # Conversational front brain nodes
    graph.add_node("front_brain_classify", _front_brain_classify_node)
    graph.add_node("resolve_context", _resolve_context_enhanced)
    graph.add_node("route_by_mode", _route_by_mode)
    graph.add_node("execute_by_mode", _execute_by_mode)
    graph.add_node("compose_response", _compose_response_final)

    graph.add_edge("front_brain_classify", "resolve_context")
    graph.add_edge("resolve_context", "route_by_mode")
    graph.add_edge("route_by_mode", "execute_by_mode")
    graph.add_edge("execute_by_mode", "compose_response")

    graph.set_entry_point("front_brain_classify")
    graph.set_finish_point("compose_response")
    return graph.compile()


def build_legacy_graph() -> GraphAdapter:
    """Build the legacy regex-based graph for rollback."""
    graph = GraphAdapter(agent_id=AGENT_ID)
    graph.add_node("classify_intent", _classify_intent_node_legacy)
    graph.add_node("resolve_context", _resolve_context_enhanced)
    graph.add_node("route_to_capability", _route_to_capability_legacy)
    graph.add_node("execute_capability", _execute_capability_legacy)
    graph.add_node("compose_response", _compose_response_final)

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


def _front_brain_enabled() -> bool:
    """Check if the conversational front brain is enabled."""
    return os.getenv("NEXUS_HERMES_CONVERSATIONAL_FRONT_BRAIN_ENABLED", "").lower() == "true"


def get_hermes_graph() -> GraphAdapter:
    global _graph
    if _graph is None:
        if _front_brain_enabled():
            _graph = build_hermes_graph()
            log.info("Hermes graph: conversational front brain enabled")
        else:
            _graph = build_legacy_graph()
            log.info("Hermes graph: legacy regex router")
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
        # New certified capabilities
        _capabilities.register("process_status", "Process definitions and runs", _get_process_status)
        _capabilities.register("process_failures", "Failed process runs", _get_process_failures)
        _capabilities.register("research_history", "Research runs and results", _get_research_history)
        _capabilities.register("opportunities", "Business opportunities", _get_opportunities)
        _capabilities.register("trading_status", "Oanda practice trading status", _get_trading_status)
        _capabilities.register("pending_approvals", "Items awaiting approval", _get_pending_approvals)
    return _capabilities


def get_hermes_otel() -> OtelAdapter:
    global _otel
    if _otel is None:
        _otel = OtelAdapter(AGENT_ID)
    return _otel
