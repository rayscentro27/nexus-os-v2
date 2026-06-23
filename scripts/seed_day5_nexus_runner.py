#!/usr/bin/env python3
"""Nexus OS v2 — Day 5 idempotent seed: queued jobs to prove the nexus_runner.

Seeds (idempotent by job_type + input.seed_key='day5'): creative_generate_assets,
creative_score_assets, creative_create_approvals, creative_create_social_drafts,
system_status, and one intentionally UNKNOWN job type to prove blocker behavior.
No real publish / trading / Telegram jobs.

    # macOS SSL: SSL_CERT_FILE="$(python3 -m certifi)" python3 scripts/seed_day5_nexus_runner.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "social"))
from _supabase import configured, get, insert, event  # noqa: E402

CK = "goclear_funding_readiness_review"
SEED = "day5"
JOBS = [
    ("creative_generate_assets", {"campaign_key": CK}),
    ("creative_score_assets", {"campaign_key": CK}),
    ("creative_create_approvals", {"campaign_key": CK}),
    ("creative_create_social_drafts", {"campaign_key": CK}),
    ("system_status", {}),
    ("totally_unknown_job_type", {"note": "intentional unknown to prove runner blocks it"}),
]


def main() -> int:
    if not configured():
        print("SETUP NEEDED: Supabase env required (not printed)."); return 2
    out = []
    for jt, extra in JOBS:
        st, existing = get("agent_jobs", f"job_type=eq.{jt}&input->>seed_key=eq.{SEED}&select=id&limit=1")
        if isinstance(existing, list) and existing:
            out.append(f"{jt}: exists"); continue
        lane = "creative" if jt.startswith("creative") else ("ops" if jt == "system_status" else "system")
        insert("agent_jobs", {"lane": lane, "job_type": jt, "status": "queued",
                              "input": {**extra, "seed_key": SEED}}, prefer="return=minimal")
        out.append(f"{jt}: queued")

    if not (get("nexus_events", "action=eq.day5_nexus_runner_seeded&select=id&limit=1")[1] or []):
        event("automation", "day5_nexus_runner_seeded", "success", "Day 5 nexus_runner seeded",
              "Queued creative/system_status/unknown jobs for the runner.")
        out.append("nexus_event: inserted")
    else:
        out.append("nexus_event: exists")

    print("Day 5 nexus_runner seed complete (no real publish/trading/Telegram).")
    for m in out:
        print("  -", m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
