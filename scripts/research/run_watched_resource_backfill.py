#!/usr/bin/env python3
"""Bounded watched resource backfill v1.

No broad scraping. Uses approved/manual fixture data to create candidate research cards.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ROOT, candidate, now, read_json, write_live_tasks, write_report

FIXTURE = ROOT / "tests" / "fixtures" / "research" / "sample_watched_resources.json"
RUNTIME = ROOT / "reports" / "runtime" / "watched_resource_backfill_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "watched_resource_backfill_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    parser.set_defaults(dry_run=True)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--items-per-resource", type=int, default=3)
    parser.add_argument("--input-file", default=str(FIXTURE))
    parser.add_argument("--no-external-ai", action="store_true", default=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()
    if not args.no_external_ai:
        print(json.dumps({"ok": False, "error": "no_external_ai_required"}, indent=2))
        return 2
    input_path = Path(args.input_file)
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    resources = read_json(input_path)[: max(1, min(args.limit, 10))]
    items = []
    for row in resources:
        per_resource = max(1, min(args.items_per_resource, 5))
        for idx in range(1, per_resource + 1):
            item = candidate(
                f"Backfill candidate {idx}: {row['resource_name']}",
                f"{row['resource_url'].rstrip('/')}/sample-backfill-{idx}",
                row["category"].replace("_", " ").replace("|", " "),
                source_type=row["resource_type"],
                proof_source=str(input_path.relative_to(ROOT)),
            )
            item["unique_key"] = f"watched_backfill:{row['resource_id']}:sample-{idx}"
            item["recommendation"] = "Backfill is metadata-candidate only in this dry-run. Transcript review will run only from explicit safe transcript files or future bounded connector output."
            item["transcript_review_available"] = False
            item["scoring_categories"] = [
                "money_potential", "goclear_apex_relevance", "seo_potential", "affiliate_potential",
                "content_potential", "implementation_difficulty", "compliance_risk", "urgency", "uniqueness", "testability",
            ]
            if "trading" in row["category"].lower():
                item["scoring_categories"] = [
                    "paper_strategy_potential", "clarity_of_rules", "backtestability", "risk_reward_discussion",
                    "drawdown_risk_caution", "market_specificity", "educational_value", "compliance_safety_risk",
                ]
                item["project_enrichment"]["paper_only"] = True
                item["project_enrichment"]["live_trading_blocked"] = True
            item["approval_required"] = False
            items.append(item)
    live = {"created": 0, "duplicates": 0, "failed": 0, "results": []}
    if not args.dry_run:
        live = write_live_tasks(items, "watched_resource_update", "watched_resource_backfill", "watched_resource_update", args.limit)
    report = {
        "ok": True, "title": "Watched Resource Backfill", "generated_at": now(), "dry_run": args.dry_run,
        "items": items,
        "channels_considered": len(resources),
        "items_per_resource": max(1, min(args.items_per_resource, 5)),
        "counts": {"channels_considered": len(resources), "proposed_items": len(items), **{k: live.get(k, 0) for k in ("created", "duplicates", "failed")}},
        "summary": "Backfill mode simulated bounded metadata-only historical review from explicit fixture/manual input; no scraping/capture/media download.",
        "safety": {"approval_required_for_internal_research": False, "ray_review_queue_flood": False, "scheduler_started": False, "media_downloaded": False, "broad_scraping": False, "external_ai_called": False},
        "live": live,
    }
    write_report(report, RUNTIME, MANUAL, args.report_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
