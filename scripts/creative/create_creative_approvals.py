#!/usr/bin/env python3
"""Nexus OS v2 — create approval cards for scored creative assets (>= threshold).

For each creative_asset with status 'scored' and overall score >= threshold that has no
approval yet, create a content-aware approvals row (pending) with a rich payload the Approval
Center can preview, and link creative_assets.approval_id. Idempotent. No publishing.

Usage: python3 scripts/creative/create_creative_approvals.py [--min-score 72] [--campaign-key ...]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "social"))
from _supabase import configured, get, insert, update, event, q  # noqa: E402

TYPE_MAP = {
    "facebook_post": "facebook_post", "instagram_caption": "instagram_caption",
    "reel_script": "reel_script", "tiktok_script": "tiktok_script", "carousel_outline": "carousel",
    "email_followup": "email", "lead_magnet_outline": "lead_magnet",
    "podcast_audio_overview_script": "audio_overview_script", "short_video_outline": "short_video",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-score", type=int, default=72)
    ap.add_argument("--campaign-key")
    args = ap.parse_args()
    if not configured():
        print("SETUP NEEDED: Supabase env required (not printed)."); return 2

    query = f"select=*&status=eq.scored&score=gte.{args.min_score}&order=score.desc&limit=100"
    if args.campaign_key:
        query += f"&payload->>campaign_key=eq.{q(args.campaign_key)}"
    st, assets = get("creative_assets", query)
    if not isinstance(assets, list):
        print("could not load creative_assets"); return 1

    made = []
    for a in assets:
        if a.get("approval_id"):
            made.append(f"{a['asset_type']}: approval exists"); continue
        item_type = TYPE_MAP.get(a["asset_type"], a["asset_type"])
        payload = {
            "asset_id": a["id"], "platform": a.get("platform"), "asset_type": a["asset_type"],
            "campaign_key": (a.get("payload") or {}).get("campaign_key"), "title": a.get("title"),
            "hook": a.get("hook"), "caption": a.get("body") or a.get("content"), "cta": a.get("cta"),
            "compliance_notes": (a.get("payload") or {}).get("compliance_notes"),
            "score_summary": (a.get("payload") or {}).get("score_summary"),
            "recommended_use": f"Draft {a['asset_type']} for {(a.get('payload') or {}).get('campaign_key')}",
        }
        st, row = insert("approvals", {
            "lane": "creative", "item_type": item_type, "item_id": a["id"], "status": "pending",
            "title": a.get("title") or item_type, "summary": (a.get("hook") or "")[:200], "payload": payload,
        })
        appr_id = row[0]["id"] if isinstance(row, list) and row else None
        update("creative_assets", f"id=eq.{a['id']}", {"approval_id": appr_id})
        made.append(f"{a['asset_type']}: approval created")

    event("monetization", "creative_approvals_created", "success", "Creative approvals created",
          ", ".join(made) or "none", payload={"campaign_key": args.campaign_key})
    print("Creative approval creation complete (all pending; nothing published).")
    for m in made:
        print("  -", m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
