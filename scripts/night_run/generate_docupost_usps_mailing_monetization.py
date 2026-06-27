#!/usr/bin/env python3
"""Part 12 — DocuPost/USPS mailing monetization (internal/report-only)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import night_run_model as nm  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    r = {
        "ok": True, "title": "DocuPost / USPS Mailing Monetization", "generated_at": nm.now(), "dry_run": True,
        "options": [
            {"method": "docupost", "name": "DocuPost (online mailing)", "recommended": True, "is_affiliate": True,
             "connector": "shell only — no API sending in v1", "revenue_opportunity_score": 55},
            {"method": "usps_certified", "name": "Print + USPS Certified Mail (DIY)", "recommended": False, "is_affiliate": False,
             "connector": "client mails + uploads receipt", "revenue_opportunity_score": 0},
        ],
        "tracking_fields": ["mailing_method", "partner_affiliate_url", "mailing_status", "postage_cost", "tracking_number",
                            "certified_mail_receipt_file_path", "return_receipt_file_path", "docupost_tracking_id",
                            "docupost_tracking_url", "mailed_at", "expected_response_deadline", "follow_up_due_at"],
        "verification": {"letters_mailed": False, "docupost_api_sending": False, "money_spent": False,
                         "tracking_receipts": "mock/dev only", "approval_gated": True},
        "counts": {"options": 2},
        "summary": "DocuPost is the recommended online mailing affiliate (shell only); USPS certified is DIY. No letters mailed, no DocuPost sending, no money spent. Mailing stays approval-gated.",
        "safety": {**nm.SAFETY},
    }
    md = ["## Mailing options"]
    for o in r["options"]:
        md.append(f"- {o['name']}: recommended={o['recommended']} affiliate={o['is_affiliate']} ({o['connector']})")
    md += ["", "## Verification"] + [f"- {k}: {v}" for k, v in r["verification"].items()]
    nm.write_report("docupost_usps_mailing_monetization_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
