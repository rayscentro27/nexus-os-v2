#!/usr/bin/env python3
"""nexus_runner — safe, bounded, manual executor for queued agent_jobs.

NOT a scheduler, NOT a daemon, NOT an infinite loop. It claims up to N eligible jobs, runs
ONLY allowlisted handlers (unknown types are blocked, never guessed), updates job + writes
nexus_events + a worker heartbeat, then STOPS.

Default is safe/dry-run. A real Facebook publish requires --real-publish AND all Day 3 adapter
gates. No Instagram, no Telegram, no trading.

Usage:
    python3 scripts/nexus_runner.py --once --limit 1 --dry-run     # default-safe
    python3 scripts/nexus_runner.py --once --limit 5 --dry-run
    python3 scripts/nexus_runner.py --job-id <uuid> --dry-run
    python3 scripts/nexus_runner.py --list-handlers
    # macOS SSL: SSL_CERT_FILE="$(python3 -m certifi)" python3 scripts/nexus_runner.py --once --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))             # for `import runner_handlers`
sys.path.insert(0, str(HERE / "social"))  # for _supabase
import _supabase as sb  # noqa: E402
from runner_handlers import REGISTRY, list_handlers  # noqa: E402

RUNNER_ID = "nexus_runner_local"
ELIGIBLE = "status=in.(queued,stubbed)"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def claim(job: dict) -> dict | None:
    """Atomically claim a job only if it's still queued/stubbed. Returns the claimed row or None."""
    attempts = (job.get("attempts") or 0) + 1
    st, rows = sb.rest("PATCH", f"agent_jobs?id=eq.{job['id']}&{ELIGIBLE}", body={
        "status": "running", "claimed_by": RUNNER_ID, "claimed_at": now(),
        "started_at": now(), "attempts": attempts, "updated_at": now(),
    }, prefer="return=representation")
    return rows[0] if isinstance(rows, list) and rows else None


def finalize(job_id: str, result: dict) -> None:
    status = result.get("status", "failed")
    sb.rest("PATCH", f"agent_jobs?id=eq.{job_id}", body={
        "status": status, "output": result.get("output") or {},
        "error": result.get("error"), "last_error": result.get("error"),
        "completed_at": now(), "updated_at": now(),
    }, prefer="return=minimal")


def main() -> int:
    ap = argparse.ArgumentParser(description="Safe manual executor for queued agent_jobs.")
    ap.add_argument("--once", action="store_true", help="run a single bounded pass (default)")
    ap.add_argument("--limit", type=int, default=1)
    ap.add_argument("--job-id")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--real-publish", action="store_true", help="allow a real FB publish (still gated)")
    ap.add_argument("--allow-risky", action="store_true", help="reserved; default off")
    ap.add_argument("--list-handlers", action="store_true")
    args = ap.parse_args()

    if args.list_handlers:
        print(json.dumps(list_handlers(), indent=2))
        return 0
    if not sb.configured():
        print("SETUP NEEDED: SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY required in .env (not printed).")
        return 2

    ctx = {"dry_run": not args.real_publish, "real_publish": bool(args.real_publish),
           "allow_risky": bool(args.allow_risky)}
    sb.event("automation", "runner_started", "info", "nexus_runner started",
             f"limit={args.limit} real_publish={ctx['real_publish']}")
    sb.insert("worker_heartbeats", {"worker_key": RUNNER_ID, "status": "running",
              "last_seen_at": now(), "metadata": {"ctx": ctx}}, prefer="return=minimal")

    # gather eligible jobs
    if args.job_id:
        st, jobs = sb.get("agent_jobs", f"id=eq.{args.job_id}&limit=1")
    else:
        st, jobs = sb.get("agent_jobs", f"{ELIGIBLE}&order=priority.asc,created_at.asc&limit={args.limit}")
    jobs = jobs if isinstance(jobs, list) else []

    summary = []
    for job in jobs:
        jt = job.get("job_type")
        # attempts guard
        if (job.get("attempts") or 0) >= (job.get("max_attempts") or 1):
            finalize(job["id"], {"status": "blocked", "output": {}, "error": "max_attempts reached"})
            sb.event("automation", "job_blocked", "failed", f"job blocked: {jt}", "max_attempts reached", job_id=job["id"])
            summary.append((jt, "blocked:max_attempts")); continue

        claimed = claim(job)
        if not claimed:
            summary.append((jt, "skip:already_claimed")); continue
        sb.event("automation", "job_claimed", "info", f"job claimed: {jt}", f"by {RUNNER_ID}", job_id=job["id"])

        handler = REGISTRY.get(jt)
        if not handler:
            finalize(job["id"], {"status": "blocked", "output": {"reason": "unknown_job_type"},
                                 "error": f"unknown_job_type:{jt}"})
            sb.event("automation", "job_blocked", "failed", f"job blocked: {jt}",
                     "unknown job type — not in allowlist", job_id=job["id"])
            summary.append((jt, "blocked:unknown")); continue

        fn, _risky = handler
        try:
            result = fn(claimed, ctx)
        except Exception as exc:  # noqa: BLE001
            result = {"status": "failed", "output": {}, "error": str(exc)[:300]}
        finalize(job["id"], result)
        ev_status = "success" if result.get("status") == "done" else ("failed" if result.get("status") == "failed" else "pending")
        sb.event("automation", f"job_{result.get('status')}", ev_status, f"job {result.get('status')}: {jt}",
                 (result.get("error") or json.dumps(result.get("output") or {}))[:200], job_id=job["id"])
        summary.append((jt, result.get("status")))

    sb.insert("worker_heartbeats", {"worker_key": RUNNER_ID, "status": "ok", "last_seen_at": now(),
              "metadata": {"processed": len(summary)}}, prefer="return=minimal")
    sb.event("automation", "runner_finished", "success", "nexus_runner finished",
             f"processed {len(summary)} job(s)")
    print(json.dumps({"processed": len(summary), "results": [{"job_type": t, "status": s} for t, s in summary]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
