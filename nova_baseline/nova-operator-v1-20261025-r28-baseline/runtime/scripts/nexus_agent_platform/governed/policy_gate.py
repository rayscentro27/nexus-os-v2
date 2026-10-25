"""Policy gate — deterministic gate before ANY execution.

Verifies every precondition required by the governed loop. If ANY check fails,
execution is blocked and a structured reason is emitted.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from nexus_agent_platform.governed import approvals as approval_mod
from nexus_agent_platform.governed import persistence, work_orders as wo
from nexus_agent_platform.governed.action_registry import (
    EXECUTABLE_RISKS,
    get_action,
    is_action_enabled,
    validate_action_id,
)


def check_execution(
    *,
    approval_id: str,
    action_id: str,
    inputs: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, List[str]]:
    """Return (allowed, reasons). reasons is the structured block reason if blocked."""
    reasons: List[str] = []

    # 1. Action exists in registry
    if not validate_action_id(action_id):
        reasons.append(f"action '{action_id}' is not in the governed action registry")
        return False, reasons

    action = get_action(action_id)

    # 2. Action enabled
    if not is_action_enabled(action_id):
        reasons.append(f"action '{action_id}' is disabled")

    # 3. Risk level allowed
    if action.get("risk_level") not in EXECUTABLE_RISKS:
        reasons.append(
            f"risk level '{action.get('risk_level')}' is not executable (only LOW)"
        )

    # 4. Approval exists
    approval = approval_mod.get_approval(approval_id)
    if approval is None:
        reasons.append(f"approval '{approval_id}' not found")

    # 5. Approval valid for this action + inputs
    if approval is not None:
        validity = approval_mod.is_approval_valid_for(approval, action_id, inputs)
        if validity:
            reasons.append(f"approval invalid: {validity}")

    # 6. Approval not consumed (single-use)
    if approval is not None and approval.get("status") == "consumed":
        reasons.append("approval already consumed (single-use)")

    # 7. Input schema valid
    schema = action.get("input_schema", {})
    schema_errs = _validate_input_schema(inputs or {}, schema)
    if schema_errs:
        reasons.extend(schema_errs)

    # 8. Executor registered (ACTION_EXECUTORS is keyed by exact action_id)
    from nexus_agent_platform.governed.executors import ACTION_EXECUTORS
    if action_id not in ACTION_EXECUTORS:
        reasons.append(f"executor for '{action_id}' is not registered")

    # 9. Timeout bounded
    if action.get("timeout_seconds", 0) <= 0 or action.get("timeout_seconds", 99999) > 3600:
        reasons.append("action timeout_seconds is not within the bounded range (1..3600)")

    # 10. Idempotency
    if approval is not None:
        idem_key = _idempotency_key(approval, action_id)
        if wo.idempotency_key_executed(idem_key):
            reasons.append("idempotency key already executed — refusing duplicate execution")

    return (len(reasons) == 0, reasons)


def _idempotency_key(approval: Dict[str, Any], action_id: str) -> str:
    return f"{approval['id']}:{action_id}:1"


def _validate_input_schema(inputs: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    props = schema.get("properties", {})
    required = schema.get("required", [])
    for field in required:
        if field not in inputs:
            errs.append(f"required input '{field}' missing")
    # Reject unknown extra inputs to keep binding exact.
    if props:
        for field in inputs:
            if field not in props:
                errs.append(f"input '{field}' is not allowed for this action")
    return errs


def emit_block(work_order_id: str, action_id: str, reasons: List[str]) -> Dict[str, Any]:
    """Record a blocked work order + audit + telemetry proof of the block."""
    reason_text = "; ".join(reasons)
    entry = {
        "type": "execution_blocked",
        "work_order_id": work_order_id,
        "action_id": action_id,
        "reason": reason_text,
    }
    persistence.emit_audit_event(entry)
    try:
        from nexus_agent_platform.runtime import execution_telemetry as telemetry
        telemetry.emit_event(
            process_id=action_id.replace(".", "_"),
            process_name="Governed Work Order",
            worker_id="policy_gate",
            agent_id="nexus_governed",
            execution_type="policy_gate_block",
            event_type="blocked",
            status="blocked",
            source="scripts/nexus_agent_platform/governed/policy_gate.py:emit_block",
            metadata={
                "work_order_id": work_order_id,
                "action_id": action_id,
                "reason": reason_text[:300],
            },
        )
    except Exception:
        pass
    return {"work_order_id": work_order_id, "blocked": True, "reasons": reasons}