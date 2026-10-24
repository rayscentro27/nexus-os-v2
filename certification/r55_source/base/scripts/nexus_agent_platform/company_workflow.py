"""Company Case workflow contracts over the existing Research Case Engine.

This module provides common routing/return semantics, not a second queue or case
store. Durable state remains in RESEARCH_CASE / Supabase and existing request,
result, approval, and worker records.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ROUTING_PATH = ROOT / "data/governed/nexus_company_routing_rules_v1.json"
REGISTRY_PATH = ROOT / "data/governed/nexus_department_workflow_registry_v1.json"
TERMINAL_AUTHORITY = {"RAY_APPROVAL_REQUIRED", "RAY_REVIEW_REQUIRED", "RAY_DENIAL_RECORDED",
                      "RAY_STOPPED_PROJECT", "TRUE_HUMAN_ONLY_BLOCKER",
                      "OBJECTIVE_ACHIEVED_AWAITING_RAY_ACCEPTANCE", "OBJECTIVE_ACCEPTED_BY_RAY"}
NON_TERMINAL = {"INSUFFICIENT_DATA", "NEGATIVE_TEST_RESULT", "PROVIDER_FAILURE",
    "INDICATOR_FAILED", "BUSINESS_MODEL_WEAK", "CAMPAIGN_UNDERPERFORMED",
    "SOURCE_MISSING", "AUTH_FAILURE", "NO_CURRENT_CAPABILITY", "NOT_ENOUGH_EVIDENCE",
    "DEPARTMENT_TASK_COMPLETE", "PARTIAL", "FAIL", "REJECTED", "NEEDS_MORE_RESEARCH"}
OBSERVABILITY_METRICS = {
    "LEGACY_TERMINAL_INTERCEPTS", "NON_TERMINAL_RESULTS_ROUTED", "TASK_FAILURES_RECOVERED",
    "PROVIDER_FAILURES_RECOVERED", "MISSING_DATA_ROUTED", "NEGATIVE_RESULTS_CONTINUED",
    "RAY_TERMINATIONS", "OBJECTIVES_ACCEPTED",
}


def _record_workflow_metric(metric: str, **context: Any) -> None:
    """Append a governed operational counter event; never stores provider secrets."""
    if metric not in OBSERVABILITY_METRICS:
        return
    try:
        from nexus_agent_platform.governed import persistence
        persistence.append_record("company_workflow_observability", {
            "metric": metric, "created_at": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc).isoformat(), **context,
        })
    except Exception:
        # Observability must not interrupt case continuation.
        return


def workflow_observability_counts() -> dict[str, int]:
    from nexus_agent_platform.governed import persistence
    counts = {metric: 0 for metric in sorted(OBSERVABILITY_METRICS)}
    for row in persistence.read_records("company_workflow_observability"):
        metric = str(row.get("metric") or "")
        # Pure contract probes are not runtime health evidence. Count only
        # events tied to a real case or governed Ray decision receipt.
        if metric in counts and (row.get("case_id") or row.get("approval_id")):
            counts[metric] += 1
    return counts


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def workflow_map() -> dict[str, Any]:
    return _read(REGISTRY_PATH)


def route_need(need: str, context: str = "") -> str:
    rules = _read(ROUTING_PATH).get("need_routes", {})
    key = str(need or "").upper()
    if key in rules:
        return str(rules[key].get("owner") or "RESEARCH")
    text = f"{need} {context}".casefold()
    patterns = [
        (r"auth|credential|provider failure|no current capability|integration|infrastructure|technical|browser|api", "SYSTEMS"),
        (r"cost|money|budget|roi|capital|margin|economics|fee|slippage", "FINANCE"),
        (r"creative|asset|video|image|landing page", "CREATIVE"),
        (r"campaign|customer acquisition|audience|funnel|distribution", "MARKETING"),
        (r"backtest|strategy|trading|market data", "TRADING"),
        (r"funding|grant|lender|eligibility", "CLYDE_CREDIT"),
        (r"lab|experiment|validate|canary|test", "LABS"),
    ]
    for pattern, owner in patterns:
        if re.search(pattern, text):
            return owner
    return "RESEARCH"


def build_handoff(*, case: dict[str, Any], request_id: str, to_department: str,
                  work: str, why: str, from_department: str = "COMPANY_CASE_ENGINE",
                  return_to: str | None = None, questions: list[str] | None = None,
                  expected_output: Any = None, cost_implication: Any = None,
                  ray_approval_required: bool = False) -> dict[str, Any]:
    """Create the universal envelope while keeping legacy fields at top level."""
    objective_id = case.get("originating_goal_id") or case.get("parent_goal_id") or case.get("case_id")
    known = list(case.get("findings") or []) + list(case.get("notebook_material_intelligence") or [])
    if not known:
        known = [{"objective": case.get("objective"), "originating_signal": case.get("originating_signal"),
                  "case_selection_reason": case.get("case_selection_reason") or case.get("selection_reason")}]
    results = list(case.get("department_results") or [])
    unknown = list(case.get("open_questions") or []) + list(case.get("missing_information") or [])
    target_return = str(return_to or from_department or "COMPANY_CASE_ENGINE").upper()
    actionable_items = [str(work).strip()] if str(work or "").strip() else []
    envelope = {
        "summary": str(why or work or "Company case work routed.")[:800],
        "supporting_data": known[-30:] + results[-10:],
        "what_was_learned": (case.get("findings") or case.get("notebook_material_intelligence") or [])[-10:],
        "actionable_items": actionable_items,
        "exact_instructions": str(work or ""), "next_owner": str(to_department).upper(),
        "case_id": case.get("case_id"), "objective_id": objective_id,
        "from_department": str(from_department).upper(), "to_department": str(to_department).upper(),
        "directive_id": request_id, "why_routed": why,
        "current_context": {"objective": case.get("objective"), "status": case.get("status"),
            "phase": case.get("current_phase"), "owner": case.get("next_owner")},
        "what_is_already_known": known[-30:], "what_is_not_known": unknown[-30:],
        "relevant_history": list(case.get("department_learning_history") or [])[-20:],
        "relevant_prior_results": results[-20:],
        "questions_to_answer": list(questions or [work]), "work_to_perform": work,
        "expected_output": expected_output or case.get("expected_output"),
        "success_criteria": case.get("success_criteria") or [],
        "return_to": target_return, "return_condition": "After the requested output is attached to this case, restore return_to as current owner unless another higher-priority need or Ray gate applies.",
        "cost_or_resource_implication": cost_implication,
        "ray_approval_required": bool(ray_approval_required), "status": "OPEN",
    }
    envelope["actionable_item_count"] = len(actionable_items)
    envelope["handoff_valid"] = validate_actionable_handoff(envelope)["valid"]
    return envelope


def validate_actionable_handoff(packet: dict[str, Any], *, ray: bool = False) -> dict[str, Any]:
    """Reject empty handoffs before they can become department work."""
    actions = packet.get("actionable_items") or []
    if isinstance(actions, str):
        actions = [actions] if actions.strip() else []
    missing = [name for name in ("summary", "supporting_data", "next_owner", "expected_output")
               if not packet.get(name)]
    if not actions:
        missing.append("actionable_items")
    if not packet.get("exact_instructions"):
        missing.append("exact_instructions")
    if ray:
        missing.extend(name for name in ("recommendation", "why", "decision_requested",
            "what_happens_if_approved", "what_happens_if_denied_or_changes_requested")
            if not packet.get(name))
    return {"valid": not missing, "actionable_item_count": len(actions), "missing": missing}


def result_contract(*, result: str, interpretation: str, what_changed: str,
                    why_changed: str, learned: str, recommendation: str,
                    recommended_changes: list[str], next_owner: str,
                    next_directive: str, return_to: str, ray_required: bool,
                    case_status: str, case_id: str | None = None) -> dict[str, Any]:
    action = str(next_directive or recommendation or "").strip()
    owner = str(next_owner or "").strip().upper()
    if not action:
        owner = owner or route_need(result, interpretation)
        action = f"Route {str(result or 'incomplete result')[:120]} to {owner} for the next bounded step."
    if not owner:
        owner = route_need(action, interpretation)
    result_text = f"{result} {interpretation}".upper()
    metric_context = {"case_id": case_id} if case_id else {}
    if case_id:
        _record_workflow_metric("NON_TERMINAL_RESULTS_ROUTED", result_status=str(result)[:100], **metric_context)
        if any(token in result_text for token in ("PROVIDER_FAILURE", "AUTH_FAILURE", "MISSING_CREDENTIAL")):
            _record_workflow_metric("PROVIDER_FAILURES_RECOVERED", result_status=str(result)[:100], **metric_context)
        if any(token in result_text for token in ("INSUFFICIENT_DATA", "NOT_ENOUGH_EVIDENCE", "SOURCE_MISSING")):
            _record_workflow_metric("MISSING_DATA_ROUTED", result_status=str(result)[:100], **metric_context)
        if any(token in result_text for token in ("NEGATIVE_TEST_RESULT", "NEGATIVE RESULT", "FAILED TEST")):
            _record_workflow_metric("NEGATIVE_RESULTS_CONTINUED", result_status=str(result)[:100], **metric_context)
        if any(token in result_text for token in ("DEPARTMENT_TASK_COMPLETE", "TASK FAILED", "PARTIAL")):
            _record_workflow_metric("TASK_FAILURES_RECOVERED", result_status=str(result)[:100], **metric_context)
    normalized_status = governed_case_status(case_status)
    return {"summary": str(result)[:800], "result": result,
        "ai_interpretation": interpretation, "what_changed": what_changed,
        "why_it_changed": why_changed, "what_was_learned": learned,
        "recommendation": recommendation, "recommended_changes": recommended_changes,
        "actionable_items": [action], "actionable_item_count": 1,
        "next_owner": owner, "next_directive": action,
        "return_to": return_to, "ray_decision_required": bool(ray_required),
        "case_status": normalized_status,
        "ai_can_terminate_project": False}


def governed_case_status(proposed: str, *, actor: str = "NEXUS") -> str:
    """Normalize legacy child/AI stop labels into active re-planning.

    This helper does not grant authority based on an actor string; Ray decisions
    are applied only by the approval-bound Company Case decision function.
    """
    value = str(proposed or "").upper()
    if value in {"COMPLETED", "REJECTED", "REJECTED_WITH_EVIDENCE",
            "CANCELLED", "TERMINATED", "ABANDONED", "FAILED", "FAILED_FINAL", "PARKED"}:
        return "REPLANNING"
    return value


def nonterminal_next_action(result_status: str, detail: str = "") -> dict[str, str]:
    value = str(result_status or "").upper()
    need_alias = {
        "INSUFFICIENT_DATA": "INFORMATION",
        "PROVIDER_FAILURE": "AUTHENTICATION",
        "MISSING_CREDENTIAL": "AUTHENTICATION",
        "CAPABILITY_UNAVAILABLE": "TECHNICAL_CAPABILITY",
        "SOURCE_MISSING": "INFORMATION",
        "NEGATIVE_TEST_RESULT": "BACKTEST" if re.search(r"trading|strategy|backtest", detail, re.I) else "TEST",
    }
    owner = route_need(need_alias.get(value, value), detail)
    return {"next_owner": owner,
            "next_action": detail.strip() or f"Route {value or 'incomplete result'} to {owner} for the next bounded step.",
            "parent_case_remains_active": "true"}


def audit_company_workflow_health(*, write_incident: bool = True) -> dict[str, Any]:
    """Systems functional-health check over canonical case and Research state."""
    from nexus_agent_platform.governed import persistence
    heartbeat = _read(ROOT / "data/runtime/research_heartbeat.json")
    try:
        from research.research_case_engine import _latest_cases, ACTIVE_STATES
        cases = [row for row in _latest_cases() if str(row.get("status") or "").upper() in ACTIVE_STATES]
    except Exception as exc:
        return {"status": "DEGRADED", "reason": type(exc).__name__, "incidents_created": 0}
    questions = sum(len(row.get("open_questions") or []) for row in cases)
    case_ids = sorted(str(row.get("case_id") or "") for row in cases)
    case_state_at = max((str(row.get("recorded_at") or row.get("updated_at") or row.get("created_at") or "")
                         for row in cases), default=None)
    queued = 0
    try:
        queue = json.loads((ROOT / "data/runtime/.research_work_queue.json").read_text(encoding="utf-8"))
        items = queue.get("items", []) if isinstance(queue, dict) else queue
        queued = sum(str(row.get("status") or "").upper() in {"QUEUED", "READY", "PENDING"}
                     for row in items if isinstance(row, dict))
    except (OSError, ValueError, TypeError):
        pass
    last_output = heartbeat.get("last_real_output") or heartbeat.get("last_success")
    incidents = []
    if heartbeat.get("heartbeat") == "ACTIVE" and queued == 0 and questions > 0:
        incidents.append({"condition": "QUEUE_EMPTY_WHILE_ACTIVE_CASES_EXIST",
            "root_cause": "Research work queue is not the active-case scheduler; strategic questions remain outside the legacy queue.",
            "safe_repair_attempt": "Prioritize active Company Case questions through owner continuation; do not enqueue legacy rows FIFO.",
            "next_action": "Use the canonical scheduled Company Case continuation to claim active owner work; do not duplicate it into the legacy FIFO.",
            "post_repair_validation": "Confirm a case question was advanced and its next owner/action persisted."})
    if heartbeat.get("heartbeat") == "ACTIVE" and questions and not last_output:
        incidents.append({"condition": "RESEARCH_HEARTBEAT_WITHOUT_OUTPUT",
            "root_cause": "Heartbeat lacks a useful completion timestamp while active questions remain.",
            "safe_repair_attempt": "Inspect last worker receipt and resume one bounded active-case continuation.",
            "next_action": "Resume the active case through the canonical scheduled continuation and verify a result plus next owner/action.",
            "post_repair_validation": "Verify a useful result and next action in the same case."})
    created = []
    prior = persistence.read_records("systems_incidents")
    for item in incidents:
        key = "company-workflow:" + item["condition"]
        existing = next((row for row in reversed(prior) if row.get("incident_key") == key
            and str(row.get("status") or "OPEN").upper() == "OPEN"), None)
        row = {**(existing or {}), "incident_id": (existing or {}).get("incident_id") or persistence.new_id("sysinc"), "incident_key": key,
            "incident_type": "COMPANY_WORKFLOW_FUNCTIONAL_HEALTH", "status": "OPEN",
            "owner": "SYSTEMS", "detected_by": "SYSTEM_HEALTH_LOOP",
            "affected_workflows": ["RESEARCH", "COMPANY_CASE_CONTINUATION"],
            "active_company_cases": len(cases), "open_case_questions": questions,
            "active_queue_items": queued, "last_research_output": last_output,
            "next_action": item.get("next_action") or item.get("safe_repair_attempt"),
            **item, "created_at": (existing or {}).get("created_at") or __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            "last_checked": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()}
        if write_incident:
            persistence.append_record("systems_incidents", row)
        created.append({**row, "refreshed_existing": bool(existing)})
    return {"status": "INCIDENT" if incidents else "HEALTHY", "daemon_state": heartbeat.get("heartbeat"),
        "authoritative_case_source": "research_case_engine._latest_cases via governed research_runtime_states + Supabase research_proactive_memory",
        "health_monitor_case_source": "research_case_engine._latest_cases",
        "case_state_as_of": case_state_at, "active_case_ids": case_ids,
        "last_useful_completion": last_output, "active_company_cases": len(cases),
        "active_cases_with_open_questions": sum(bool(row.get("open_questions")) for row in cases),
        "open_research_questions": questions, "active_valid_queue_items": queued,
        "incidents": incidents, "incident_records_created": created}
