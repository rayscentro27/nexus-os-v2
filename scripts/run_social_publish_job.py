#!/usr/bin/env python3
"""Nexus OS v2 — social publish job executor (manual script, NOT a scheduler).

Finds (or takes) one queued agent_jobs row of job_type 'social_publish', runs the Facebook
publisher adapter on its post, updates the job, and writes nexus_events.

DRY-RUN by default. Real publish requires --real-publish AND passes all adapter gates
(approval=approved, account=Clear Credentials, env token present, publish_enabled=true).

Usage:
    python3 scripts/run_social_publish_job.py [--job-id <uuid>] [--real-publish]
    # macOS SSL: SSL_CERT_FILE="$(python3 -m certifi)" python3 scripts/run_social_publish_job.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "social"))
from _supabase import configured, get, update, event, q  # noqa: E402
import facebook_publisher  # noqa: E402


def _find_job(job_id: str | None):
    if job_id:
        st, rows = get("agent_jobs", f"id=eq.{q(job_id)}&limit=1")
    else:
        st, rows = get("agent_jobs", "job_type=eq.social_publish&status=eq.queued&order=created_at.asc&limit=1")
    return rows[0] if isinstance(rows, list) and rows else None


def main() -> int:
    ap = argparse.ArgumentParser(description="Run a social_publish job (dry-run by default).")
    ap.add_argument("--job-id")
    ap.add_argument("--real-publish", action="store_true", help="attempt a real publish (still gated)")
    ap.add_argument("--dry-run", action="store_true", help="explicit dry-run (default behavior)")
    args = ap.parse_args()

    if not configured():
        print("SETUP NEEDED: SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY required in .env (not printed).")
        return 2

    job = _find_job(args.job_id)
    if not job:
        print("No queued social_publish job found (and no --job-id). Nothing to do.")
        return 0

    post_id = (job.get("input") or {}).get("post_id")
    if not post_id:
        update("agent_jobs", f"id=eq.{q(job['id'])}", {"status": "failed", "error": "no post_id in job input",
                "updated_at": datetime.now(timezone.utc).isoformat()})
        print("Job has no post_id in input — marked failed.")
        return 1

    update("agent_jobs", f"id=eq.{q(job['id'])}", {"status": "running", "locked_by": "run_social_publish_job",
            "locked_at": datetime.now(timezone.utc).isoformat()})

    result = facebook_publisher.publish(post_id, real_publish=bool(args.real_publish))

    done = result.get("ok") and (result.get("mode") == "dry_run" or result.get("published"))
    update("agent_jobs", f"id=eq.{q(job['id'])}", {
        "status": "done" if done else "failed",
        "output": result,
        "error": None if done else (result.get("blocker") or result.get("error") or "publish not completed"),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    event("automation", "social_publish_job", "success" if done else "failed",
          f"social_publish job {'done' if done else 'failed'} ({result.get('mode')})",
          json.dumps({k: v for k, v in result.items() if k != "error"})[:200], job_id=job["id"])

    print(json.dumps({"job_id": job["id"], "post_id": post_id, **result}, indent=2))
    return 0 if done else 1


if __name__ == "__main__":
    raise SystemExit(main())
