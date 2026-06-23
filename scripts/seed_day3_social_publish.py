#!/usr/bin/env python3
"""Nexus OS v2 — Day 3 idempotent proof seed for the approval-gated Facebook publish flow.

Creates (idempotent, keyed by payload.seed_key / stable markers):
  - one approved approval (item_type 'social_publish')
  - one sample Facebook social_posts row for Clear Credentials (linked to account + approval)
  - one queued agent_jobs row of type 'social_publish' (input.post_id) for a DRY-RUN
  - one nexus_events 'day3_social_publish_foundation_seeded'

No real publish. Caption is compliance-friendly (includes a no-guarantee line).
    # macOS SSL: SSL_CERT_FILE="$(python3 -m certifi)" python3 scripts/seed_day3_social_publish.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "social"))
from _supabase import configured, get, insert, event, q  # noqa: E402

SEED_KEY = "day3_fb_sample"
CAPTION = ("Before you apply for business funding, check your readiness first. Nexus helps you "
           "identify the blockers that may be holding your business back. No guarantees — just a "
           "clearer plan. Comment READY for the checklist.")


def find_one(table: str, query: str):
    st, rows = get(table, query + "&limit=1")
    return rows[0] if isinstance(rows, list) and rows else None


def main() -> int:
    if not configured():
        print("SETUP NEEDED: Supabase env required (not printed)."); return 2
    out = []

    fb = find_one("social_accounts", "platform=eq.facebook&account_id=eq.131069194210954")
    if not fb:
        print("BLOCKER: Facebook social_account (Clear Credentials) not found — run earlier seeds first.")
        return 1
    account_id = fb["id"]

    # 1) approval (approved, so the dry-run shows a fully-gated path; real publish still blocked)
    appr = find_one("approvals", "item_type=eq.social_publish&title=eq." + q("Approve sample Facebook readiness post"))
    if not appr:
        st, rows = insert("approvals", {
            "lane": "social", "item_type": "social_publish", "status": "approved",
            "title": "Approve sample Facebook readiness post",
            "summary": "Sample compliance-safe FB post for the Day 3 dry-run pipeline.",
            "approved_by": "seed_day3", "decided_at": datetime.now(timezone.utc).isoformat(),
            "payload": {"platform": "facebook", "caption": CAPTION, "seed_key": SEED_KEY},
        })
        appr = rows[0] if isinstance(rows, list) and rows else None
        out.append("approval: inserted")
    else:
        out.append("approval: exists")
    approval_id = appr["id"] if appr else None

    # 2) social_posts (idempotent by payload.seed_key)
    post = find_one("social_posts", "payload->>seed_key=eq." + SEED_KEY)
    if not post:
        st, rows = insert("social_posts", {
            "platform": "facebook", "account_id": account_id, "content": CAPTION,
            "status": "approved", "approval_id": approval_id, "score": None,
            "payload": {"seed_key": SEED_KEY, "campaign_key": "goclear_q3_funding_readiness",
                        "account_name": "Clear Credentials"},
        })
        post = rows[0] if isinstance(rows, list) and rows else None
        out.append("social_post: inserted")
    else:
        out.append("social_post: exists")
    post_id = post["id"] if post else None

    # 3) queued dry-run job (idempotent by input.seed_key)
    job = find_one("agent_jobs", "job_type=eq.social_publish&input->>seed_key=eq." + SEED_KEY)
    if not job:
        insert("agent_jobs", {
            "lane": "social", "job_type": "social_publish", "status": "queued",
            "input": {"post_id": post_id, "seed_key": SEED_KEY, "mode": "dry_run"},
        }, prefer="return=minimal")
        out.append("agent_job: inserted (queued dry-run)")
    else:
        out.append("agent_job: exists")

    # 4) proof event (idempotent by action)
    existing = find_one("nexus_events", "action=eq.day3_social_publish_foundation_seeded")
    if not existing:
        event("social", "day3_social_publish_foundation_seeded", "success",
              "Day 3 social publish foundation seeded",
              "Sample approved FB post + queued dry-run job (no real publish).",
              payload={"post_id": post_id, "approval_id": approval_id})
        out.append("nexus_event: inserted")
    else:
        out.append("nexus_event: exists")

    print("Day 3 social publish seed complete (no real publish, no Telegram, no trading).")
    for line in out:
        print("  -", line)
    print("  post_id:", post_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
