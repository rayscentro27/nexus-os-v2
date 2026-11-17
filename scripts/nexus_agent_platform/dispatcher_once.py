#!/usr/bin/env python3
"""Short-lived bounded dispatcher; department execution happens in children."""
from __future__ import annotations
import json
import os
import sys
import time
from datetime import datetime, timezone
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

def _egress_counters() -> dict:
    try:
        from nexus_agent_platform.supabase_egress_guard import job_egress_snapshot
        snap = job_egress_snapshot(os.environ.get("NEXUS_DURABLE_JOB_ID", ""))
        return {"requests_used": snap.get("attempt_request_count", 0),
                "response_bytes": snap.get("attempt_response_bytes", 0)}
    except Exception:
        return {}


def main() -> int:
    started_at = time.monotonic()
    from nexus_agent_platform.supabase_egress_guard import JobEgressBudgetExceeded, JOB_MAX_REQUESTS, JOB_MAX_RESPONSE_BYTES
    budget = {"max_requests": JOB_MAX_REQUESTS, "max_response_bytes": JOB_MAX_RESPONSE_BYTES}
    stage = "recover_expired"
    try:
        store = default_store()
        stale_reclaimed = store.recover_expired()
        stage = "research_parent_watchdog"
        try:
            from nexus_agent_platform.research_parent_workflow import recover_orphaned_parents
            parent_watchdog = recover_orphaned_parents(store)
        except JobEgressBudgetExceeded:
            raise
        except Exception as exc:
            # Preserve normal dispatch availability; the next interval retries
            # the idempotent parent scan and surfaces the exact diagnostic.
            parent_watchdog = {"status": "UNAVAILABLE", "error": f"{type(exc).__name__}: {str(exc)[:180]}"}
        allow_raw = os.environ.get("NEXUS_DISPATCH_ALLOWED_JOB_IDS")
        allowed_job_ids = {value.strip() for value in allow_raw.split(",") if value.strip()} if allow_raw else None
        source_raw = os.environ.get("NEXUS_DISPATCH_ALLOWED_JOB_SOURCES")
        allowed_job_sources = {value.strip() for value in source_raw.split(",") if value.strip()} if source_raw else None
        stage = "dispatch"
        result = dispatch_once(store, allowed_job_ids=allowed_job_ids, allowed_job_sources=allowed_job_sources)
        stage = "health_snapshot"
        snapshot = persist_snapshot()
    except JobEgressBudgetExceeded:
        # Bounded receipt instead of a traceback crash loop: no job is lost
        # (claims are atomic RPCs; unclaimed work stays durable) and the next
        # 30s interval starts with a fresh per-run accounting window.
        print(json.dumps({"status": "BUDGET_EXHAUSTED", "stage": stage,
                          "at": datetime.now(timezone.utc).isoformat(), "budget": budget,
                          **_egress_counters(),
                          "total_seconds": round(time.monotonic() - started_at, 2)}, separators=(",", ":")))
        return 0
    health = {key: snapshot.get(key) for key in (
        "generated_at", "runtime_mode", "dispatcher", "ready", "running", "blocked",
        "failed_retryable", "expired_leases", "active_worker_count", "oldest_queued_age_seconds",
    )}
    run = {"status": "OK", **_egress_counters(), "budget": budget,
           "jobs_scanned": result.get("scanned"), "jobs_claimable": result.get("claimable"),
           "jobs_claimed": result.get("started"), "jobs_retried": result.get("retried"),
           "jobs_skipped_blocked": snapshot.get("blocked"), "stale_leases_reclaimed": stale_reclaimed,
           "total_seconds": round(time.monotonic() - started_at, 2)}
    print(json.dumps({**result, "research_parent_watchdog": parent_watchdog,
                      "health": health, "run": run}, separators=(",", ":")))
    return 0

if __name__ == "__main__": raise SystemExit(main())
