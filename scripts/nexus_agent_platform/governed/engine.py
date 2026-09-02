"""Governed loop engine — the canonical operate-the-loop orchestrator.

Chain:
    Nova recommend
    -> Ray explicitly approves
    -> approval record bound to action+inputs
    -> governed work order
    -> policy gate
    -> allowlisted executor
    -> verified execution telemetry
    -> Nova reviews result

NOVA REASONS. RAY AUTHORIZES. THE POLICY GATE DECIDES. THE EXECUTOR PERFORMS ONLY
REGISTERED ACTIONS. TELEMETRY PROVES WHAT HAPPENED. NOVA REVIEWS. NO CHAINED
AUTONOMY.
"""

from __future__ import annotations

import traceback
from typing import Any, Dict, List, Optional

from nexus_agent_platform.governed import approvals as approval_mod
from nexus_agent_platform.governed import policy_gate, work_orders as wo
from nexus_agent_platform.governed import persistence
from nexus_agent_platform.governed.action_registry import (
    EXECUTABLE_RISKS,
    get_action,
)
from nexus_agent_platform.governed.executors import (
    ExecutorTimeoutError,
    execute_with_timeout,
    get_executor,
)


def execute_approved_work_order(
    work_order_id: str,
    *,
    resolved_by: str = "ray",
) -> Dict[str, Any]:
    """Execute a governed work order that has a valid, bound approval.

    This is the ONLY execution entry point. It is owned by the runtime /
    executor layer, NOT by Nova's model. Nova can never call this directly with
    arbitrary content.
    """
    order = wo.get_work_order(work_order_id)
    if order is None:
        return {
            "status": "not_found",
            "work_order_id": work_order_id,
            "executed": False,
        }

    # If the order is currently running, refuse (idempotency / no double-run).
    if order.get("status") == "running":
        return {
            "status": "blocked",
            "work_order_id": work_order_id,
            "executed": False,
            "reason": "work order is already running",
        }

    action_id = order.get("action_id")
    inputs = order.get("inputs") or {}
    approval_id = order.get("approval_id")

    # ── Policy gate: deterministic validation before ANY execution ──
    allowed, reasons = policy_gate.check_execution(
        approval_id=approval_id,
        action_id=action_id,
        inputs=inputs,
    )
    if not allowed:
        policy_gate.emit_block(work_order_id, action_id, reasons)
        try:
            wo.transition(work_order_id, "blocked")
        except ValueError:
            pass
        return {
            "status": "blocked",
            "work_order_id": work_order_id,
            "action_id": action_id,
            "executed": False,
            "reasons": reasons,
        }

    action = get_action(action_id)
    timeout_seconds = action.get("timeout_seconds", 120) if action else 120

    # Finance is a single, advisory gate at the governed executor boundary.
    # It records the decision before execution and never receives publication,
    # payment, or live-trading authority.
    try:
        from nexus_agent_platform.finance.engine import finance_preflight
        finance_pre = finance_preflight(
            work_order_id,
            department=str(inputs.get("department") or action.get("department") if action else "OPERATIONS"),
            initiative_id=inputs.get("initiative_id"),
            campaign_id=inputs.get("campaign_id"),
            strategy_id=inputs.get("strategy_id"),
            envelope={"MAX_CASH_COST_USD": float((inputs.get("finance_budget") or {}).get("max_cash_cost_usd", 0))},
            estimated={"cash_cost_usd": float(inputs.get("estimated_cash_cost_usd", 0) or 0)},
            authority="INTERNAL_ONLY",
            resource_state=str(inputs.get("resource_state", "UNKNOWN")),
        )
        if finance_pre.get("decision") in {"BLOCK_BUDGET", "BLOCK_AUTHORITY", "BLOCK_RESOURCE", "UNKNOWN_REQUIRES_REVIEW"}:
            try:
                wo.transition(work_order_id, "blocked")
            except ValueError:
                pass
            return {"status": "blocked", "work_order_id": work_order_id, "action_id": action_id, "executed": False, "finance_preflight": finance_pre}
    except Exception as exc:
        # Finance failure must not silently permit spending; retain the work
        # order and make the accounting dependency visible to the operator.
        return {"status": "blocked", "work_order_id": work_order_id, "action_id": action_id, "executed": False, "reason": f"finance_preflight_failed:{exc}"}

    try:
        wo.transition(work_order_id, "running")
    except ValueError:
        return {
            "status": "blocked",
            "work_order_id": work_order_id,
            "action_id": action_id,
            "executed": False,
            "reason": f"invalid transition from '{order.get('status')}' to running",
        }

    executor = get_executor(action_id)
    if executor is None:
        wo.record_result(
            work_order_id, status="failed",
            error=f"executor '{action_id}' not registered",
        )
        return {
            "status": "failed",
            "work_order_id": work_order_id,
            "action_id": action_id,
            "executed": False,
            "blocked": False,
        }

    # ── Verified execution telemetry run ──
    from nexus_agent_platform.runtime.execution_telemetry import execution_run

    meta = {
        "work_order_id": work_order_id,
        "approval_id": approval_id,
        "action_id": action_id,
        "resolved_by": resolved_by,
    }
    try:
        with execution_run(
            process_id=action.get("telemetry_process_id", action_id.replace(".", "_")),
            process_name=action.get("name"),
            worker_id="nexus_governed_executor",
            agent_id="nexus_governed",
            execution_type="governed_work_order",
            source="scripts/nexus_agent_platform/governed/engine.py:execute_approved_work_order",
            metadata=meta,
        ) as run_id:
            result = execute_with_timeout(executor, inputs, timeout_seconds)
    except ExecutorTimeoutError as exc:
        _timeout_failure(work_order_id, action_id, str(exc), approval_id, meta)
        return {
            "status": "failed",
            "work_order_id": work_order_id,
            "action_id": action_id,
            "executed": True,
            "blocked": False,
            "error": str(exc),
            "timed_out": True,
        }
    except Exception as exc:
        error_message = str(exc) or exc.__class__.__name__
        _execution_failure(work_order_id, action_id, error_message, approval_id, meta)
        return {
            "status": "failed",
            "work_order_id": work_order_id,
            "action_id": action_id,
            "executed": True,
            "blocked": False,
            "error": error_message,
        }

    # Worker capacity is not a repair failure and must remain retryable.  The
    # executor returns this private machine contract only after its broker has
    # found no eligible worker (or a selected worker became unavailable).
    if result.get("_execution_status") == "WAITING_WORKER":
        try:
            wo.transition(work_order_id, "queued", result=result, error=None)
        except ValueError:
            wo.record_result(work_order_id, status="failed", error="invalid worker-capacity requeue transition")
            return {"status": "failed", "work_order_id": work_order_id, "action_id": action_id,
                    "executed": True, "blocked": False, "error": "invalid worker-capacity requeue transition"}
        return {"status": "waiting_worker", "work_order_id": work_order_id, "action_id": action_id,
                "executed": False, "blocked": False, "result": result}

    if result.get("_execution_status") == "REPAIR_FAILED":
        failed = wo.record_result(work_order_id, status="failed", result=result, error=result.get("failure"))
        _finance_postrun(work_order_id, inputs, "FAILED")
        return {"status": "failed", "work_order_id": work_order_id, "action_id": action_id,
                "executed": True, "blocked": False, "result": result, "order": failed}

    # ── Terminal success: consume single-use approval, record result ──
    approval_mod.mark_approval_consumed(approval_id)
    completed = wo.record_result(
        work_order_id,
        status="completed",
        result=result,
        error=None,
        telemetry_run_id=run_id,
    )
    _finance_postrun(work_order_id, inputs, "COMPLETED")
    return {
        "status": "completed",
        "work_order_id": work_order_id,
        "action_id": action_id,
        "executed": True,
        "result": result,
        "approval_id": approval_id,
        "telemetry_run_id": run_id,
        "order": completed,
    }


def _timeout_failure(work_order_id, action_id, error, approval_id, meta):
    try:
        from nexus_agent_platform.runtime.execution_telemetry import emit_event
        emit_event(
            process_id=action_id.replace(".", "_"),
            process_name="Governed Executor Timeout",
            worker_id="nexus_governed_executor",
            agent_id="nexus_governed",
            execution_type="governed_work_order",
            event_type="failed",
            status="failed",
            source="scripts/nexus_agent_platform/governed/engine.py:_timeout_failure",
            error_message=error[:300],
            error_type="ExecutorTimeoutError",
            metadata=meta,
        )
    except Exception:
        pass
    wo.record_result(work_order_id, status="failed", error=error, telemetry_run_id=None)
    _finance_postrun(work_order_id, {}, "FAILED")


def _execution_failure(work_order_id, action_id, error, approval_id, meta):
    wo.record_result(work_order_id, status="failed", error=error, telemetry_run_id=None)
    _finance_postrun(work_order_id, {}, "FAILED")


def _finance_postrun(work_order_id: str, inputs: Dict[str, Any], status: str) -> None:
    try:
        from nexus_agent_platform.finance.engine import finance_postrun
        finance_postrun(work_order_id, department=str(inputs.get("department", "OPERATIONS")),
                        initiative_id=inputs.get("initiative_id"),
                        estimated={"cash_cost_usd": float(inputs.get("estimated_cash_cost_usd", 0) or 0)},
                        actual={"cash_cost_usd": float(inputs.get("actual_cash_cost_usd", 0) or 0),
                                "model_tokens": int(inputs.get("model_tokens", 0) or 0),
                                "gpu_minutes": float(inputs.get("gpu_minutes", 0) or 0),
                                "storage_bytes": int(inputs.get("storage_bytes", 0) or 0)},
                        status=status, attempt=int(inputs.get("attempt", 1) or 1), retry_of=inputs.get("retry_of"))
    except Exception:
        # Execution truth remains in the governed work-order receipt; an
        # accounting error is surfaced by the missing Finance postrun record.
        return


# ═══════════════════════════════════════════════════════════════
# POST-EXECUTION REVIEW (Nova reasons over verified result)
# ═══════════════════════════════════════════════════════════════


def review_work_order(work_order_id: str) -> Dict[str, Any]:
    """Evaluate a completed work order: outcome vs expected, evidence, next step.

    Do NOT auto-launch the next action.
    """
    order = wo.get_work_order(work_order_id)
    if order is None:
        return {"status": "not_found", "work_order_id": work_order_id}
    masked = wo._mask_work_order(order)

    status = order.get("status")
    if status != "completed":
        return {
            "status": "not_verifiable",
            "work_order_id": work_order_id,
            "work_order_state": status,
            "outcome": "unknown",
            "message": "No verified terminal result to review yet.",
        }

    result = order.get("result") or {}
    expected = order.get("expected_outcome") or ""
    evidence = [
        {
            "kind": "execution_telemetry",
            "telemetry_run_id": order.get("telemetry_run_id"),
            "process_id": result.get("telemetry_process_id")
            or (get_action(order.get("action_id")) or {}).get("telemetry_process_id"),
        },
        {"kind": "execution_result", "summary": result.get("result_summary")},
        {"kind": "approval_consumed", "single_use": True},
    ]

    overall = result.get("overall_status") or (result.get("ok") and "ok")
    outcome = "unknown"
    if expected:
        norm_expected = expected.lower()
        if "healthy" in norm_expected and overall == "healthy":
            outcome = "met"
        elif "healthy" in norm_expected and overall in ("degraded", "partial", "unknown"):
            outcome = "partial"
        elif result.get("ok") is not None:
            outcome = "met" if result.get("ok") else "not_met"
    elif result.get("result_summary"):
        outcome = "met"

    remaining = ""
    if overall in ("degraded", "partial", "unknown"):
        remaining = (
            "Health coverage is partial or degraded; some services are not fully verified."
        )
    next_recommendation = (
        "Address the remaining degraded/unverified services; a fresh governed "
        "action would require another explicit approval."
        if remaining else "No immediate follow-up required; re-run a bounded study "
        "refresh later to keep system truth current."
    )

    review = {
        "status": "completed",
        "work_order_id": masked["work_order_id"],
        "action_id": masked["action_id"],
        "outcome": outcome,
        "evidence": evidence,
        "remaining_issue": remaining or None,
        "next_recommendation": next_recommendation,
        "no_auto_launch": True,
    }
    persistence.emit_audit_event({
        "type": "post_review_completed",
        "work_order_id": work_order_id,
        "action_id": masked["action_id"],
        "outcome": outcome,
    })
    return review
