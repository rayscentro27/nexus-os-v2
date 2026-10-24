#!/usr/bin/env python3
"""Short-lived bounded dispatcher; department execution happens in children."""
from __future__ import annotations
import json
import os
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

def _initialize_dispatch_egress_context() -> None:
    """Give short-lived dispatcher control-plane reads a fresh accounting window.

    feeder_runtime assigns a process-scoped fallback job ID for legacy calls.
    PID reuse could otherwise inherit the prior process's egress counters and
    make an unrelated dispatcher wake fail before it reaches the queue.
    Durable job workers replace this context with their actual job/execution IDs.
    """
    os.environ.setdefault("NEXUS_DURABLE_EXECUTION_ID", f"dispatcher-{os.getpid()}-{time.time_ns()}")

_initialize_dispatch_egress_context()
from nexus_agent_platform.durable_jobs import default_store, dispatch_once
from nexus_agent_platform.job_health import persist_snapshot

def main() -> int:
    store = default_store()
    store.recover_expired()
    try:
        from nexus_agent_platform.research_parent_workflow import recover_orphaned_parents
        parent_watchdog = recover_orphaned_parents(store)
    except Exception as exc:
        # Preserve normal dispatch availability; the next interval retries
        # the idempotent parent scan and surfaces the exact diagnostic.
        parent_watchdog = {"status": "UNAVAILABLE", "error": f"{type(exc).__name__}: {str(exc)[:180]}"}
    allow_raw = os.environ.get("NEXUS_DISPATCH_ALLOWED_JOB_IDS")
    allowed_job_ids = {value.strip() for value in allow_raw.split(",") if value.strip()} if allow_raw else None
    source_raw = os.environ.get("NEXUS_DISPATCH_ALLOWED_JOB_SOURCES")
    allowed_job_sources = {value.strip() for value in source_raw.split(",") if value.strip()} if source_raw else None
    result = dispatch_once(store, allowed_job_ids=allowed_job_ids, allowed_job_sources=allowed_job_sources)
    snapshot = persist_snapshot()
    health = {key: snapshot.get(key) for key in (
        "generated_at", "runtime_mode", "dispatcher", "ready", "running", "blocked",
        "failed_retryable", "expired_leases", "active_worker_count", "oldest_queued_age_seconds",
    )}
    print(json.dumps({**result, "research_parent_watchdog": parent_watchdog,
                      "health": health}, separators=(",", ":")))
    return 0

if __name__ == "__main__": raise SystemExit(main())
