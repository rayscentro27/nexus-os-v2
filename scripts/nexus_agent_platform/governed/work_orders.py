"""Governed work order layer.

Canonical lifecycle:
    pending_approval -> approved -> queued -> running -> completed
Failure paths:
    queued -> blocked | cancelled
    running -> failed
    pending_approval -> rejected | expired | cancelled

Idempotency: every executable work order has an idempotency key; retries /
replayed approvals never double-execute. Stale detection marks queued/running
orders past their threshold.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from nexus_agent_platform.governed import persistence
from nexus_agent_platform.governed.action_registry import get_action

VALID_STATUSES = frozenset({
    "pending_approval", "approved", "queued", "running",
    "completed", "blocked", "failed", "cancelled", "expired", "stale",
})

# Allowed direct transitions (status -> set of allowed next statuses).
ALLOWED_TRANSITIONS: Dict[str, frozenset] = {
    "pending_approval": frozenset({"approved", "pending_approval", "rejected", "expired", "cancelled"}),
    "approved": frozenset({"queued"}),
    "queued": frozenset({"queued", "running", "blocked", "cancelled"}),
    "running": frozenset({"running", "completed", "failed"}),
    "completed": frozenset(),
    "blocked": frozenset(),
    "failed": frozenset(),
    "cancelled": frozenset(),
    "expired": frozenset(),
    "stale": frozenset({"queued"}),
}

DEFAULT_STALE_SECONDS = 15 * 60
DEFAULT_RUNNING_TIMEOUT_SECONDS = 15 * 60


def utc_now() -> str:
    return persistence._now()


def create_work_order(
    *,
    approval_id: str,
    action_id: str,
    requested_by: str = "hermes_nova",
    approved_by: str = "ray",
    inputs: Optional[Dict[str, Any]] = None,
    expected_outcome: str = "",
    recommendation_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    status: str = "queued",
) -> Dict[str, Any]:
    """Create a governed work order tied to a validated approval."""
    action = get_action(action_id)
    created_at = utc_now()
    work_order = {
        "id": persistence.new_id("wo"),
        "work_order_id": persistence.new_id("wo"),
        "approval_id": approval_id,
        "action_id": action_id,
        "status": status,
        "requested_by": requested_by,
        "approved_by": approved_by,
        "created_at": created_at,
        "started_at": None,
        "completed_at": None,
        "inputs": inputs or {},
        "expected_outcome": expected_outcome,
        "result": None,
        "error": None,
        "telemetry_run_id": None,
        "recommendation_id": recommendation_id,
        "idempotency_key": idempotency_key or f"{approval_id}:{action_id}:1",
        "stale_after_seconds": DEFAULT_STALE_SECONDS,
        "running_timeout_seconds": action.get("timeout_seconds", DEFAULT_RUNNING_TIMEOUT_SECONDS)
        if action else DEFAULT_RUNNING_TIMEOUT_SECONDS,
    }
    persistence.append_record("work_orders", work_order)
    persistence.emit_audit_event({
        "type": "work_order_created",
        "work_order_id": work_order["work_order_id"],
        "approval_id": approval_id,
        "action_id": action_id,
        "requested_by": requested_by,
    })
    return _mask_work_order(work_order)


def get_work_order(work_order_id: str) -> Optional[Dict[str, Any]]:
    return persistence.get_record("work_orders", work_order_id, key="work_order_id")


def idempotency_key_executed(idempotency_key: str) -> bool:
    """Idempotency guard: has any work order already run with this key?"""
    for record in persistence.read_records("work_orders"):
        if record.get("idempotency_key") == idempotency_key:
            if record.get("status") in ("completed", "running", "blocked", "failed"):
                return True
    return False


def transition(work_order_id: str, to_status: str, **changes: Any) -> Dict[str, Any]:
    """Attempt a state transition. Invalid transitions raise ValueError."""
    current = get_work_order(work_order_id)
    if current is None:
        raise ValueError(f"Work order not found: {work_order_id}")
    allowed = ALLOWED_TRANSITIONS.get(current["status"], frozenset())
    if to_status not in allowed:
        raise ValueError(f"Invalid {current['status']} -> {to_status} transition")
    updated = {**current, "status": to_status, **changes}
    if to_status == "running" and updated.get("started_at") is None:
        updated["started_at"] = utc_now()
    if to_status == "completed" and updated.get("completed_at") is None:
        updated["completed_at"] = utc_now()
    if to_status == "blocked":
        updated.pop("started_at", None)
    persistence.append_record("work_orders", updated)
    persistence.emit_audit_event({
        "type": f"work_order_{to_status}",
        "work_order_id": work_order_id,
        "action_id": updated.get("action_id"),
        "status": to_status,
    })
    return updated


def record_result(
    work_order_id: str,
    *,
    status: str,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    telemetry_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Record a terminal-execution result on a running work order."""
    current = get_work_order(work_order_id)
    if current is None:
        raise ValueError(f"Work order not found: {work_order_id}")
    if status not in ("completed", "failed", "blocked"):
        raise ValueError(f"Invalid terminal status: {status}")
    updated = {
        **current,
        "status": status,
        "result": result,
        "error": error,
        "telemetry_run_id": telemetry_run_id,
        "completed_at": utc_now(),
    }
    persistence.append_record("work_orders", updated)
    persistence.emit_audit_event({
        "type": f"execution_{status}",
        "work_order_id": work_order_id,
        "action_id": updated.get("action_id"),
        "status": status,
        "telemetry_run_id": telemetry_run_id,
    })
    return _mask_work_order(updated)


def _order_is_stale(order: Dict[str, Any]) -> bool:
    """True if order is queued/running past its threshold (or its run is stale)."""
    if order["status"] not in ("queued", "running"):
        return False
    if order["status"] == "running" and _running_too_long(order):
        return True
    anchor = order.get("started_at") or order.get("created_at") or ""
    from datetime import datetime, timezone
    try:
        anchor_dt = datetime.fromisoformat(anchor)
    except ValueError:
        return False
    if anchor_dt.tzinfo is None:
        anchor_dt = anchor_dt.replace(tzinfo=timezone.utc)
    threshold = (order.get("stale_after_seconds") or DEFAULT_STALE_SECONDS)
    if order["status"] == "running":
        threshold = order.get("running_timeout_seconds") or DEFAULT_RUNNING_TIMEOUT_SECONDS
    return (datetime.now(timezone.utc) - anchor_dt).total_seconds() > threshold


def _running_too_long(order: Dict[str, Any]) -> bool:
    return _order_is_stale(order)


def detect_stale_work_orders() -> List[Dict[str, Any]]:
    """Detect queued/running work orders past their threshold; classify stale."""
    stale = []
    seen: set = set()
    for record in persistence.read_records("work_orders"):
        if record["work_order_id"] in seen:
            continue
        seen.add(record["work_order_id"])
        if record.get("status") in ("queued", "running") and _order_is_stale(record):
            stale.append(_mask_work_order({**record, "status": "stale"}))
    return stale


def list_work_orders(
    limit: int = 50,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    seen: set = set()
    result: List[Dict[str, Any]] = []
    for record in persistence.read_records("work_orders"):
        if record["work_order_id"] in seen:
            continue
        seen.add(record["work_order_id"])
        if status and record.get("status") != status:
            continue
        result.append(_mask_work_order(record))
    return result[:limit]


def count_work_orders_by_status() -> Dict[str, int]:
    counts = {s: 0 for s in VALID_STATUSES}
    seen: set = set()
    for record in persistence.read_records("work_orders"):
        if record["work_order_id"] in seen:
            continue
        seen.add(record["work_order_id"])
        status_key = record.get("status", "unknown")
        if status_key in counts:
            counts[status_key] += 1
    return counts


def _mask_work_order(order: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "work_order_id": order["work_order_id"],
        "approval_id": order.get("approval_id"),
        "action_id": order.get("action_id"),
        "status": order.get("status"),
        "requested_by": order.get("requested_by"),
        "approved_by": order.get("approved_by"),
        "created_at": order.get("created_at"),
        "started_at": order.get("started_at"),
        "completed_at": order.get("completed_at"),
        "inputs": order.get("inputs"),
        "expected_outcome": order.get("expected_outcome"),
        "result": order.get("result"),
        "error": order.get("error"),
        "telemetry_run_id": order.get("telemetry_run_id"),
        "recommendation_id": order.get("recommendation_id"),
        "idempotency_key": order.get("idempotency_key"),
    }


def work_order_terminal_status(order: Dict[str, Any]) -> bool:
    return order.get("status") in ("completed", "failed", "blocked", "cancelled", "expired")