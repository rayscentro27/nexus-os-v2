"""Machine-readable acknowledgement contract for Nova-to-Nexus commands."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import hashlib
import json
from pathlib import Path

from nexus_agent_platform.governed import persistence


TERMINAL_STATES = {"COMPLETED", "BLOCKED", "REJECTED", "FAILED"}
ROOT = Path(__file__).resolve().parents[2]
SAFE_CONTROL_REQUESTS = ROOT / "data/runtime/nova_control_requests.jsonl"


def acknowledge_command(request_id: str, *, authority_status: str,
                        current_state: str, receipt: Optional[str] = None,
                        work_order_id: Optional[str] = None,
                        assigned_department: Optional[str] = None,
                        assigned_worker_or_queue: Optional[str] = None,
                        status: str = "RECEIVED") -> Dict[str, Any]:
    """Build an acknowledgement without claiming execution or completion."""
    if status not in {"RECEIVED", "ASSIGNED", "QUEUED", "STARTED", *TERMINAL_STATES}:
        raise ValueError("unsupported acknowledgement state")
    return {
        "command_received": True,
        "request_id": request_id,
        "work_order_id": work_order_id,
        "assigned_department": assigned_department,
        "assigned_worker_or_queue": assigned_worker_or_queue,
        "authority_status": authority_status,
        "current_state": current_state,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "receipt": receipt,
        "authority": "NEXUS_TRUTHKERNEL",
    }


def submit_nexus_request(*, summary: str, source: str = "hermes_nova",
                         referent: str = "") -> Dict[str, Any]:
    """Submit bounded intake to Nexus without executing an operation."""
    clean_summary = " ".join(str(summary or "").split())[:500]
    if not clean_summary:
        raise ValueError("request summary is required")
    request_id = persistence.new_id("nexus_req")
    record = {
        "request_id": request_id,
        "source": source,
        "summary": clean_summary,
        "referent": " ".join(str(referent or "").split())[:500],
        "authority_status": "PENDING_NEXUS_VALIDATION",
        "state": "RECEIVED",
        "execution_performed": False,
        "created_at": persistence._now(),
    }
    persistence.append_record("queue", record)
    audit = persistence.emit_audit_event({
        "type": "nexus_request_received",
        "request_id": request_id,
        "source": source,
        "execution_performed": False,
    })
    return acknowledge_command(
        request_id,
        authority_status=record["authority_status"],
        current_state=record["state"],
        status="RECEIVED",
        receipt=audit.get("event_id"),
    )


def assign_safe_internal_work(*, goal_id: str, summary: str, department: str = "",
                             requested_by: str = "hermes_nova") -> Dict[str, Any]:
    """Queue one allowlisted internal goal action for Active Operator pickup.

    This is a control-plane assignment, not arbitrary CRUD or execution.  The
    durable portfolio and continuation planner remain authoritative for the
    action; external/customer/financial actions cannot be selected here.
    """
    from nexus_agent_platform.goal_completion import active_objective_portfolio, next_work_for_active_goal

    clean_goal = str(goal_id or "").strip()
    clean_summary = " ".join(str(summary or "").split())[:500]
    goal = next((row for row in active_objective_portfolio() if row.get("goal_id") == clean_goal), None)
    if not goal or not clean_summary:
        return {"status": "invalid", "error": "eligible durable goal and summary are required"}
    if department and department != goal.get("department"):
        return {"status": "invalid", "error": "department does not match the canonical goal owner"}
    dispatch = next_work_for_active_goal(goal, work_item_id=f"nova_control:{clean_goal}", question=clean_summary, department=goal.get("department"))
    allowed = {"research.refresh", "trading.research_cycle", "internal.capability_verify", "ai.plan_and_verify", "funding.readiness_review"}
    if dispatch.get("action") not in allowed:
        return {"status": "blocked", "error": "goal has no allowlisted safe internal executor", "goal_id": clean_goal, "candidate_action": dispatch.get("action")}
    key = hashlib.sha256(f"{clean_goal}:{dispatch['action']}:{clean_summary}".encode()).hexdigest()[:24]
    SAFE_CONTROL_REQUESTS.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    try:
        existing = [json.loads(line) for line in SAFE_CONTROL_REQUESTS.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, ValueError):
        existing = []
    prior = next((row for row in existing if row.get("idempotency_key") == key and row.get("status") in {"QUEUED", "RUNNING", "COMPLETED"}), None)
    if prior:
        prior_status = str(prior["status"])
        return acknowledge_command(prior["request_id"], authority_status="INTERNAL_SAFE", current_state=prior_status, work_order_id=prior["work_order_id"], assigned_department=goal.get("department"), assigned_worker_or_queue="active_operator", status=prior_status, receipt=prior.get("request_id"))
    request_id = persistence.new_id("nova_control")
    record = {"request_id": request_id, "work_order_id": f"nwo_{key}", "goal_id": clean_goal,
              "department": goal.get("department"), "summary": clean_summary,
              "action": dispatch["action"], "status": "QUEUED", "requested_by": requested_by,
              "authority_status": "INTERNAL_SAFE", "idempotency_key": key,
              "external_side_effects": False, "created_at": persistence._now()}
    with SAFE_CONTROL_REQUESTS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    audit = persistence.emit_audit_event({"type": "nova_safe_internal_work_assigned", "request_id": request_id, "goal_id": clean_goal, "action": dispatch["action"], "external_side_effects": False})
    return acknowledge_command(request_id, authority_status="INTERNAL_SAFE", current_state="QUEUED", work_order_id=record["work_order_id"], assigned_department=record["department"], assigned_worker_or_queue="active_operator", status="QUEUED", receipt=audit.get("event_id"))
