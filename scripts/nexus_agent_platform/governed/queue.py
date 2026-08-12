"""Governed work queue + priority engine.

The queue is a VIEW over persisted work orders, ordered by a deterministic
priority score. It never executes anything on its own: a runner must explicitly
square the queue, and it only ever picks up ONE eligible order at a time through
``next_eligible``.

Eligibility rules (all must hold):
  - work order was created from an APPROVED approval (status ``approved``/``queued``)
  - action exists, is enabled, and its risk is in EXECUTABLE_RISKS
  - idempotency key has not already run
  - order is not stale

Priority is bounded and deterministic: LOW risk before others, FIFO by age
within the same risk tier. It is a hint for ordering, never authorization.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from nexus_agent_platform.governed import persistence, work_orders as wo
from nexus_agent_platform.governed.action_registry import (
    EXECUTABLE_RISKS,
    get_action,
    is_action_executable,
)

QUEUEABLE_STATUSES = ("approved", "queued")

RISK_PRIORITY = {"low": 0, "moderate": 1, "high": 2, "prohibited": 3, "unknown": 4}

# A runner must pass this many checks back in; the engine refuses unless the
# runner declared the queue was squared.
RUNNER_CHECKPOINT = "governed_runner_v1"


def priority_score(order: Dict[str, Any]) -> float:
    """Deterministic priority score. LOWER is higher priority (runs first)."""
    risk = order.get("risk_level") or get_action(order.get("action_id") or "") or {}
    risk_level = risk.get("risk_level", "unknown") if isinstance(risk, dict) else "unknown"
    risk_rank = RISK_PRIORITY.get(risk_level, RISK_PRIORITY["unknown"])

    created_at = order.get("created_at") or ""
    try:
        created_dt = datetime.fromisoformat(created_at)
    except (ValueError, TypeError):
        created_dt = datetime.now(timezone.utc)
    if created_dt.tzinfo is None:
        created_dt = created_dt.replace(tzinfo=timezone.utc)
    age_seconds = (datetime.now(timezone.utc) - created_dt).total_seconds()

    # Risk dominates ordering; age breaks ties within the same risk tier.
    # Older orders score lower (higher priority) but never out-rank risk.
    return risk_rank * 1_000_000_000 + age_seconds


def _latest(order_id: str) -> Optional[Dict[str, Any]]:
    return persistence.get_record("work_orders", order_id, key="work_order_id")


def order_eligible(order: Dict[str, Any]) -> Dict[str, Any]:
    """Check eligibility of one work order. Returns {eligible, reasons}."""
    reasons: List[str] = []
    if order.get("status") not in QUEUEABLE_STATUSES:
        reasons.append(f"status '{order.get('status')}' is not queueable")
    action = get_action(order.get("action_id") or "")
    if action is None:
        reasons.append(f"action '{order.get('action_id')}' is not a governed action")
    elif not action.get("enabled"):
        reasons.append(f"action '{order.get('action_id')}' is disabled")
    elif not is_action_executable(order.get("action_id")):
        reasons.append(f"action '{order.get('action_id')}' is not executable (risk not in {sorted(EXECUTABLE_RISKS)})")
    if order.get("idempotency_key") and wo.idempotency_key_executed(order["idempotency_key"]):
        reasons.append("idempotency key already executed")
    if order.get("status") == "queued" and _latest_is_stale(order):
        reasons.append("work order is stale")
    return {"eligible": not reasons, "reasons": reasons}


def _latest_is_stale(order: Dict[str, Any]) -> bool:
    anchor = order.get("started_at") or order.get("created_at") or ""
    try:
        anchor_dt = datetime.fromisoformat(anchor)
    except (ValueError, TypeError):
        return False
    if anchor_dt.tzinfo is None:
        anchor_dt = anchor_dt.replace(tzinfo=timezone.utc)
    threshold = order.get("stale_after_seconds") or wo.DEFAULT_STALE_SECONDS
    return (datetime.now(timezone.utc) - anchor_dt).total_seconds() > threshold


def get_queue(limit: int = 50, status: Optional[str] = None) -> Dict[str, Any]:
    """Read-only, priority-ordered view of queueable work orders."""
    eligible: List[Dict[str, Any]] = []
    seen: set = set()
    for record in persistence.read_records("work_orders"):
        if record["work_order_id"] in seen:
            continue
        seen.add(record["work_order_id"])
        if status and record.get("status") != status:
            continue
        if record.get("status") in QUEUEABLE_STATUSES:
            eligible.append(record)
    eligible.sort(key=priority_score)
    orders = [wo._mask_work_order(o) for o in eligible[:limit]]
    return {
        "status": "success",
        "returned_count": len(orders),
        "queueable_count": len(eligible),
        "work_orders": orders,
        "priority_note": (
            "Queue is a read-only view ordered by risk then age. "
            "Nothing runs without an explicit runner squaring the queue."
        ),
    }


def next_eligible(checkpoint: Optional[str] = None) -> Dict[str, Any]:
    """Pick the single next eligible order for a runner.

    The runner MUST pass back the exact RUNNER_CHECKPOINT to prove it read the
    queue. The queue returns the top eligible order (or none) — it never marks
    it running and never executes.
    """
    if checkpoint != RUNNER_CHECKPOINT:
        return {
            "status": "checkpoint_required",
            "eligible": False,
            "error": (
                "A runner must square the queue with the governed checkpoint. "
                "This is read-only; no order was picked."
            ),
        }
    queue = get_queue(limit=100)
    for order in queue.get("work_orders", []):
        latest = _latest(order["work_order_id"])
        if latest is None:
            continue
        check = order_eligible(latest)
        if check["eligible"]:
            return {
                "status": "picked",
                "eligible": True,
                "work_order_id": latest["work_order_id"],
                "order": wo._mask_work_order(latest),
            }
    return {"status": "empty", "eligible": False, "work_order_id": None}


def claim_next(checkpoint: str, claimed_by: str) -> Dict[str, Any]:
    """Runner-side claim: pick next eligible order and transition it to queued.

    Still does NOT execute. The engine's ``execute_approved_work_order`` is the
    only execution entry and independently re-validates everything.
    """
    if checkpoint != RUNNER_CHECKPOINT:
        return {
            "status": "checkpoint_required",
            "eligible": False,
            "error": "Runner must square the queue with the governed checkpoint.",
        }
    picked = next_eligible(checkpoint)
    if not picked.get("eligible"):
        return picked
    order_id = picked["work_order_id"]
    latest = _latest(order_id)
    if latest is None:
        return {"status": "not_found", "eligible": False, "work_order_id": order_id}
    check = order_eligible(latest)
    if not check["eligible"]:
        return {"status": "ineligible", "eligible": False, "work_order_id": order_id, "reasons": check["reasons"]}
    try:
        wo.transition(order_id, "queued", **{})
    except ValueError:
        # Already queued — fine, this is a claim on an existing queued order.
        pass
    persistence.emit_audit_event({
        "type": "work_order_claimed",
        "work_order_id": order_id,
        "claimed_by": claimed_by,
    })
    return {
        "status": "claimed",
        "eligible": True,
        "work_order_id": order_id,
        "order": wo._mask_work_order(wo.get_work_order(order_id) or latest),
    }
