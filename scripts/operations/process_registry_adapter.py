#!/usr/bin/env python3
"""
Append-only Nexus process registry adapter.

Local scripts use this adapter to emit truthful run records without requiring
Supabase. When remote connectivity is unavailable, records spool locally and
must not be presented as remote registry writes.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

SPOOL_PATH = Path("data/runtime/process_registry_spool.jsonl")
VALID_RUN_STATES = {
    "QUEUED",
    "RUNNING",
    "SUCCEEDED",
    "PARTIAL",
    "FAILED",
    "BLOCKED",
    "CANCELLED",
    "TIMED_OUT",
    "SIMULATED",
    "UNKNOWN",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_spool(record: Dict[str, Any], spool_path: Path = SPOOL_PATH) -> Path:
    spool_path.parent.mkdir(parents=True, exist_ok=True)
    with spool_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
    return spool_path


def emit_process_run(
    *,
    process_key: str,
    name: str,
    status: str,
    idempotency_key: str,
    entry_point: str,
    trigger_type: str,
    output_location: Optional[str] = None,
    items_attempted: int = 0,
    items_succeeded: int = 0,
    items_failed: int = 0,
    error_code: Optional[str] = None,
    error_message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    normalized_status = status.upper()
    if normalized_status not in VALID_RUN_STATES:
        normalized_status = "UNKNOWN"

    now = utc_now()
    record = {
        "registry_write": "local_spool",
        "remote_registry_updated": False,
        "process_definition": {
            "process_key": process_key,
            "name": name,
            "entry_point": entry_point,
            "trigger_type": trigger_type,
            "enabled": True,
            "execution_mode": "script",
            "is_mock": normalized_status == "SIMULATED",
            "updated_at": now,
        },
        "process_run": {
            "idempotency_key": idempotency_key,
            "status": normalized_status,
            "started_at": now,
            "completed_at": now if normalized_status not in {"QUEUED", "RUNNING"} else None,
            "heartbeat_at": now,
            "items_attempted": items_attempted,
            "items_succeeded": items_succeeded,
            "items_failed": items_failed,
            "output_location": output_location,
            "error_code": error_code,
            "error_message": error_message,
            "metadata": metadata or {},
            "created_at": now,
        },
    }
    append_spool(record)
    return record


def remote_registry_available() -> bool:
    return bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))
