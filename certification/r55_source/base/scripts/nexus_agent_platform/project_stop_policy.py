"""Ray-only authority for stopping a parent Nexus project or company goal.

Agents may reject child attempts, artifacts, sources, and hypotheses. A parent
project stop requires an explicit Ray decision reference; child failure alone
always returns a continuation action.
"""
from __future__ import annotations

from typing import Any

PROJECT_STOP_STATES = {"REJECTED", "REJECTED_WITH_EVIDENCE", "CANCELLED", "TERMINATED",
                       "ABANDONED", "FAILED", "FAILED_FINAL", "COMPLETED", "COMPLETE",
                       "PARKED", "CLOSED"}
PARENT_COLLECTIONS = {"goals", "opportunities", "business_ideas", "marketing_projects",
                      "creative_campaigns", "research_special_projects", "upgrade_requests",
                      "research_cases"}
_DECISIONS = {"REJECTED": "REJECT", "REJECTED_WITH_EVIDENCE": "REJECT",
              "CANCELLED": "CANCEL", "TERMINATED": "TERMINATE",
              "ABANDONED": "STOP", "FAILED": "STOP", "FAILED_FINAL": "STOP",
              "COMPLETED": "STOP", "COMPLETE": "STOP", "PARKED": "STOP", "CLOSED": "STOP"}


def ray_stop_authorized(*, actor: str, approval_id: str | None, decision: str | None,
                        project_id: str | None = None) -> bool:
    identity = " ".join(str(actor or "").strip().upper().replace("_", " ").split())
    decision_value = str(decision or "").strip().upper()
    if identity not in {"RAY", "RAY DAVIS", "RAYMOND DAVIS"} or not approval_id or not project_id or \
            decision_value not in {"STOP", "REJECT", "TERMINATE", "CANCEL"}:
        return False
    # A caller-supplied actor label is not authority. Require the existing
    # governed approval ledger to show Ray approved this exact project stop.
    try:
        from nexus_agent_platform.governed.approvals import get_approval
        approval = get_approval(str(approval_id))
    except Exception:
        return False
    if not approval or str(approval.get("status", "")).lower() not in {"approved", "consumed"}:
        return False
    resolved_by = " ".join(str(approval.get("resolved_by") or "").upper().replace("_", " ").split())
    inputs = approval.get("input_summary") or {}
    return (resolved_by in {"RAY", "RAY DAVIS", "RAYMOND DAVIS"} and
            str(approval.get("action_id") or "") == "project.stop" and
            str(inputs.get("project_id") or "") == str(project_id) and
            str(inputs.get("decision") or "").upper() == decision_value)


def parent_stop_fallback(*, proposed_status: str, next_owner: str = "RESEARCH") -> dict[str, Any]:
    """Preserve the objective and route a rejected approach for replanning.

    An AI/department stop proposal is not itself a reason to interrupt Ray.
    Only the governed Ray approval receipt may stop the parent project.
    """
    return {
        "project_status": "ACTIVE",
        "execution_state": "REPLANNING",
        "requested_parent_decision": str(proposed_status).upper(),
        "next_action_id": "replan-rejected-approach",
        "next_owner": next_owner or "RESEARCH",
        "next_action_type": "REASSESS_AND_ROUTE_NEXT_APPROACH",
        "next_action_reason": "The failed/rejected state describes an approach; preserve the parent objective and select a safe next route.",
        "return_owner_after_decision": next_owner or "RESEARCH",
        "continue_research": True,
        "requires_ray": False,
    }


def guard_parent_state_write(*, collection: str, proposed: dict[str, Any],
                             prior: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Protect parent entity stores at their common persistence boundary.

    Child work item terminal states are intentionally outside this policy.
    This guard applies only to registered parent collections and records that
    carry a parent identity. It returns the normalized record and optional
    denial receipt so callers can preserve both continuation and audit data.
    """
    row = dict(proposed)
    if collection not in PARENT_COLLECTIONS:
        return row, None
    identity = (row.get("goal_id") or row.get("opportunity_id") or row.get("project_id") or
                row.get("business_idea_id") or row.get("case_id") or row.get("id"))
    if not identity:
        return row, None
    status_key = "status" if "status" in row else "project_status" if "project_status" in row else None
    if not status_key:
        return row, None
    proposed_status = str(row.get(status_key) or "").upper()
    if proposed_status not in PROJECT_STOP_STATES:
        return row, None
    decision = str(row.get("ray_stop_decision") or _DECISIONS[proposed_status]).upper()
    actor = str(row.get("actor") or row.get("updated_by") or row.get("created_by") or "NEXUS")
    approval_id = row.get("ray_approval_id") or row.get("approval_id")
    if ray_stop_authorized(actor=actor, approval_id=str(approval_id or ""),
                           decision=decision, project_id=str(identity)):
        row["ray_authorized_stop"] = True
        return row, None
    fallback = parent_stop_fallback(proposed_status=proposed_status,
                                    next_owner=str(row.get("owner") or "RESEARCH"))
    safe_prior = str((prior or {}).get(status_key) or "").upper()
    row["requested_parent_status"] = proposed_status
    row[status_key] = safe_prior if safe_prior and safe_prior not in PROJECT_STOP_STATES else "ACTIVE"
    row.update({"execution_state": "REPLANNING", "next_action_id": fallback["next_action_id"],
        "next_owner": fallback["next_owner"], "next_action_type": fallback["next_action_type"],
        "next_action_reason": fallback["next_action_reason"], "return_owner_after_decision": fallback["return_owner_after_decision"],
        "continue_project": True, "requires_ray": False})
    receipt = {"policy": "RAY_ONLY_PARENT_STOP", "collection": collection,
        "entity_id": str(identity), "requested_status": proposed_status,
        "preserved_status": row[status_key], "actor": actor,
        "approval_id_present": bool(approval_id), "denied": True}
    row["stop_policy_receipt"] = receipt
    return row, receipt
