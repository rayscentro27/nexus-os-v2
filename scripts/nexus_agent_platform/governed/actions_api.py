"""Narrow governed-action capabilities for Nova.

These are NOT general write capabilities. They only create bounded,
schema-conforming records (recommendations, approval requests) or read
governed state. Execution itself is NOT callable here — it lives in
``governed.engine`` and is owned by the runtime/executor boundary.

The narrow capability names are the ONLY ones registered; there is no generic
CRUD.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from nexus_agent_platform.governed import approvals as approval_mod
from nexus_agent_platform.governed import persistence, recommendations, work_orders as wo
from nexus_agent_platform.governed.action_registry import (
    EXECUTABLE_RISKS,
    get_action,
    is_action_executable,
    list_available_actions,
)
from nexus_agent_platform.governed.queue import get_queue


def get_available_actions() -> Dict[str, Any]:
    """Exact allowed action registry (executable + honest non-executable list)."""
    actions = []
    for action in list_available_actions():
        aid = action.get("action_id", "")
        actions.append({
            "action_id": aid,
            "name": action.get("name"),
            "risk_level": action.get("risk_level"),
            "executable": is_action_executable(aid),
            "approval_required": action.get("approval_required", True),
            "enabled": action.get("enabled", False) if get_action(aid) else False,
            "description": action.get("description", ""),
        })
    return {
        "status": "success",
        "count": len(actions),
        "executable_count": sum(1 for a in actions if a["executable"]),
        "actions": actions,
    }


def prepare_action_recommendation(
    *,
    title: str,
    problem: str,
    recommended_action_id: Optional[str],
    reason: str,
    evidence: List[Dict[str, Any]],
    expected_outcome: str,
    risk_level: str,
    dependencies: Optional[List[str]] = None,
    confidence: str = "medium",
    source: str = "hermes_nova",
) -> Dict[str, Any]:
    """Create a bounded recommendation record (NOT authority to execute)."""
    if risk_level not in ("low", "moderate", "high", "prohibited"):
        return {"status": "invalid", "error": f"invalid risk_level '{risk_level}'"}
    rec = recommendations.create_recommendation(
        title=title,
        problem=problem,
        recommended_action_id=recommended_action_id,
        reason=reason,
        evidence=evidence,
        expected_outcome=expected_outcome,
        risk_level=risk_level,
        dependencies=dependencies or [],
        confidence=confidence,
        requires_approval=True,
        source=source,
    )
    return {
        "status": "success",
        "recommendation_id": rec["recommendation_id"],
        "executable_action": rec["executable_action"],
        "recommendation_only": rec["recommendation_only"],
        "action_id": rec["recommended_action_id"],
        "note": (
            "Recommendation recorded. Execution still requires explicit Ray approval "
            "and a governed work order."
        ),
    }


def create_approval_request(
    *,
    action_id: str,
    action_summary: str = "",
    input_summary: Optional[Dict[str, Any]] = None,
    recommendation_id: Optional[str] = None,
    evidence_refs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Create a bounded, persisted pending approval request for one action."""
    action = get_action(action_id)
    if action is None:
        return {
            "status": "invalid",
            "error": f"action '{action_id}' is not a governed action",
        }
    if not action.get("enabled"):
        return {
            "status": "invalid",
            "error": f"action '{action_id}' is disabled",
        }
    approval = approval_mod.create_approval_request(
        action_id=action_id,
        requested_by="hermes_nova",
        requested_for="ray",
        input_summary=input_summary,
        action_summary=action_summary or action.get("name", action_id),
        evidence_refs=evidence_refs,
        recommendation_id=recommendation_id,
    )
    return {
        "status": "success",
        "approval_id": approval["id"],
        "action_id": action_id,
        "action_summary": approval["action_summary"],
        "risk_level": approval["risk_level"],
        "status": approval["status"],
        "expires_at": approval["expires_at"],
        "requires_approval": approval["requires_approval"],
        "message": "Approval request ready. Awaiting explicit Ray approval.",
    }


def get_approval_status(approval_id: Optional[str] = None) -> Dict[str, Any]:
    """Read a specific approval or list pending ones (bounded)."""
    if approval_id:
        approval = approval_mod.get_approval(approval_id)
        if approval is None:
            return {"status": "not_found", "approval_id": approval_id}
        return {"status": "success", "approval_id": approval_id,
                "approval": approval_mod._mask_approval(approval)}
    pending = approval_mod.get_pending_approvals(requested_for="ray", include_self=False)
    return {
        "status": "success",
        "pending_count": len(pending),
        "pending_approvals": pending,
    }


def get_work_order_status(work_order_id: str) -> Dict[str, Any]:
    order = wo.get_work_order(work_order_id)
    if order is None:
        return {"status": "not_found", "work_order_id": work_order_id}
    return {
        "status": "success",
        "work_order_id": work_order_id,
        "order": wo._mask_work_order(order),
        "terminal": wo.work_order_terminal_status(order),
    }


def get_work_order_result(work_order_id: str) -> Dict[str, Any]:
    order = wo.get_work_order(work_order_id)
    if order is None:
        return {"status": "not_found", "work_order_id": work_order_id}
    masked = wo._mask_work_order(order)
    if order.get("status") != "completed":
        return {
            "status": "success",
            "work_order_id": work_order_id,
            "work_order_state": order.get("status"),
            "result": None,
            "note": "No verified terminal result yet — completion requires a verified terminal status.",
        }
    return {
        "status": "success",
        "work_order_id": work_order_id,
        "work_order_state": "completed",
        "result": masked.get("result"),
        "telemetry_run_id": masked.get("telemetry_run_id"),
        "error": masked.get("error"),
    }


def get_recent_work_orders(limit: int = 10, status: Optional[str] = None) -> Dict[str, Any]:
    orders = wo.list_work_orders(limit=limit, status=status)
    counts = wo.count_work_orders_by_status()
    return {
        "status": "success",
        "returned_count": len(orders),
        "work_orders": orders,
        "status_counts": counts,
    }


def get_work_queue(limit: int = 50, status: Optional[str] = None) -> Dict[str, Any]:
    """Read-only, priority-ordered work queue view. Never executes anything."""
    return get_queue(limit=limit, status=status)


def resolve_governed_approval(
    approval_id: str,
    decision: str,
    resolved_by: str = "ray",
) -> Dict[str, Any]:
    """Resolve an approval (approve/reject/cancel). Called by the runtime flow
    after conversation-scoped validation — NOT a general Nova write."""
    if decision not in ("approve", "reject", "cancel"):
        return {"status": "ambiguous", "approved": False}
    return approval_mod.resolve_approval(approval_id, decision, resolved_by=resolved_by)


def create_work_order_from_approval(
    approval_id: str,
    inputs: Optional[Dict[str, Any]] = None,
    expected_outcome: str = "",
    recommendation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a governed work order only from an APPROVED approval."""
    approval = approval_mod.get_approval(approval_id)
    if approval is None:
        return {"status": "not_found", "approval_id": approval_id}
    if approval.get("status") != "approved":
        return {
            "status": "invalid",
            "approval_id": approval_id,
            "error": f"approval status is '{approval.get('status')}', expected 'approved'",
        }
    action_id = approval.get("action_id")
    order = wo.create_work_order(
        approval_id=approval_id,
        action_id=action_id,
        requested_by="hermes_nova",
        approved_by="ray",
        inputs=inputs or approval.get("input_summary") or {},
        expected_outcome=expected_outcome,
        recommendation_id=recommendation_id or approval.get("recommendation_id"),
        idempotency_key=f"{approval_id}:{action_id}:1",
    )
    persistence.emit_audit_event({
        "type": "work_order_queued",
        "work_order_id": order["work_order_id"],
        "approval_id": approval_id,
        "action_id": action_id,
    })
    return {
        "status": "success",
        "work_order_id": order["work_order_id"],
        "approval_id": approval_id,
        "action_id": action_id,
        "order": order,
    }