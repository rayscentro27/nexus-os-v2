#!/usr/bin/env python3
"""Convert YouTube research candidates into SEO/affiliate plan candidates."""
from __future__ import annotations

import argparse
import json

from common import ROOT, now, read_json, write_report

RUNTIME = ROOT / "reports" / "runtime" / "youtube_to_seo_affiliate_plan_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "youtube_to_seo_affiliate_plan_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--no-dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--no-external-ai", action="store_true", default=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()
    if not args.no_external_ai:
        print(json.dumps({"ok": False, "error": "no_external_ai_required"}, indent=2))
        return 2
    yt_path = ROOT / "reports" / "runtime" / "youtube_research_report_latest.json"
    yt = read_json(yt_path) if yt_path.exists() else {}
    items = yt.get("top_videos_or_candidates", []) if isinstance(yt.get("top_videos_or_candidates"), list) else []
    plans = []
    for item in items[: max(1, min(args.limit, 25))]:
        blob = json.dumps(item).lower()
        target = "business funding readiness checklist" if "funding" in blob or "credit" in blob else "ai automation tools for small business" if "ai" in blob else "paper trading strategy education"
        plans.append({
            "source_video": item.get("source_url") or item.get("video_url"),
            "channel": item.get("title", "").split(":")[-1].strip() or "unknown",
            "target_keyword": target,
            "article_angle": f"How to evaluate {target}",
            "affiliate_offer_hint": "business credit/funding partner" if "funding" in target else "AI/SEO tool affiliate" if "ai" in target else "trading education tool, if compliant",
            "GoClear_offer_tie_in": "$97 readiness review" if "funding" in target else "",
            "CTA": "Request a readiness review" if "funding" in target else "Download the checklist",
            "compliance_note": "No guarantees; include education/disclosure language.",
            "recommended_department": "SEO / Marketing",
            "priority_score": item.get("score", item.get("project_enrichment", {}).get("score", 50)),
        })
    report = {
        "ok": True,
        "title": "YouTube to SEO Affiliate Plan",
        "generated_at": now(),
        "dry_run": not args.no_dry_run,
        "plans": plans,
        "counts": {"plans": len(plans), "created": 0, "duplicates": 0, "failed": 0},
        "summary": "Generated internal SEO/affiliate plan candidates from YouTube research. No public content created.",
        "safety": {"publish_send_trade_deploy": False, "external_ai_called": False, "ray_review_queue_flood": False},
    }
    write_report(report, RUNTIME, MANUAL, args.report_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
