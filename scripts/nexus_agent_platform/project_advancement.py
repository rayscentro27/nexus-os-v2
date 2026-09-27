"""Canonical bridge from governed department handoffs to internal work.

This is deliberately a small adapter over the existing append-only handoff,
work-order, and research-request stores.  It does not create a second queue or
worker system.  It records a department's consumption of a QUALIFY/TEST
handoff, executes only a bounded internal intake where a certified
deterministic executor already exists, and records the reviewed next action.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from nexus_agent_platform.governed import persistence
from nexus_foundation.contracts import build_work_order, transition_work_order


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


OWNER_BY_DEPARTMENT = {
    "TRADING": "TRADING_ENGINE",
    "SYSTEMS": "SYSTEMS_AI_WORKER",
    "CLYDE_CREDIT": "CLYDE",
    "CREDIT_BUSINESS_FUNDING": "CLYDE",
    "REVENUE_OPPORTUNITY_DISCOVERY": "GROWTH",
    "MARKETING": "GROWTH",
    "CREATIVE": "CREATIVE",
    "OPERATIONS": "NOVA",
    "FINANCE": "NOVA",
}


def _latest(rows: list[dict[str, Any]], key: str, value: str) -> dict[str, Any] | None:
    # persistence.read_records returns newest-first.
    for row in rows:
        if str(row.get(key) or "") == str(value):
            return row
    return None


def _work_order_for_handoff(handoff_id: str) -> dict[str, Any] | None:
    return next((row for row in persistence.read_records("work_orders")
                 if row.get("inputs", {}).get("handoff_id") == handoff_id
                 or row.get("handoff_id") == handoff_id), None)


def create_internal_work_order(handoff: dict[str, Any]) -> dict[str, Any]:
    """Create one idempotent internal order for a qualified/test handoff."""
    handoff_id = str(handoff.get("handoff_id") or "")
    if not handoff_id:
        raise ValueError("handoff_id_required")
    existing = _work_order_for_handoff(handoff_id)
    if existing:
        return {**existing, "deduplicated": True}
    decision = str(handoff.get("alpha_decision") or handoff.get("decision") or "").upper()
    if decision not in {"QUALIFY", "QUALIFIED", "TEST"}:
        raise ValueError("handoff_not_executable")
    department = str(handoff.get("department_target") or handoff.get("target_department") or "").upper()
    owner = OWNER_BY_DEPARTMENT.get(department)
    if not owner:
        raise ValueError(f"no_internal_owner:{department}")
    project_id = str(handoff.get("finding_id") or handoff.get("request_id") or handoff_id)
    order = build_work_order(
        goal_id=project_id,
        work_type="department_internal_intake",
        owner_specialist=owner,
        inputs={
            "handoff_id": handoff_id,
            "decision": decision,
            "department": department,
            "research_package_id": handoff.get("research_package_id"),
            "alpha_receipt_id": handoff.get("alpha_receipt_id"),
            "source_refs": list(handoff.get("source_refs") or []),
            "external_action_allowed": False,
        },
        authority_required="internal_read_only",
        approval_required=False,
        priority="normal",
        cost_budget={"max_usd": 0},
        retry_budget={"max_attempts": 1},
    )
    order["handoff_id"] = handoff_id
    order["owner"] = owner
    order["department"] = department
    order["idempotency_key"] = f"department-intake:{handoff_id}"
    persistence.append_record("work_orders", order)
    return order


def consume_trading_test(handoff_id: str) -> dict[str, Any]:
    """Consume the real Trading TEST handoff without inventing strategy rules.

    The executor validates the intake contract.  Missing strategy rules are a
    truthful dependency result, not a reason to manufacture a backtest.
    """
    handoffs = persistence.read_records("research_v2_handoffs")
    handoff = _latest(handoffs, "handoff_id", handoff_id)
    if not handoff:
        raise ValueError("handoff_not_found")
    if str(handoff.get("department_target") or "").upper() != "TRADING":
        raise ValueError("not_trading_handoff")
    if str(handoff.get("alpha_decision") or "").upper() != "TEST":
        raise ValueError("trading_test_required")
    order = create_internal_work_order(handoff)
    if order.get("status") == "COMPLETED":
        return {"handoff": handoff, "work_order": order, "deduplicated": True}
    order = transition_work_order(order, "ASSIGNED", assignment_reason="existing TRADING_ENGINE deterministic intake")
    persistence.append_record("work_orders", order)
    order = transition_work_order(order, "IN_PROGRESS", worker_id="TRADING_ENGINE", execution_class="DETERMINISTIC_EXECUTOR")
    persistence.append_record("work_orders", order)
    source_refs = list(handoff.get("source_refs") or [])
    if not source_refs:
        source_refs = next((list(row.get("source_refs") or []) for row in handoffs
                            if row.get("handoff_id") == handoff_id and row.get("source_refs")), [])
    missing = [
        "concrete strategy or indicator identity",
        "entry and exit rules",
        "market and timeframe",
        "risk and position-sizing rules",
    ]
    output = {
        "status": "BLOCKED_DEPENDENCY",
        "worker": "TRADING_ENGINE",
        "execution_class": "DETERMINISTIC_EXECUTOR",
        "source_refs": source_refs,
        "ruleset_present": False,
        "missing_inputs": missing,
        "live_trading": False,
        "external_action_performed": False,
    }
    review = {
        "status": "REVIEWED",
        "reviewer": "TRADING_ENGINE_INTAKE_GATE",
        "decision": "RETURN_TO_RESEARCH",
        "reason": "A paper/backtest cannot be created without a supported ruleset.",
    }
    next_action = {
        "action": "Acquire a supported strategy ruleset from permitted public sources.",
        "owner": "RESEARCH",
        "work_type": "RESEARCH_FOLLOWUP",
        "expected_output": "strategy identity, entry, exit, market, timeframe, and risk rules",
        "completion_criteria": missing,
        "approval_required": False,
        "blocker": "MISSING_STRATEGY_RULESET",
        "return_target": "TRADING",
    }
    order = transition_work_order(order, "COMPLETED", result={"output": output, "review": review, "next_action": next_action}, receipt_refs=[f"trading-intake:{handoff_id}"], next_action=next_action)
    order["completed_by"] = "TRADING_ENGINE"
    persistence.append_record("work_orders", order)
    timestamp = _now()
    persistence.append_record("research_v2_handoffs", {
        **handoff,
        "status": "CONSUMED",
        "department_consumed_at": timestamp,
        "work_order_id": order["work_order_id"],
        "output": output,
        "review": review,
        "next_action": next_action,
        "project_state": "WAITING_DEPENDENCY",
        "updated_at": timestamp,
    })
    request_id = handoff.get("request_id")
    if request_id:
        persistence.append_record("research_requests", {
            "request_id": request_id,
            "status": "WAITING_DEPENDENCY",
            "department": "TRADING",
            "work_order_id": order["work_order_id"],
            "project_state": "WAITING_DEPENDENCY",
            "next_action": next_action,
            "updated_at": timestamp,
            "external_action_allowed": False,
        })
    return {"handoff": handoff, "work_order": order, "output": output, "review": review, "next_action": next_action, "project_state": "WAITING_DEPENDENCY", "deduplicated": False}


def advancement_metrics(*, since: str | None = None) -> dict[str, Any]:
    """Count real persisted advancement events without treating queue depth as progress."""
    orders = persistence.read_records("work_orders")
    handoffs = persistence.read_records("research_v2_handoffs")
    if since:
        orders = [row for row in orders if str(row.get("created_at") or row.get("completed_at") or "") >= since]
        handoffs = [row for row in handoffs if str(row.get("recorded_at") or row.get("updated_at") or "") >= since]
    latest_orders: dict[str, dict[str, Any]] = {}
    for row in orders:  # persistence returns newest-first
        if row.get("work_order_id"):
            latest_orders.setdefault(str(row["work_order_id"]), row)
    return {
        "work_orders_created": len(latest_orders),
        "work_orders_claimed": sum(1 for row in latest_orders.values() if row.get("status") in {"ASSIGNED", "IN_PROGRESS", "COMPLETED"}),
        "work_orders_completed": sum(1 for row in latest_orders.values() if row.get("status") == "COMPLETED"),
        "deterministic_executions": sum(1 for row in latest_orders.values() if row.get("execution_class") == "DETERMINISTIC_EXECUTOR"),
        "outputs_reviewed": sum(1 for row in handoffs if (row.get("review") or {}).get("status") == "REVIEWED"),
        "next_actions_created": sum(1 for row in latest_orders.values() if row.get("next_action")) + sum(1 for row in handoffs if row.get("next_action")),
        "project_state_transitions": sum(1 for row in handoffs if row.get("project_state")),
        "handoffs_created": len(handoffs),
        "handoffs_consumed": sum(1 for row in handoffs if row.get("status") in {"CONSUMED", "COMPLETED"}),
        "department_activity": {department: sum(1 for row in handoffs if str(row.get("department_target") or "").upper() == department) for department in sorted({str(row.get("department_target") or "").upper() for row in handoffs if row.get("department_target")})},
    }
