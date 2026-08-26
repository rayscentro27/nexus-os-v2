"""Governed approval layer.

Approval is explicit, persisted, bound to exactly one action + inputs, expires,
is single-use, and survives worker restarts. No blanket approvals.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from nexus_agent_platform.governed import persistence
from nexus_agent_platform.governed.action_registry import get_action

DEFAULT_APPROVAL_TTL_SECONDS = 30 * 60
APPROVAL_STATUSES = frozenset({"pending", "approved", "rejected", "expired", "consumed", "cancelled"})
TERMINAL_APPROVAL_STATUSES = frozenset({"rejected", "expired", "consumed", "cancelled"})

# Explicit approval phrases — used as a deterministic first gate, never alone.
# Always combined with persisted context (exactly one matching pending approval).
EXPLICIT_APPROVE_PHRASES = (
    "approve", "approved", "yes, run it", "yes please run it", "run it",
    "execute it", "go ahead", "approved", "confirm", "confirmed",
    "execute the approved", "run the approved", "i approve", "i approve it",
    "yes run", "proceed",
)

EXPLICIT_REJECT_PHRASES = ("reject", "rejected", "no", "don't run", "dont run",
                           "do not run", "cancel approval", "deny", "denied")


def utc_now() -> str:
    return persistence._now()


def create_approval_request(
    *,
    action_id: str,
    requested_by: str = "hermes_nova",
    requested_for: str = "ray",
    input_summary: Optional[Dict[str, Any]] = None,
    action_summary: str = "",
    evidence_refs: Optional[List[str]] = None,
    recommendation_id: Optional[str] = None,
    ttl_seconds: int = DEFAULT_APPROVAL_TTL_SECONDS,
    expires_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a persisted pending approval request bound to one action."""
    action = get_action(action_id)
    created_at = utc_now()
    approval = {
        "id": persistence.new_id("appr"),
        "recommendation_id": recommendation_id,
        "action_id": action_id,
        "action_summary": action_summary or (action.get("name", action_id) if action else action_id),
        "input_summary": input_summary or {},
        "requested_by": requested_by,
        "requested_for": requested_for,
        "risk_level": action.get("risk_level", "unknown") if action else "unknown",
        "status": "pending",
        "created_at": created_at,
        "expires_at": expires_at or _add_seconds(created_at, ttl_seconds),
        "evidence_refs": evidence_refs or [],
        "requires_approval": bool(action and action.get("approval_required", True)),
        "resolution": None,
        "resolved_at": None,
        "resolved_by": None,
    }
    persistence.append_record("approvals", approval)
    persistence.emit_audit_event({
        "type": "approval_requested",
        "approval_id": approval["id"],
        "action_id": action_id,
        "recommendation_id": recommendation_id,
        "requested_by": requested_by,
    })
    return approval


def _add_seconds(iso_time: str, seconds: int) -> str:
    from datetime import datetime, timedelta, timezone
    try:
        dt = datetime.fromisoformat(iso_time)
    except ValueError:
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (dt + timedelta(seconds=seconds)).isoformat()


def get_approval(approval_id: str) -> Optional[Dict[str, Any]]:
    return persistence.get_record("approvals", approval_id)


def get_pending_approvals(
    requested_for: str = "ray",
    include_self: bool = True,
) -> List[Dict[str, Any]]:
    """List non-expired pending approvals scoped to the requested principal.

    ``include_self`` is retained for compatibility, but no longer broadens a
    Ray query to every principal.  Callers that need an administrative view
    must explicitly pass ``requested_for=None``.
    """
    result = []
    seen: set = set()
    for record in persistence.read_records("approvals"):
        if record["id"] in seen:
            continue
        seen.add(record["id"])
        if record.get("status") != "pending" or approval_is_expired(record):
            continue
        if requested_for is None or requested_for == record.get("requested_for"):
            result.append(_mask_approval(record))
    return result


def approval_is_expired(approval: Dict[str, Any]) -> bool:
    from datetime import datetime, timezone
    expiry = approval.get("expires_at")
    if not expiry:
        return False
    try:
        exp = datetime.fromisoformat(expiry)
    except ValueError:
        return False
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) > exp


def is_approval_valid_for(approval: Dict[str, Any], action_id: str, inputs: Optional[Dict[str, Any]]) -> str:
    """Return a reason string if the approval is NOT valid for this execution, else ''."""
    if approval.get("status") != "approved":
        return f"approval status is '{approval.get('status')}', expected 'approved'"
    if approval_is_expired(approval):
        return "approval has expired"
    if approval.get("action_id") != action_id:
        return f"approval is bound to {approval.get('action_id')}, not {action_id}"
    bound_inputs = approval.get("input_summary") or {}
    if inputs is not None and list(inputs.keys()) != list(bound_inputs.keys()):
        return "approval inputs do not match requested action inputs"
    return ""


def resolve_approval(
    approval_id: str,
    decision: str,
    *,
    resolved_by: str = "ray",
    feedback: str = "",
) -> Dict[str, Any]:
    """Resolve a pending approval: approve | reject | cancel.

    Returns an envelope; ``status`` may be:
      - ok: approval transitioned
      - unauthorized: not the right approver
      - ambiguous: not a valid decision
      - not_pending: approval no longer pending
      - not_found
    """
    if decision not in ("approve", "reject", "cancel"):
        return {"status": "ambiguous", "decision": decision, "approved": False}
    approval = get_approval(approval_id)
    if approval is None:
        return {"status": "not_found", "approval_id": approval_id, "approved": False}
    if approval.get("status") != "pending":
        return {"status": "not_pending", "approval_id": approval_id,
                "current_status": approval.get("status"), "approved": False}
    if approval_is_expired(approval):
        updated = _transition_approval(approval_id, "expired", resolved_by, feedback)
        return {"status": "expired", "approval_id": approval_id,
                "approved": False, "approval": updated}

    new_status = {"approve": "approved", "reject": "rejected", "cancel": "cancelled"}[decision]
    updated = _transition_approval(approval_id, new_status, resolved_by, feedback)
    if new_status == "approved":
        persistence.emit_audit_event({
            "type": "approval_granted",
            "approval_id": approval_id,
            "action_id": updated.get("action_id"),
            "resolved_by": resolved_by,
        })
    else:
        persistence.emit_audit_event({
            "type": f"approval_{new_status}",
            "approval_id": approval_id,
            "action_id": updated.get("action_id"),
            "resolved_by": resolved_by,
        })
    return {
        "status": "ok",
        "approved": new_status == "approved",
        "approval_id": approval_id,
        "approval": _mask_approval(updated),
    }


def _transition_approval(
    approval_id: str,
    new_status: str,
    resolved_by: str,
    feedback: str,
) -> Dict[str, Any]:
    """Append a superseding record for the approval with a new status."""
    current = get_approval(approval_id)
    assert current is not None
    updated = {
        **current,
        "status": new_status,
        "resolution": feedback or ("approved" if new_status == "approved" else new_status),
        "resolved_at": utc_now(),
        "resolved_by": resolved_by,
    }
    persistence.append_record("approvals", updated)
    return updated


def mark_approval_consumed(approval_id: str) -> Optional[Dict[str, Any]]:
    """Single-use: mark approved approval as consumed after execution."""
    current = get_approval(approval_id)
    if current is None or current.get("status") != "approved":
        return current
    updated = {
        **current,
        "status": "consumed",
        "consumed_at": utc_now(),
    }
    persistence.append_record("approvals", updated)
    persistence.emit_audit_event({
        "type": "approval_consumed",
        "approval_id": approval_id,
        "action_id": updated.get("action_id"),
    })
    return updated


def expire_pending_approvals() -> int:
    """Transition expired pending approvals to 'expired'. Returns count."""
    count = 0
    seen: set = set()
    for record in persistence.read_records("approvals"):
        if record["id"] in seen or record.get("status") != "pending":
            continue
        seen.add(record["id"])
        if permission_is_expired(record):
            _transition_approval(record["id"], "expired", "system", "ttl expired")
            count += 1
    return count


def permission_is_expired(record: Dict[str, Any]) -> bool:
    return approval_is_expired(record)


def _mask_approval(approval: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "approval_id": approval["id"],
        "recommendation_id": approval.get("recommendation_id"),
        "action_id": approval.get("action_id"),
        "action_summary": approval.get("action_summary"),
        "input_summary": approval.get("input_summary", {}),
        "requested_by": approval.get("requested_by"),
        "requested_for": approval.get("requested_for"),
        "risk_level": approval.get("risk_level"),
        "status": approval.get("status"),
        "created_at": approval.get("created_at"),
        "expires_at": approval.get("expires_at"),
        "evidence_refs": approval.get("evidence_refs", []),
        "requires_approval": approval.get("requires_approval", True),
    }
