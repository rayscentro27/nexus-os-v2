#!/usr/bin/env python3
"""Convert strong research items into experiment candidates."""
from __future__ import annotations

import argparse
import json

from common import ROOT, candidate, now, write_live_tasks, write_report

RUNTIME = ROOT / "reports" / "runtime" / "research_to_experiment_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "research_to_experiment_latest.md"

EXPERIMENTS = [
    ("Test $97 readiness review landing page angle", "business funding", "GoClear/Apex owners", "$97 readiness review", "SEO/content", "$97 review interest", "0-50", "7 days", "lead or booked call"),
    ("Test affiliate article around business credit vendor", "business credit", "new LLC owners", "affiliate review article", "SEO", "affiliate clicks", "0-50", "14 days", "clicks/leads"),
    ("Test YouTube transcript-to-blog workflow", "seo", "Nexus content ops", "transcript to blog", "Source Intake", "draft velocity", "0", "7 days", "draft created"),
    ("Test AI automation service offer", "ai automation", "small business owners", "automation audit", "Opportunity Lab", "qualified leads", "0-100", "14 days", "booked call"),
    ("Test trading strategy paper backtest only", "trading strategies", "Trading Lab", "paper strategy", "Trading Lab", "paper scorecard", "0", "7 days", "backtest report"),
]


def build_items(limit: int) -> list[dict]:
    items = []
    for i, (hypothesis, topic, audience, angle, traffic, expected, cost, duration, metric) in enumerate(EXPERIMENTS[:limit]):
        item = candidate(hypothesis, f"experiment://{i+1}", topic, source_type="experiment", proof_source="deterministic_experiment_seed")
        item.update({
            "unique_key": f"research_experiment:{i+1}",
            "owner_tab": "trading" if "trading" in topic else "opportunities" if topic != "seo" else "seo",
            "summary": f"Hypothesis: {hypothesis}. Audience: {audience}. Traffic: {traffic}.",
            "recommendation": "Create an experiment card; execute only after Ray reviews risk and approvals.",
            "experiment": {
                "hypothesis": hypothesis,
                "audience": audience,
                "offer_or_content_angle": angle,
                "traffic_source": traffic,
                "expected_result": expected,
                "test_cost": cost,
                "test_duration": duration,
                "success_metric": metric,
                "next_action": "Create a safe task or park.",
                "risk_level": "high" if "trading" in topic else "medium" if "credit" in topic or "funding" in topic else "low",
                "department_owner": item["owner_tab"],
                "source_research_id": None,
                "priority_score": item["score"],
            },
        })
        item["project_enrichment"]["category"] = "research_experiment"
        items.append(item)
    return items


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    parser.set_defaults(dry_run=True)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--no-external-ai", action="store_true", default=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()
    if not args.no_external_ai:
        print(json.dumps({"ok": False, "error": "no_external_ai_required"}, indent=2))
        return 2
    items = build_items(max(1, min(args.limit, 10)))
    live = {"created": 0, "duplicates": 0, "failed": 0, "results": []}
    if not args.dry_run:
        live = write_live_tasks(items, "research_experiment", "research_to_experiment", "research_experiment", args.limit)
    report = {
        "ok": True, "title": "Research To Experiments", "generated_at": now(), "dry_run": args.dry_run,
        "items": items, "counts": {"experiments": len(items), **{k: live.get(k, 0) for k in ("created", "duplicates", "failed")}},
        "summary": "Strong research ideas converted into safe experiment candidates. No execution.",
        "live": live,
    }
    write_report(report, RUNTIME, MANUAL, args.report_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
