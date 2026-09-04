"""General parent-goal continuation contracts for the Nexus Active Operator.

This is a pure decision layer. It does not execute providers, mutate external
systems, or create a scheduler. Existing runners supply evidence and perform
the bounded action selected by these contracts.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Iterable


TERMINAL_STATES = {"GOAL_COMPLETED", "GOAL_INVALIDATED_BY_EVIDENCE", "GOAL_SUPERSEDED", "GOAL_DEFERRED_BY_EXPLICIT_PRIORITY_DECISION", "TRUE_EXTERNAL_BLOCKER", "SAFETY_BLOCKED", "REQUIRES_RAY_APPROVAL", "REQUIRES_HUMAN_ORIGIN_EVENT", "TECHNICALLY_UNSOLVABLE_WITH_CURRENT_AUTHORITY"}
FAILURE_CLASSES = {"PROVIDER_UNAVAILABLE", "ENDPOINT_BLOCKED", "AUTH_RUNTIME_MISMATCH", "MISSING_CREDENTIAL", "RATE_LIMIT", "BAD_CONFIGURATION", "NETWORK_PATH_FAILURE", "DATA_NOT_AVAILABLE", "WEBSITE_INTERACTIVE_ONLY", "BROWSER_REQUIRED", "API_REQUIRED", "MCP_REQUIRED", "CLI_REQUIRED", "REMOTE_WORKER_REQUIRED", "CAPABILITY_GAP", "DEPENDENCY_MISSING", "FORMAT_CHANGED", "TEMPORARY_PROVIDER_ERROR", "PAID_SERVICE_REQUIRED", "LEGAL_TERMS_RESTRICTION", "SAFETY_BLOCKED"}
RESOLUTION_LADDER = ("REUSE_PREVIOUS_SUCCESSFUL_PATH", "CHECK_CONFIG_ENVIRONMENT", "EXISTING_CODE", "EXISTING_CREDENTIAL_CONTROL", "CLI", "API", "MCP", "PUBLIC_WEB", "ORACLE_BROWSER", "EXISTING_REMOTE_WORKER", "MODAL_CPU", "RESEARCH_ALTERNATIVE_PROVIDER", "GITHUB_OPEN_SOURCE_RESEARCH", "BUILD_OR_ADAPT_CONNECTOR", "REROUTE_OBJECTIVE", "RAY_ONLY_TRUE_BOUNDARY")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:24]


@dataclass(frozen=True)
class ParentGoal:
    goal_id: str
    statement: str
    success_criteria: tuple[str, ...]
    owner: str = "NEXUS"
    priority: str = "P2"
    authority_envelope: str = "INTERNAL_SAFE"
    status: str = "ACTIVE"
    active_workstreams: tuple[str, ...] = ()
    current_evidence: tuple[str, ...] = ()
    missing_criteria: tuple[str, ...] = ()
    failed_paths: tuple[str, ...] = ()
    candidate_next_paths: tuple[str, ...] = ()
    last_progress: str | None = None
    next_review: str | None = None


def build_goal(goal_id: str, statement: str, success_criteria: Iterable[str], *, owner: str = "NEXUS", priority: str = "P2", authority_envelope: str = "INTERNAL_SAFE", active_workstreams: Iterable[str] = (), candidate_next_paths: Iterable[str] = ()) -> dict[str, Any]:
    goal = ParentGoal(goal_id, statement, tuple(success_criteria), owner, priority, authority_envelope, active_workstreams=tuple(active_workstreams), candidate_next_paths=tuple(candidate_next_paths), next_review=_now())
    return {**asdict(goal), "schema_version": "nexus.parent-goal.v1", "created_at": _now(), "updated_at": _now()}


def classify_path_failure(result: dict[str, Any]) -> dict[str, Any]:
    raw = " ".join(str(result.get(key, "")) for key in ("error", "reason", "status", "failure_class")).lower()
    if result.get("failure_class") in FAILURE_CLASSES:
        failure_class = result["failure_class"]
    elif any(term in raw for term in ("rate", "429", "throttle")):
        failure_class = "RATE_LIMIT"
    elif any(term in raw for term in ("credential", "401", "403", "auth")):
        failure_class = "AUTH_RUNTIME_MISMATCH"
    elif any(term in raw for term in ("timeout", "connection", "network")):
        failure_class = "NETWORK_PATH_FAILURE"
    elif any(term in raw for term in ("not found", "missing", "unavailable", "no data")):
        failure_class = "DATA_NOT_AVAILABLE"
    else:
        failure_class = "CAPABILITY_GAP"
    return {"failure_class": failure_class, "failed_path": result.get("path") or result.get("provider") or "UNKNOWN", "evidence": result.get("evidence", result.get("error", "UNKNOWN")), "retryability": "BOUNDED" if failure_class not in {"SAFETY_BLOCKED", "LEGAL_TERMS_RESTRICTION"} else "NONE", "known_alternatives": list(result.get("known_alternatives", [])), "classified_at": _now()}


def evaluate_parent_goal(goal: dict[str, Any], evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = evidence or {}
    criteria = list(goal.get("success_criteria", []))
    satisfied = set(evidence.get("satisfied_criteria", []))
    missing = [criterion for criterion in criteria if criterion not in satisfied]
    existing_status = str(goal.get("status", "ACTIVE"))
    if existing_status in TERMINAL_STATES:
        status = existing_status
    elif not missing and criteria:
        status = "GOAL_COMPLETED"
    else:
        status = "ACTIVE"
    return {**goal, "status": status, "current_evidence": list(evidence.get("current_evidence", goal.get("current_evidence", []))), "missing_criteria": missing, "last_progress": evidence.get("last_progress", goal.get("last_progress")), "updated_at": _now()}


def select_next_safe_action(goal: dict[str, Any], *, failure: dict[str, Any] | None = None, attempted_paths: Iterable[str] = ()) -> dict[str, Any]:
    attempted = set(attempted_paths)
    if goal.get("status") in TERMINAL_STATES:
        return {"action": "VERIFY_TERMINAL_STATE", "owner": "NEXUS", "continue_parent": False}
    if failure:
        failure = classify_path_failure(failure) if "failure_class" not in failure else failure
        for path in goal.get("candidate_next_paths", RESOLUTION_LADDER):
            if path not in attempted and path != failure.get("failed_path"):
                return {"action": path, "owner": "NEXUS", "continue_parent": True, "failure": failure, "bounded": True}
        return {"action": "REROUTE_OBJECTIVE", "owner": "NEXUS", "continue_parent": True, "failure": failure, "bounded": True}
    return {"action": (goal.get("candidate_next_paths") or list(RESOLUTION_LADDER))[0], "owner": "NEXUS", "continue_parent": True, "bounded": True}


def should_continue(goal: dict[str, Any], *, evidence: dict[str, Any] | None = None, failure: dict[str, Any] | None = None, attempted_paths: Iterable[str] = ()) -> dict[str, Any]:
    evaluated = evaluate_parent_goal(goal, evidence)
    action = select_next_safe_action(evaluated, failure=failure, attempted_paths=attempted_paths)
    return {"goal": evaluated, "next_action": action, "parent_goal_complete": evaluated["status"] in TERMINAL_STATES, "report_complete_is_goal_complete": False}


def repetition_guard(attempts: Iterable[dict[str, Any]], *, max_identical: int = 2) -> dict[str, Any]:
    rows = list(attempts)
    fingerprints = [fingerprint({"path": row.get("path"), "arguments": row.get("arguments"), "result": row.get("result")}) for row in rows]
    repeated = len(fingerprints) - len(set(fingerprints))
    return {"repeated": repeated >= max_identical, "repeat_count": repeated, "action": "CHANGE_STRATEGY" if repeated >= max_identical else "CONTINUE_BOUNDED", "attempt_fingerprints": fingerprints}


def active_objective_portfolio() -> list[dict[str, Any]]:
    return [{"goal_id": goal_id, "domain": domain, "status": "ACTIVE", "owner": "NEXUS", "priority": priority, "authority": "INTERNAL_SAFE"} for goal_id, domain, priority in (("trading.real_data", "Trading real-data completion", "P1"), ("research.company_intelligence", "Research intelligence expansion", "P1"), ("portal.client_beta", "Client portal advancement", "P2"), ("portal.admin_control_center", "Admin portal advancement", "P2"), ("goclear.example_campaign", "Internal GoClear campaign/video", "P2"), ("systems.modal_verification", "Modal capability verification", "P2"), ("systems.oracle_browser", "Oracle browser verification", "P2"))]


def next_work_for_active_goal(goal: dict[str, Any], *, work_item_id: str, question: str,
                              department: str = "RESEARCH", action: str = "research.refresh") -> dict[str, Any]:
    """Materialize one bounded, idempotent child action for an open parent goal.

    This remains a planning contract: the canonical Active Operator owns queue
    persistence and execution.  Keeping the contract here makes empty-queue
    continuation reusable by departments instead of encoding a Trading-only
    exception in the supervisor.
    """
    if str(goal.get("status", "ACTIVE")) in TERMINAL_STATES:
        return {"dispatch": "SKIP_TERMINAL_GOAL", "continue_parent": False, "goal_id": goal.get("goal_id")}
    return {
        "dispatch": "CREATE_OR_REUSE_WORK_ORDER",
        "goal_id": goal.get("goal_id"),
        "parent_goal": goal.get("statement") or goal.get("domain"),
        "department": department,
        "owner": goal.get("owner", "NEXUS"),
        "priority": goal.get("priority", "P2"),
        "action": action,
        "work_item_id": work_item_id,
        "question": question,
        "authority": goal.get("authority_envelope", "INTERNAL_SAFE"),
        "external_side_effects": False,
        "continue_parent": True,
    }
