#!/usr/bin/env python3
"""Affiliate opportunity tracker v1."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ROOT, candidate, now, read_csv, write_live_tasks, write_report

FIXTURE = ROOT / "tests" / "fixtures" / "research" / "sample_affiliate_programs.csv"
RUNTIME = ROOT / "reports" / "runtime" / "affiliate_opportunity_tracker_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "affiliate_opportunity_tracker_latest.md"


def make_item(row: dict, idx: int) -> dict:
    topic = row.get("category", "affiliate marketing").replace("_", " ")
    item = candidate(row["program_name"], row["affiliate_url"], topic, source_type="affiliate_program_page", proof_source=row.get("proof_source", str(FIXTURE.relative_to(ROOT))))
    item.update({
        "unique_key": f"affiliate:{row['program_name']}",
        "title": f"Affiliate opportunity: {row['program_name']}",
        "summary": f"{row['program_name']} may support {row.get('content_angle')} with {row.get('commission_type')} payout.",
        "recommendation": "Review terms manually before making claims; route to SEO/Opportunity/GoClear if relevant.",
        "next_action": "Create a content test or park until terms are proofed.",
        "owner_tab": "opportunities",
        "affiliate_program": row,
    })
    item["project_enrichment"]["category"] = "affiliate_opportunity"
    item["project_enrichment"]["destination"] = "Opportunity Lab"
    return item


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-file", default=str(FIXTURE))
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    parser.set_defaults(dry_run=True)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()
    rows = read_csv(Path(args.input_file))[: max(1, min(args.limit, 10))]
    items = [make_item(row, i) for i, row in enumerate(rows)]
    live = {"created": 0, "duplicates": 0, "failed": 0, "results": []}
    if not args.dry_run:
        live = write_live_tasks(items, "affiliate_opportunity", "affiliate_opportunity_tracker", "affiliate_opportunity", args.limit)
    report = {
        "ok": True, "title": "Affiliate Opportunity Tracker", "generated_at": now(), "dry_run": args.dry_run,
        "items": items, "counts": {"programs": len(items), **{k: live.get(k, 0) for k in ("created", "duplicates", "failed")}},
        "summary": "Affiliate candidates loaded from manual CSV. Terms are not claimed current until proofed.",
        "live": live,
    }
    write_report(report, RUNTIME, MANUAL, args.report_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
