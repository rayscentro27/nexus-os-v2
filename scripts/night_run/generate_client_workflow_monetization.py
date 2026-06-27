#!/usr/bin/env python3
"""Part 9 — Client workflow monetization integration (internal/report-only)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import night_run_model as nm  # noqa: E402

# task -> (revenue_path, partner, diy, revenue_score, affiliate_score, retention, funding_potential)
TASK_MON = [
    ("choose_credit_report_source", "credit_monitoring affiliate", "SmartCredit", "AnnualCreditReport.com (free)", 70, 80, "Score tracking retains clients monthly.", "low"),
    ("connect_smartcredit_or_upload_report", "credit_monitoring affiliate", "SmartCredit", "Manual upload", 70, 80, "Monitoring is the core monthly value.", "low"),
    ("approve_dispute_letters", "mailing affiliate", "DocuPost", "USPS Certified Mail", 55, 55, "Letter tracking is recurring convenience.", "low"),
    ("confirm_business_entity", "business_formation affiliate", "Formation partner", "State SoS (DIY)", 70, 70, "Business setup extends the relationship.", "medium"),
    ("add_ein", "business_formation affiliate", "Formation partner", "IRS.gov (free)", 40, 40, "Guided setup adds convenience.", "low"),
    ("add_business_bank_account", "online_business_bank affiliate", "Bluevine (primary)", "Client's own bank", 75, 70, "Statements needed for funding; ongoing tracking retains.", "high"),
    ("add_duns_profile", "business_credit_profile affiliate", "Business credit tool", "Free DUNS (D&B)", 60, 65, "Business credit building drives subscription.", "medium"),
    ("add_vendor_accounts", "vendor_credit affiliate", "Vendor credit partner", "Net-30 vendors (DIY)", 60, 60, "Vendor tradelines build over months.", "medium"),
    ("upload_bank_statements", "funding readiness", None, "From client bank", 50, 0, "Funding readiness tracking retains toward funding.", "high"),
    ("complete_funding_readiness_review", "funding commission pipeline", None, None, 80, 0, "Funding-ready clients move to post-funding tier.", "high"),
    ("review_recommended_funding_path", "funding commission pipeline", None, None, 85, 0, "Approved funding path is highest-value moment.", "high"),
]


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    tasks = [{"task_key": k, "revenue_path": rp, "recommended_partner": pn, "diy_option": diy,
              "revenue_opportunity_score": rs, "affiliate_opportunity_score": afs,
              "subscription_retention_reason": ret, "funding_commission_potential": fp, "approval_gated": True}
             for (k, rp, pn, diy, rs, afs, ret, fp) in TASK_MON]
    avg = round(sum(t["revenue_opportunity_score"] for t in tasks) / len(tasks))
    high_funding = sum(1 for t in tasks if t["funding_commission_potential"] == "high")
    r = {
        "ok": True, "title": "Client Workflow Monetization", "generated_at": nm.now(), "dry_run": True,
        "task_monetization": tasks,
        "task_to_revenue_examples": [
            "credit report missing -> SmartCredit or free report option",
            "no score -> SmartCredit recommendation",
            "LLC missing -> formation affiliate or state DIY",
            "EIN missing -> guided option or IRS DIY",
            "business bank missing -> online bank partner or client's own bank",
            "letters ready -> DocuPost or USPS certified mail",
            "client stuck -> reminder/upsell",
            "client nearly funding-ready -> Ray Review/funding path",
        ],
        "counts": {"tasks": len(tasks), "avg_revenue_score": avg, "high_funding_tasks": high_funding},
        "summary": f"Mapped {len(tasks)} workflow tasks to revenue/affiliate/retention/funding signals (avg revenue score {avg}). All client-facing recs approval-gated.",
        "safety": {**nm.SAFETY, "client_recommendation_exposed": False},
    }
    md = ["## Task -> revenue mapping"]
    for t in tasks:
        md.append(f"- {t['task_key']}: {t['revenue_path']} · partner={t['recommended_partner']} · DIY={t['diy_option']} · rev={t['revenue_opportunity_score']} · funding={t['funding_commission_potential']}")
    md += ["", "## Examples"] + [f"- {x}" for x in r["task_to_revenue_examples"]]
    nm.write_report("client_workflow_monetization_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
