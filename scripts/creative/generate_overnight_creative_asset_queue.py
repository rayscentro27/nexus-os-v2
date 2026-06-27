#!/usr/bin/env python3
"""Overnight creative asset queue (draft-only). Also emits landing-page + social-video idea reports."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "research"))
import money_opportunity_model as mo  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    items = mo.ranked()
    # Creative asset queue from top content/landing/social opportunities.
    queue = []
    for o in items:
        kinds = []
        if o["scores"]["landing_page_potential"] >= 60: kinds.append("landing_page")
        if o["scores"]["tiktok_potential"] >= 60: kinds.append("tiktok_video")
        if o["scores"]["instagram_facebook_potential"] >= 60: kinds.append("ig_fb_post")
        if not kinds:
            continue
        queue.append({"opportunity_id": o["opportunity_id"], "title": o["title"], "asset_kinds": kinds,
                      "publish_status": "draft_only", "approval_required": True})
    aq = {
        "ok": True, "title": "Overnight Creative Asset Queue", "generated_at": mo.now(), "dry_run": True,
        "publish_status": "draft_only", "approval_required": True, "queue": queue,
        "counts": {"assets": len(queue)},
        "summary": f"{len(queue)} creative assets queued (draft-only). Nothing produced, uploaded, or published.",
        "safety": {**mo.SAFETY, "post_published": False, "video_uploaded": False, "external_action_performed": False},
    }
    mo.write_report("overnight_creative_asset_queue_latest", aq, ["## Creative asset queue (draft-only)"] +
                    [f"- {q['title']}: {', '.join(q['asset_kinds'])}" for q in queue])

    # Landing page ideas
    lp = [o for o in items if o["scores"]["landing_page_potential"] >= 60][:5]
    lpr = {
        "ok": True, "title": "Overnight Landing Page Ideas", "generated_at": mo.now(), "dry_run": True,
        "publish_status": "draft_only", "approval_required": True,
        "ideas": [{"title": o["title"], "landing_page_potential": o["scores"]["landing_page_potential"],
                   "angle": o["source_category"]} for o in lp],
        "counts": {"ideas": len(lp)},
        "summary": f"{len(lp)} landing page ideas (draft-only). Recommended first: {lp[0]['title'] if lp else 'n/a'}.",
        "safety": {**mo.SAFETY, "landing_page_deployed": False},
    }
    mo.write_report("overnight_landing_page_ideas_latest", lpr, ["## Landing page ideas (draft-only)"] +
                    [f"- [{o['scores']['landing_page_potential']}] {o['title']}" for o in lp])

    # Social video ideas
    sv = [o for o in items if o["scores"]["tiktok_potential"] >= 60 or o["scores"]["instagram_facebook_potential"] >= 60][:5]
    svr = {
        "ok": True, "title": "Overnight Social Video Ideas", "generated_at": mo.now(), "dry_run": True,
        "publish_status": "draft_only", "approval_required": True,
        "ideas": [{"title": o["title"], "tiktok_potential": o["scores"]["tiktok_potential"],
                   "instagram_facebook_potential": o["scores"]["instagram_facebook_potential"]} for o in sv],
        "counts": {"ideas": len(sv)},
        "summary": f"{len(sv)} social video ideas (draft-only). Recommended first TikTok: {sv[0]['title'] if sv else 'n/a'}.",
        "safety": {**mo.SAFETY, "video_uploaded": False, "post_published": False},
    }
    mo.write_report("overnight_social_video_ideas_latest", svr, ["## Social video ideas (draft-only)"] +
                    [f"- TikTok {o['scores']['tiktok_potential']} / IG-FB {o['scores']['instagram_facebook_potential']}: {o['title']}" for o in sv])

    print(json.dumps(aq, indent=2) if a.json else aq["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
