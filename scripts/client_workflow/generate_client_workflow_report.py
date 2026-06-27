#!/usr/bin/env python3
"""Client Workflow engine status report (dry-run, local-first).

No DB writes, no external calls, no client-facing output. Reads clients read-only if Supabase is
configured; otherwise uses deterministic sample clients.

    python3 scripts/client_workflow/generate_client_workflow_report.py --dry-run --json
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

RUNTIME = ROOT / "reports" / "runtime" / "client_workflow_engine_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "client_workflow_engine_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()

    clients, source = m.load_clients()
    by_stage: dict[str, int] = {}
    for cl in clients:
        by_stage[cl["current_stage"]] = by_stage.get(cl["current_stage"], 0) + 1
    d = m.digest(clients)

    report = {
        "ok": True,
        "title": "Client Workflow Engine",
        "generated_at": m.now(),
        "dry_run": True,
        "data_source": source,
        "clients_by_stage": by_stage,
        "stages": m.STAGES,
        "credit_report_source_workflow": {
            "smartcredit": "recommended affiliate path (score visibility); NO password/scrape/login",
            "annualcreditreport": "free official path; reports only (manual score entry allowed)",
            "manual_upload": "upload report from another source",
        },
        "smartcredit_connector_status": "not_configured (affiliate-link-only; report download requires_partner_api_confirmation)",
        "mailing_workflow": {
            "docupost": "connector shell only; no auto-send, no postage spend",
            "usps_certified": "DIY print + certified mail; client uploads receipt proof",
        },
        "ray_review_behavior": "One Ray Review card per READY plan; never per negative item. Client plan hidden until approved.",
        "digest_top_recommendation": d["top_recommendation"],
        "counts": {
            "total_clients": d["total_clients"],
            "stuck_clients": d["stuck_clients"],
            "credit_reports_pending": d["credit_reports_pending"],
            "business_incomplete": d["business_incomplete"],
            "letters_unmailed": d["letters_unmailed"],
            "mailing_proof_missing": d["mailing_proof_missing"],
            "ready_for_ray_review": d["ready_for_ray_review"],
            "near_funding_ready": d["near_funding_ready"],
            "revenue_risk_clients": d["revenue_risk_clients"],
        },
        "summary": f"Client workflow engine summarized {d['total_clients']} clients across {len(m.STAGES)} stages ({source}). No client contacted, nothing published/sent/mailed/spent.",
        "safety": {"client_contacted": False, "letters_mailed": False, "money_spent": False,
                   "smartcredit_password_stored": False, "smartcredit_scraped": False,
                   "external_ai_on_client_data": False, "client_plan_exposed": False},
    }
    write_report(report, RUNTIME, MANUAL, args.report_path)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(report["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
