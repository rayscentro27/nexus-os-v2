"""Deterministic productive routing after a department work attempt."""
from __future__ import annotations

from typing import Any


def next_action_after_result(*, result: dict[str, Any], previous: dict[str, Any] | None = None,
                             alternatives_available: bool = True) -> dict[str, Any]:
    """Return a materially different bounded route for nonterminal failure.

    A failed attempt is never treated as goal failure. Human escalation is only
    selected when the result explicitly records a human-only boundary.
    """
    status = str(result.get("status") or "PARTIAL").upper()
    action = str(result.get("action") or (previous or {}).get("tool") or "unknown")
    failure = str(result.get("failure_class") or "UNKNOWN").upper()
    human_only = bool(result.get("human_action_required"))
    if human_only:
        return {"decision": "WAIT_FOR_HUMAN_ONLY_ACTION", "next_action": "WAIT_HUMAN",
                "why_human_required": str(result.get("why_human_required") or "Explicit human-only boundary recorded."),
                "resume_stage": str(result.get("resume_stage") or action), "material_delta": ["HUMAN_BOUNDARY"]}
    if action == "research.refresh" and failure in {"EVIDENCE_INSUFFICIENT", "NO_RESULTS", "QUALITY_REJECTION"}:
        return {"decision": "RESEARCH_MORE_WITH_DIFFERENT_METHOD", "next_action": "research.alternate_public",
                "material_delta": ["SOURCE_CLASS", "QUERY_STRATEGY", "TOOL"], "goal_status": "ACTIVE"}
    if alternatives_available:
        return {"decision": "DIAGNOSE_AND_CHANGE_STRATEGY", "next_action": "DIAGNOSE_REPAIR_OR_USE_ALTERNATE_PATH",
                "material_delta": ["FAILURE_DIAGNOSIS", "ALTERNATE_STRATEGY"], "goal_status": "ACTIVE"}
    return {"decision": "CREATE_BOUNDED_CROSS_DEPARTMENT_HELP", "next_action": "CROSS_DEPARTMENT_HANDOFF",
            "material_delta": ["OWNER", "CAPABILITY_PATH"], "goal_status": "ACTIVE",
            "last_attempt_status": status}
