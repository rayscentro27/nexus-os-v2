#!/usr/bin/env python3
"""Hermes Client Workflow recommendations (dry-run).

Proactively surfaces stuck clients, missing tasks, mailing gaps, funding blockers, Ray-Review-ready
clients, upsell/affiliate opportunities, and revenue risk. Internal-only output; no client contact.

    python3 scripts/client_workflow/generate_hermes_client_recommendations.py --dry-run --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "research"))
sys.path.insert(0, str(ROOT / "scripts" / "client_workflow"))
from common import write_report  # noqa: E402
import client_workflow_model as m  # noqa: E402

RUNTIME = ROOT / "reports" / "runtime" / "hermes_client_workflow_recommendations_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "hermes_client_workflow_recommendations_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()

    clients, source = m.load_clients()
    d = m.digest(clients)
    # Only the ready_for_ray_review recommendations are approval-gated (one card per ready plan).
    ray_cards = [r for r in d["recommendations"] if r["kind"] == "ready_for_ray_review"]

    report = {
        "ok": True,
        "title": "Hermes Client Workflow Recommendations",
        "generated_at": m.now(),
        "dry_run": True,
        "data_source": source,
        "top_recommendation": d["top_recommendation"],
        "recommendations": d["recommendations"],
        "ray_review_cards_proposed": len(ray_cards),
        "counts": {
            "total_clients": d["total_clients"],
            "recommendations": len(d["recommendations"]),
            "stuck_clients": d["stuck_clients"],
            "credit_reports_pending": d["credit_reports_pending"],
            "smartcredit_incomplete": d["smartcredit_incomplete"],
            "no_score": d["no_score"],
            "business_incomplete": d["business_incomplete"],
            "letters_unmailed": d["letters_unmailed"],
            "mailing_proof_missing": d["mailing_proof_missing"],
            "ready_for_ray_review": d["ready_for_ray_review"],
            "upsell_opportunities": d["upsell_opportunities"],
            "near_funding_ready": d["near_funding_ready"],
            "revenue_risk_clients": d["revenue_risk_clients"],
            "do_not_send_to_lenders": d["do_not_send_to_lenders"],
        },
        "summary": f"Hermes generated {len(d['recommendations'])} internal recommendations across {d['total_clients']} clients ({d['ready_for_ray_review']} ready for Ray review). Internal-only; no client contacted.",
        "safety": {"internal_only": True, "client_contacted": False, "external_ai_on_client_data": False,
                   "client_plan_exposed": False},
    }
    write_report(report, RUNTIME, MANUAL, args.report_path)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(report["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
