#!/usr/bin/env python3
"""Generate a safe YouTube research report from local dry-run/watch/transcript reports.

No YouTube network calls, media downloads, scraping, schedulers, external AI, or Ray Review Queue
creation. This prepares context Hermes can read later.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from common import ROOT, now, read_json, write_report

RUNTIME = ROOT / "reports" / "runtime" / "youtube_research_report_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "youtube_research_report_latest.md"
RAY_FIXTURE = ROOT / "tests" / "fixtures" / "research" / "ray_watched_youtube_channels.json"


def load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return read_json(path)
    except Exception:
        return {}


def item_score(item: dict[str, Any]) -> int:
    if isinstance(item.get("score"), (int, float)):
        return int(item["score"])
    pe = item.get("project_enrichment") if isinstance(item.get("project_enrichment"), dict) else {}
    if isinstance(pe.get("score"), (int, float)):
        return int(pe["score"])
    return 0


def flatten_items(*reports: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for report in reports:
        for key in ("items", "top_items", "candidates"):
            value = report.get(key)
            if isinstance(value, list):
                out.extend([x for x in value if isinstance(x, dict)])
    return out


def channel_quality(channels: list[dict[str, Any]], items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for channel in channels:
        name = channel["resource_name"]
        related = [item for item in items if name.lower() in json.dumps(item).lower()]
        scores = [item_score(item) for item in related]
        rows.append({
            "channel": name,
            "resource_url": channel["resource_url"],
            "category": channel["category"],
            "enabled": channel.get("enabled") is True,
            "approved_by_ray": channel.get("approved_by_ray") is True,
            "candidate_count": len(related),
            "average_score": round(sum(scores) / len(scores), 1) if scores else None,
            "status": "manual_dry_run_ready",
        })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--mode", default="weekly", choices=[
        "weekly", "top-videos", "top-channels", "goclear-opportunities",
        "seo-affiliate-opportunities", "ai-automation-ideas", "trading-paper-ideas",
    ])
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--no-external-ai", action="store_true", default=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()
    if not args.no_external_ai:
        print(json.dumps({"ok": False, "error": "no_external_ai_required"}, indent=2))
        return 2
    limit = max(1, min(args.limit, 25))
    channels = read_json(RAY_FIXTURE)
    watch = load(ROOT / "reports" / "runtime" / "watched_resource_watch_latest.json")
    backfill = load(ROOT / "reports" / "runtime" / "watched_resource_backfill_latest.json")
    transcript = load(ROOT / "reports" / "runtime" / "youtube_transcript_review_latest.json")
    items = flatten_items(watch, backfill, transcript)
    top = sorted(items, key=item_score, reverse=True)[:limit]
    trading = [item for item in top if "trading" in json.dumps(item).lower()]
    report = {
        "ok": True,
        "title": "YouTube Research Report",
        "generated_at": now(),
        "dry_run": True,
        "mode": args.mode,
        "summary": f"Prepared a dry-run YouTube research report across {len(channels)} Ray-approved watched channels and {len(items)} local candidate/review items. No live YouTube lookup, media download, scheduler, external AI, or Ray Review Queue item creation occurred.",
        "channels": channels,
        "top_videos_or_candidates": top,
        "top_channels_by_opportunity_quality": channel_quality(channels, items),
        "top_goclear_content_opportunities": [item for item in top if "goclear" in json.dumps(item).lower() or "funding" in json.dumps(item).lower()],
        "top_seo_affiliate_opportunities": [item for item in top if "seo" in json.dumps(item).lower() or "affiliate" in json.dumps(item).lower()],
        "top_ai_automation_ideas": [item for item in top if "ai" in json.dumps(item).lower() or "automation" in json.dumps(item).lower()],
        "top_paper_only_trading_strategy_ideas": trading,
        "what_nexus_reviewed_autonomously": {
            "watch_candidates": len(watch.get("items", [])) if isinstance(watch.get("items"), list) else 0,
            "backfill_candidates": len(backfill.get("items", [])) if isinstance(backfill.get("items"), list) else 0,
            "transcript_reviews": transcript.get("counts", {}).get("reviews", 0) if isinstance(transcript.get("counts"), dict) else 0,
        },
        "what_needs_ray_decision": [],
        "what_ray_can_ignore_for_now": [
            "ordinary metadata candidates",
            "autonomous transcript scoring",
            "paper-only trading research unless it asks for live execution",
        ],
        "hermes_recommended_direction": "Start with Credit Plug for GoClear/SEO angles, compare Michael Ionita and Alec Delpuech for AI/online business experiments, and keep Stedman Waiters paper-only in Trading Lab.",
        "counts": {
            "watched_channels": len(channels),
            "enabled_channels": sum(1 for channel in channels if channel.get("enabled") is True),
            "items_considered": len(items),
            "top_items": len(top),
            "ray_review_items_created": 0,
        },
        "safety": {
            "scheduler_started": False,
            "media_downloaded": False,
            "broad_scraping": False,
            "external_ai_called": False,
            "ray_review_queue_flood": False,
            "publish_send_trade_deploy": False,
        },
    }
    write_report(report, RUNTIME, MANUAL, args.report_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
