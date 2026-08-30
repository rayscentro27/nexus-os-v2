"""Machine-readable acknowledgement contract for Nova-to-Nexus commands."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional


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
