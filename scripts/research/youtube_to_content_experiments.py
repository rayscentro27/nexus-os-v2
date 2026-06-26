#!/usr/bin/env python3
"""Convert YouTube research into internal content experiment candidates."""
from __future__ import annotations

import argparse
import json

from common import ROOT, now, read_json, write_live_tasks, write_report

RUNTIME = ROOT / "reports" / "runtime" / "youtube_to_content_experiments_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "youtube_to_content_experiments_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    parser.set_defaults(dry_run=True)
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
    experiments = []
    for idx, item in enumerate(items[: max(1, min(args.limit, 25))], 1):
        blob = json.dumps(item).lower()
        department = "trading" if "trading" in blob else "goclear" if "funding" in blob or "credit" in blob else "seo"
        experiments.append({
            "title": f"YouTube experiment {idx}: {item.get('title', item.get('video_title', 'research item'))}"[:140],
            "source_url": item.get("source_url") or item.get("video_url"),
            "owner_tab": department,
            "score": item.get("score", item.get("project_enrichment", {}).get("score", 50)),
            "summary": "Internal YouTube-derived content experiment candidate.",
            "recommendation": "Create internal test plan only; publish/send requires later approval.",
            "next_action": "Draft a small experiment card and review after results.",
            "proof_source": "youtube_research_report_latest.json",
            "unique_key": f"youtube_content_experiment:{idx}:{item.get('source_url') or item.get('video_url')}",
            "project_enrichment": {
                "enrichment_status": "scored",
                "summary": "Internal YouTube-derived content experiment candidate.",
                "score": item.get("score", item.get("project_enrichment", {}).get("score", 50)),
                "score_label": "medium",
                "category": "youtube_content_experiment",
                "destination": "Trading Lab" if department == "trading" else "GoClear / Apex" if department == "goclear" else "SEO / Marketing",
                "pros": ["Turns research into a testable internal hypothesis."],
                "cons": ["Execution and publishing remain approval-gated."],
                "recommendation": "Create internal test plan only; publish/send requires later approval.",
                "proposed_schedule": "Manual review in next department digest.",
                "next_action": "Draft a small experiment card and review after results.",
                "confidence": 0.7,
                "risk_triggers": ["paper_only_required"] if department == "trading" else [],
                "approval_required": False,
                "hermes_memory_summary": "YouTube research converted into internal experiment candidate.",
                "source_summary": "YouTube research conversion",
                "enrichment_source": "deterministic",
                "paper_only": department == "trading",
                "live_trading_blocked": department == "trading",
            },
        })
    live = {"created": 0, "duplicates": 0, "failed": 0, "results": []}
    if not args.dry_run:
        live = write_live_tasks(experiments, "youtube_content_experiment", "youtube_to_content_experiments", "content_experiment", min(args.limit, 10))
    report = {
        "ok": True,
        "title": "YouTube to Content Experiments",
        "generated_at": now(),
        "dry_run": args.dry_run,
        "experiments": experiments,
        "counts": {"experiments": len(experiments), **{k: live.get(k, 0) for k in ("created", "duplicates", "failed")}},
        "summary": "Generated internal YouTube-to-content experiment candidates. No outbound action.",
        "live": live,
        "safety": {"publish_send_trade_deploy": False, "external_ai_called": False, "ray_review_queue_flood": False},
    }
    write_report(report, RUNTIME, MANUAL, args.report_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
