#!/usr/bin/env python3
"""Client Workflow affiliate recommendation report (dry-run).

Every recommendation pairs a partner option with a DIY/free option, includes disclosure, and never
guarantees outcomes. No outbound action. No affiliate URL is activated.

    python3 scripts/client_workflow/generate_affiliate_recommendation_report.py --dry-run --json
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

RUNTIME = ROOT / "reports" / "runtime" / "affiliate_recommendation_engine_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "affiliate_recommendation_engine_latest.md"

DISCLOSURE = "Recommended partner; we may earn a commission if you sign up. Optional — a free/DIY option is always available."
NO_GUARANTEE = "Educational/planning only. No guarantee of approval, deletion, score increase, or funding."

# (category, partner, diy_option, maps_to, revenue_opportunity_score)
RECS = [
    ("credit_monitoring", "SmartCredit", "AnnualCreditReport.com (free reports only)", "credit_report_source", 80),
    ("business_formation", "Formation partner", "State Secretary of State + IRS.gov (free EIN)", "llc_entity", 70),
    ("registered_agent", "Registered agent partner", "Act as your own registered agent", "registered_agent", 40),
    ("business_address", "Virtual address partner", "Use an existing commercial address", "business_address", 55),
    ("business_phone", "VoIP partner", "Any business phone line", "business_phone", 45),
    ("website_domain_email", "Website/domain partner", "Self-built site + domain email", "website_domain", 50),
    ("business_credit_profile", "Business credit tool", "Free DUNS request from D&B", "duns_profile", 65),
    ("business_bank_account", "Business banking partner", "Open at any business bank", "business_bank_account", 60),
    ("bookkeeping_accounting", "Bookkeeping partner", "DIY spreadsheet/accounting", "bookkeeping", 45),
    ("vendor_credit_accounts", "Vendor credit partner", "Open net-30 vendors directly", "vendor_accounts", 60),
    ("online_mailing", "DocuPost", "USPS Certified Mail at your local Post Office", "mailing", 55),
    ("funding_readiness_services", "Funding readiness partner", "Internal funding readiness checklist", "funding_readiness", 70),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()

    recommendations = [{
        "category": cat,
        "partner_name": partner,
        "affiliate_url": None,  # activated only via approved partner_offers
        "disclosure_text": DISCLOSURE,
        "diy_option_name": diy,
        "diy_option_url": None,
        "client_selected_path": "undecided",
        "conversion_status": "none",
        "revenue_opportunity_score": score,
        "compliance_notes": NO_GUARANTEE,
        "maps_to": maps_to,
    } for (cat, partner, diy, maps_to, score) in RECS]

    report = {
        "ok": True,
        "title": "Affiliate Recommendation Engine",
        "generated_at": m.now(),
        "dry_run": True,
        "recommendations": recommendations,
        "rules": [
            "Always show a DIY/free/official option.",
            "Never say the affiliate option is required.",
            "Always disclose affiliate/referral relationship.",
            "Never guarantee outcomes.",
            "Hermes recommends affiliate paths only when relevant to a client's missing task/stage.",
        ],
        "counts": {
            "recommendations": len(recommendations),
            "with_diy_option": sum(1 for r in recommendations if r["diy_option_name"]),
            "affiliate_urls_activated": 0,
        },
        "summary": f"{len(recommendations)} affiliate recommendations, each with a DIY/free option and disclosure. No URL activated, no outbound action.",
        "safety": {"affiliate_url_activated": False, "outbound_action": False, "guarantee_made": False},
    }
    write_report(report, RUNTIME, MANUAL, args.report_path)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(report["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
