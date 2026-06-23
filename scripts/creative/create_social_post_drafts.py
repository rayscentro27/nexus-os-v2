#!/usr/bin/env python3
"""Nexus OS v2 — convert approved/approval-ready facebook_post creative assets into
social_posts DRAFTS (Clear Credentials). Does NOT create a publish job and does NOT publish.

Idempotent (one draft per asset via payload.creative_asset_id). Links the social_posts row to
the asset's approval where present. status = 'draft'. No publishing, no Telegram, no trading.

Usage: python3 scripts/creative/create_social_post_drafts.py [--campaign-key ...]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "social"))
from _supabase import configured, get, insert, event, q  # noqa: E402

FB_PAGE_ID = "131069194210954"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign-key")
    args = ap.parse_args()
    if not configured():
        print("SETUP NEEDED: Supabase env required (not printed)."); return 2

    st, accs = get("social_accounts", f"platform=eq.facebook&account_id=eq.{FB_PAGE_ID}&select=id&limit=1")
    if not (isinstance(accs, list) and accs):
        print("BLOCKER: Facebook account (Clear Credentials) not found."); return 1
    account_id = accs[0]["id"]

    query = "select=*&asset_type=eq.facebook_post&order=created_at.desc&limit=50"
    if args.campaign_key:
        query += f"&payload->>campaign_key=eq.{q(args.campaign_key)}"
    st, assets = get("creative_assets", query)
    made = []
    for a in (assets if isinstance(assets, list) else []):
        st, existing = get("social_posts", f"payload->>creative_asset_id=eq.{a['id']}&select=id&limit=1")
        if isinstance(existing, list) and existing:
            made.append("facebook_post: draft exists"); continue
        insert("social_posts", {
            "platform": "facebook", "account_id": account_id,
            "content": a.get("body") or a.get("content"), "status": "draft",
            "approval_id": a.get("approval_id"),
            "payload": {"creative_asset_id": a["id"], "campaign_key": (a.get("payload") or {}).get("campaign_key"),
                        "account_name": "Clear Credentials"},
        }, prefer="return=minimal")
        made.append("facebook_post: draft created")

    event("social", "creative_social_drafts_created", "success", "Facebook drafts created from creative assets",
          ", ".join(made) or "none", payload={"campaign_key": args.campaign_key})
    print("Social draft creation complete (drafts only — no publish job, no publish).")
    for m in made:
        print("  -", m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
