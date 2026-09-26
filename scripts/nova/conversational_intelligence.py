"""Bounded compound-query and repeated-request intelligence for Nova.

This module is intentionally deterministic and side-effect free except for the
explicit pattern persistence helper. It does not create schedules or send
notifications.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PATTERN_PATH = ROOT / "data" / "runtime" / "nova_request_patterns.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:16]


def _time_scope(text: str) -> str:
    lowered = text.lower()
    for phrase, scope in (("last night", "LAST_NIGHT"), ("overnight", "OVERNIGHT"), ("yesterday", "YESTERDAY"), ("this morning", "THIS_MORNING"), ("today", "TODAY")):
        if phrase in lowered:
            return scope
    return "CURRENT_UNSPECIFIED"


def decompose_compound_query(raw: str) -> dict[str, Any]:
    text = " ".join(str(raw or "").split())
    lowered = text.lower()
    intents: list[dict[str, Any]] = []

    def add(domain: str, question: str, sources: list[str], truth: str = "UNKNOWN") -> None:
        intents.append({
            "intent_id": f"intent_{len(intents) + 1}", "domain": domain,
            "question": question.strip(" ,?."), "required_sources": sources,
            "status": "UNANSWERED", "result": None, "truth_class": truth,
            "unresolved_reason": None,
        })

    if re.search(r"\b(?:how did nexus run|how did .* run|overnight|last night|runtime|systems?)\b", lowered):
        add("SYSTEMS_RUNTIME", "overnight/current Nexus operational status", ["systems_health_states", "systems_incidents", "systems_services"])
    if re.search(r"\b(?:what did research find|research find|research discover|research)\b", lowered):
        add("RESEARCH", "Research findings for the requested period", ["research_runtime_states", "research_requests", "research_v2_mission_reports", "research_discovery_clusters"])
    if re.search(r"\b(?:alpha|approve|reject|research findings)\b", lowered):
        add("ALPHA", "Alpha decision related to the relevant Research findings", ["alpha_decision_receipts", "alpha_rejection_history"])
    if re.search(r"\b(?:marketing|lead|leads|campaign)\b", lowered):
        add("MARKETING", "Marketing activity and lead state", ["marketing_health", "marketing_campaigns", "marketing_leads"])
    if re.search(r"\b(?:creative|prompt architect|asset|video|design)\b", lowered):
        add("CREATIVE", "Creative work, provider state, and Prompt Architect status", ["creative_health", "creative_tasks", "creative_prompt_architect_receipts"])
    if re.search(r"\b(?:break|failed|failure|incident|down|unhealthy)\b", lowered):
        add("INCIDENTS", "Failures, incidents, and blockers", ["systems_incidents", "systems_health_states", "creative_health", "customer_service_health"])
    if re.search(r"\b(?:make any money|revenue|profit|financial|spent|cost)\b", lowered):
        add("FINANCE", "Verified revenue, cost, and net for the requested period", ["finance_truth_snapshots", "finance_revenue", "finance_cost_receipts", "finance_goal_snapshots"], "UNKNOWN_INCOMPLETE_COVERAGE")
    if re.search(r"\b(?:finish|finished|completed|complete|what moved|what happened)\b", lowered):
        add("COMPLETIONS", "Completed and attempted work", ["goals", "work_orders", "audit", "research_requests"])
    if not intents:
        add("GENERAL", text, ["executive_snapshot", "targeted_domain_retrieval"])
    return {
        "compound_query_id": "compound_" + _id((text, [x["domain"] for x in intents])),
        "raw_utterance": text,
        "time_scope": _time_scope(text),
        "intents": intents,
        "intent_count": len(intents),
        "no_lost_subquestion_policy": "Each intent must end ANSWERED, UNKNOWN, BLOCKED, NOT_APPLICABLE, or NEEDS_CLARIFICATION before synthesis.",
        "created_at": _now(),
    }


def resolve_intents(decomposition: dict[str, Any], evidence: dict[str, dict[str, Any]]) -> dict[str, Any]:
    result = dict(decomposition)
    resolved = []
    for intent in decomposition.get("intents", []):
        item = dict(intent)
        found = evidence.get(item["domain"])
        if found and found.get("status") in {"ANSWERED", "UNKNOWN", "BLOCKED", "NOT_APPLICABLE", "NEEDS_CLARIFICATION"}:
            item.update(found)
        else:
            item.update({"status": "UNKNOWN", "unresolved_reason": "No current record-backed evidence for this subquestion."})
        resolved.append(item)
    result["intents"] = resolved
    result["all_intents_closed"] = all(x.get("status") in {"ANSWERED", "UNKNOWN", "BLOCKED", "NOT_APPLICABLE", "NEEDS_CLARIFICATION"} for x in resolved)
    return result


def detect_repeated_request_pattern(occurrences: list[dict[str, Any]], *, topic: str) -> dict[str, Any]:
    sessions = {str(row.get("session_id")) for row in occurrences if row.get("session_id")}
    morning = sum(1 for row in occurrences if str(row.get("time_window", "")).upper() in {"MORNING", "AM"})
    candidate = len(occurrences) >= 3 and len(sessions) >= 3 and morning >= 2
    pattern_id = "pattern_" + _id((topic, sorted(sessions), len(occurrences)))
    return {
        "pattern_id": pattern_id, "topic": topic,
        "first_seen": min((row.get("at", "UNKNOWN") for row in occurrences), default="UNKNOWN"),
        "last_seen": max((row.get("at", "UNKNOWN") for row in occurrences), default="UNKNOWN"),
        "occurrence_count": len(occurrences), "distinct_session_count": len(sessions),
        "common_time_window": "MORNING" if morning >= 2 else "MIXED",
        "automation_candidate": candidate, "suggestion_already_made": False,
        "user_response": "PENDING_EXPLICIT_APPROVAL", "evidence": occurrences,
        "threshold": "at least 3 occurrences across 3 sessions with recurring time signal",
    }


def automation_suggestion(pattern: dict[str, Any], report_name: str = "morning executive report") -> dict[str, Any]:
    if not pattern.get("automation_candidate"):
        return {"status": "NO_SUGGESTION", "reason": "bounded recurrence threshold not met"}
    return {"status": "SUGGESTION_ONLY", "message": f"You've been checking {pattern.get('topic', 'this information')} most mornings. Would you like me to add it to your existing {report_name}?", "automation_created": False, "approval_required": True}


def persist_pattern(pattern: dict[str, Any]) -> dict[str, Any]:
    PATTERN_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        current = json.loads(PATTERN_PATH.read_text())
        if not isinstance(current, list): current = []
    except (OSError, ValueError):
        current = []
    if not any(row.get("pattern_id") == pattern.get("pattern_id") for row in current if isinstance(row, dict)):
        current.append(pattern)
        PATTERN_PATH.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n")
    return pattern
