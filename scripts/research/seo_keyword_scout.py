#!/usr/bin/env python3
"""SEO keyword scout v1 from manual CSV."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ROOT, candidate, num, now, read_csv, write_live_tasks, write_report

RUNTIME = ROOT / "reports" / "runtime" / "seo_keyword_scout_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "seo_keyword_scout_latest.md"


def make_item(row: dict) -> dict:
    topic = row.get("topic_cluster") or row["keyword"]
    item = candidate(row["keyword"], f"keyword://{row['keyword']}", topic.replace("_", " "), source_type="keyword", proof_source=row.get("proof_source", row.get("source", "manual_csv")))
    difficulty_penalty = 20 if row.get("difficulty_estimate", "").lower() == "high" else 10 if row.get("difficulty_estimate", "").lower() == "medium" else 0
    score = max(0, min(100, int(((num(row.get("affiliate_relevance"), 0) or 0) + (num(row.get("GoClear_relevance"), 0) or 0)) / 2 - difficulty_penalty)))
    item.update({
        "unique_key": f"seo_keyword:{row['keyword']}",
        "title": f"SEO keyword opportunity: {row['keyword']}",
        "summary": f"{row['search_intent']} intent keyword for {row.get('target_offer')}; suggested format: {row.get('content_type_recommendation')}.",
        "owner_tab": "seo",
        "score": score,
        "seo_keyword": row,
    })
    item["project_enrichment"]["score"] = score
    item["project_enrichment"]["category"] = "seo_keyword_opportunity"
    item["project_enrichment"]["destination"] = "SEO / Marketing"
    return item


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-file", required=True)
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    parser.set_defaults(dry_run=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()
    path = Path(args.input_file)
    if not path.is_absolute():
        path = ROOT / path
    items = [make_item(row) for row in read_csv(path)]
    live = {"created": 0, "duplicates": 0, "failed": 0, "results": []}
    if not args.dry_run:
        live = write_live_tasks(items, "seo_keyword_opportunity", "seo_keyword_scout", "seo_keyword_opportunity", len(items))
    report = {
        "ok": True, "title": "SEO Keyword Scout", "generated_at": now(), "dry_run": args.dry_run,
        "items": items, "counts": {"keywords": len(items), **{k: live.get(k, 0) for k in ("created", "duplicates", "failed")}},
        "summary": "Keywords loaded from manual CSV. No paid API called.",
        "live": live,
    }
    write_report(report, RUNTIME, MANUAL, args.report_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
