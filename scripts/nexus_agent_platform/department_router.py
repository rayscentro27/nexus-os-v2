"""Deterministic department/loop routing for the Telegram operator surface.

Natural language may select an intent, but this module resolves only entries
present in canonical registries and delegates execution to governed WP4 loops.
Human-gate messages are handled by the separate TruthKernel route first.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

from .loops.governed_loops import run_governed_loop
from .loops.daily_system_operations import run_daily_system_loop

ROOT = Path(__file__).resolve().parents[2]
DEPARTMENT_PATH = ROOT / "data/runtime/nexus_department_registry.json"
LOOP_PATH = ROOT / "data/runtime/nexus_loop_registry_v2.json"
SKILL_PATH = ROOT / "data/runtime/nexus_skill_registry.json"
WORKER_PATH = ROOT / "data/runtime/nexus_worker_role_map.json"

INTENT_MAP: dict[str, dict[str, str]] = {
    "STATUS": {"department": "OPERATIONS", "loop": "NEXUS_DAILY_SYSTEM_OPERATIONS", "skill": "system-operations", "worker": "NEXUS_OPERATIONS_WORKER", "authority": "internal_read_only"},
    "SYSTEM_OPERATIONS": {"department": "OPERATIONS", "loop": "NEXUS_DAILY_SYSTEM_OPERATIONS", "skill": "system-operations", "worker": "NEXUS_OPERATIONS_WORKER", "authority": "internal_read_only"},
    "SYSTEM_HEALTH": {"department": "OPERATIONS", "loop": "NEXUS_SYSTEM_HEALTH_RECOVERY", "skill": "system-recovery", "worker": "NEXUS_OPERATIONS_WORKER", "authority": "internal_read_only"},
    "RESEARCH": {"department": "RESEARCH_ALPHA", "loop": "NEXUS_RESEARCH_INTELLIGENCE", "skill": "research-intelligence", "worker": "NEXUS_RESEARCH_WORKER", "authority": "read_only"},
    "REPO_INTELLIGENCE": {"department": "SYSTEM_ENGINEERING", "loop": "NEXUS_REPO_INTELLIGENCE", "skill": "repo-intelligence", "worker": "NEXUS_RESEARCH_WORKER", "authority": "internal_read_only"},
    "FUNDING_READINESS": {"department": "CREDIT_BUSINESS_FUNDING", "loop": "NEXUS_CREDIT_BUSINESS_FUNDING", "skill": "funding-readiness", "worker": "NEXUS_FUNDING_WORKER", "authority": "internal_review"},
    "RAY_REVIEW": {"department": "GOVERNANCE_REVIEW", "loop": "NEXUS_RAY_REVIEW", "skill": "ray-review", "worker": "NEXUS_REVIEW_WORKER", "authority": "human_review"},
    "WORK_ORDER": {"department": "GOVERNANCE_REVIEW", "loop": "NEXUS_RAY_REVIEW", "skill": "work-order-management", "worker": "NEXUS_REVIEW_WORKER", "authority": "human_review"},
}


def _load(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def classify_intent(text: str) -> str:
    value = re.sub(r"[?.!]+$", "", text.strip().lower())
    if re.fullmatch(r"(?:hello|hi|hey)(?: nexus)?(?:[, :\-].*)?", value) or re.fullmatch(r"(?:good morning|good afternoon|good evening)(?: nexus)?", value) or re.search(r"\bhow are you(?: today)?\b", value):
        return "CONVERSATION"
    if value in {"/status", "status", "how is nexus doing", "what is nexus status", "what's nexus status", "what is running right now", "what is the current status of nexus", "what's working right now", "what is blocked", "what needs my attention", "is active operator running", "what happened with the last loop", "what is the health of hermes"} or re.fullmatch(r"(?:what is|what's) (?:the )?(?:current )?status of nexus", value):
        return "STATE_QUERY"
    if value in {"who are you", "what can you do", "/help", "help"}:
        return "CONVERSATION"
    if re.search(r"\b(system operations|daily operations|operations check|system check|today'?s operations)\b", value) or value in {"/run system_operations", "/run daily_operations"}:
        return "SYSTEM_OPERATIONS"
    if value == "/run system_health" or re.search(r"\b(system health|health check|health recovery)\b", value):
        return "SYSTEM_HEALTH"
    if re.search(r"\b(research|look up|investigate)\b", value) and not re.search(r"\brepo", value):
        return "RESEARCH"
    if re.search(r"\b(repo|repository|git status|codebase)\b", value):
        return "REPO_INTELLIGENCE"
    if re.search(r"\b(funding readiness|funding|bankability|credit readiness)\b", value):
        return "FUNDING_READINESS"
    if re.search(r"\b(review item|ray review|needs my attention|what needs my attention)\b", value):
        return "RAY_REVIEW"
    if value.startswith(("/request ", "/work ", "create a work order", "turn this into a work order")):
        return "WORK_ORDER"
    return "UNKNOWN"


def state_query_response(text: str) -> str:
    """Produce a read-only summary from canonical program state."""
    state = _load(ROOT / "data/runtime/nexus_rebuild_program.json")
    safety = state.get("safety", {}) if isinstance(state.get("safety"), dict) else {}
    query = text.lower()
    if "who are you" in query or "what can you do" in query:
        return "I’m Nexus, the governed control-plane assistant. I can explain verified state, run approved bounded internal checks, research public topics, inspect the repository, and prepare review work. TruthKernel and Nexus remain authoritative; consequential actions stay gated."
    blocked = state.get("blocked_work_packages", [])
    active = state.get("active_work_packages", [])
    lines = ["Nexus current state", "", f"What is true now? {state.get('state', 'UNKNOWN')}.", f"What is working? Active work packages: {len(active)}; Hermes runtime and the bounded WP4 routing foundation are recorded as complete with limits.", f"What is blocked? {', '.join(blocked) if blocked else 'Nothing recorded.'}", f"What happens next? {state.get('next_action', 'Continue from the canonical checkpoint.')}", f"Do you need Ray? {'Yes for consequential authority or the outstanding Telegram E2E.' if safety.get('active_operator_paused', True) else 'No for this read-only query.'}"]
    return "\n".join(lines)


def _registry_valid(route: Mapping[str, str]) -> bool:
    loops = {x.get("loop_id") for x in _load(LOOP_PATH).get("loops", []) if isinstance(x, dict)}
    skills = {x.get("skill_id") for x in _load(SKILL_PATH).get("skills", []) if isinstance(x, dict)}
    workers = {x.get("worker_id") for x in _load(WORKER_PATH).get("workers", []) if isinstance(x, dict)}
    departments = {x.get("department_id") for x in _load(DEPARTMENT_PATH).get("departments", []) if isinstance(x, dict)}
    return route["loop"] in loops and route["skill"] in skills and route["worker"] in workers and route["department"] in departments


def resolve(text: str) -> dict[str, Any]:
    intent = classify_intent(text)
    if intent in {"CONVERSATION", "UNKNOWN", "STATE_QUERY"}:
        return {"intent_class": intent, "status": "NO_EXECUTION" if intent == "CONVERSATION" else "READ_ONLY_STATE" if intent == "STATE_QUERY" else "UNKNOWN_INTENT"}
    route = INTENT_MAP[intent]
    if not _registry_valid(route):
        return {"intent_class": intent, "status": "ROUTING_UNAVAILABLE", "error": "canonical registry mismatch"}
    return {"intent_class": intent, "status": "RESOLVED", **route}


def execute(text: str, *, input_source: str = "telegram") -> tuple[str, dict[str, Any]] | None:
    # Preserve the older, separately certified system-health process handler
    # for its exact command while natural-language health requests use WP5
    # registry routing.
    if text.strip().lower() == "/run system_health":
        return None
    resolved = resolve(text)
    # Status remains a read-model response handled by the established worker;
    # it should not launch a diagnostic process merely because it is routed to
    # the Operations department.
    if resolved.get("intent_class") == "STATE_QUERY":
        return state_query_response(text), {"route": "NEXUS_READ_ONLY_STATE", "outcome": "ANSWERED", "lane": "READ_ONLY_STATE_LANE", **resolved}
    if resolved.get("intent_class") == "CONVERSATION":
        return "Nexus is here. I’m doing well and ready to help. I can explain verified state, answer questions, or run a bounded internal check when you explicitly ask me to.", {"route": "NEXUS_CONVERSATION", "outcome": "ANSWERED", "lane": "CONVERSATIONAL_LANE", **resolved}
    if resolved["status"] == "NO_EXECUTION":
        if resolved["intent_class"] == "CONVERSATION":
            return "Nexus is here. I can report status, run bounded system checks, research public topics, inspect the repository, or prepare governed review work.", {"route": "NEXUS_CONVERSATION", "outcome": "ANSWERED", **resolved}
        return None
    if resolved["status"] != "RESOLVED":
        return "I could not resolve that request to a certified Nexus department and loop. No work was executed.", {"route": "NEXUS_ROUTING", "outcome": "BLOCKED", **resolved}
    context: dict[str, Any] = {"input_source": input_source}
    if resolved["intent_class"] == "RESEARCH":
        context["question"] = re.sub(r"\s+", " ", text).strip()[:240]
        context["live_private_searxng"] = False
    if resolved["intent_class"] == "RAY_REVIEW":
        context.update({"what_happened": "Telegram requested a bounded internal review item", "what_is_true_now": "No external action was performed", "what_happens_next": "Review item remains governed", "do_you_need_ray": True})
    if resolved["intent_class"] == "FUNDING_READINESS":
        context["subject"] = "synthetic Telegram request"
    try:
        result = (run_daily_system_loop(context) if resolved["loop"] == "NEXUS_DAILY_SYSTEM_OPERATIONS"
                  else run_governed_loop(resolved["loop"], context))
    except (OSError, ValueError, RuntimeError) as exc:
        return ("This request resolved to a Nexus route, but its governed executor is unavailable. No work was marked successful.", {"route": "NEXUS_DEPARTMENT_LOOP", "outcome": "BLOCKED", "execution_status": "FAILED", "error": type(exc).__name__, **resolved})
    capability_by_loop = {
        "NEXUS_DAILY_SYSTEM_OPERATIONS": "python.daily_system_operations",
        "NEXUS_SYSTEM_HEALTH_RECOVERY": "python.daily_system_operations",
        "NEXUS_RESEARCH_INTELLIGENCE": "searxng.research",
        "NEXUS_REPO_INTELLIGENCE": "truthkernel.authority",
        "NEXUS_CREDIT_BUSINESS_FUNDING": "truthkernel.authority",
        "NEXUS_RAY_REVIEW": "truthkernel.authority",
    }
    metadata = {"route": "NEXUS_DEPARTMENT_LOOP", "outcome": "ANSWERED" if result.final_state == "SUCCEEDED_VERIFIED" else "BLOCKED", "execution_status": result.final_state, "run_id": result.run_id, "receipt_id": result.receipt_id, "receipt_path": result.receipt_path, "capability_id": capability_by_loop.get(resolved["loop"]), "execution_target": "MAC_LOCAL" if resolved["loop"] not in {"NEXUS_RESEARCH_INTELLIGENCE"} else "HYBRID_MAC_ORACLE", "model_provider": "Nexus deterministic", "model_name": "none", **resolved}
    if result.error:
        metadata["error"] = result.error
    response = (f"{resolved['intent_class']} — {result.final_state}.\n\n"
                f"What happened? The {resolved['loop']} loop ran through {resolved['department']} / {resolved['skill']}.\n"
                f"What is true now? The result is {result.final_state}; no authority was inferred from Hermes text.\n"
                f"What happens next? Review the governed receipt: {result.receipt_path}.\n"
                f"Do you need Ray? {'Yes, for any consequential action.' if resolved['authority'] != 'internal_read_only' else 'No for this bounded read-only result.'}")
    return response, metadata
