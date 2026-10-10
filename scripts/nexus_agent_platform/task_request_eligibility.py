"""Fail-closed admission gate for legacy task_requests to durable execution."""
from __future__ import annotations

from typing import Any, Mapping


def task_request_is_dispatch_eligible(row: Mapping[str, Any]) -> bool:
    """Only an explicitly reviewed V2 migration may admit a task request.

    Historical state, a legacy status, or a credential never grants execution
    authority. The migration marker is metadata only and must be written by a
    separate reviewed migration process.
    """
    if not isinstance(row, Mapping):
        return False
    payload = row.get("payload")
    if not isinstance(payload, Mapping):
        return False
    return bool(
        str(row.get("status") or "").lower() in {"requested", "assigned", "approved"}
        and row.get("approved_by_ray")
        and payload.get("nexus_dispatch_eligibility") == "CURRENT_V2_MIGRATED"
        and payload.get("nexus_dispatch_migration_id")
        and payload.get("nexus_dispatch_migration_approved_by_ray")
    )
