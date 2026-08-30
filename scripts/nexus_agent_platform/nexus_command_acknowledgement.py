"""Machine-readable acknowledgement contract for Nova-to-Nexus commands."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from nexus_agent_platform.governed import persistence


TERMINAL_STATES = {"COMPLETED", "BLOCKED", "REJECTED", "FAILED"}


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
