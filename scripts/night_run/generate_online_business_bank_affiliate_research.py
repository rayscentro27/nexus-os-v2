#!/usr/bin/env python3
"""Part 7 — Online business bank account affiliate research (internal/report-only)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import night_run_model as nm  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    r = {
        "ok": True, "title": "Online Business Bank Affiliate Research", "generated_at": nm.now(), "dry_run": True,
        "disclaimer": "Internal research estimates to validate against live referral terms. No affiliate URL activated.",
        "partners": nm.ONLINE_BANK_PARTNERS,
        "recommended_primary": nm.ONLINE_BANK_PRIMARY,
        "backups": nm.ONLINE_BANK_BACKUPS,
        "diy_option": nm.ONLINE_BANK_DIY,
        "business_setup_category": "business_bank_account",
        "compliance_note": nm.ONLINE_BANK_COMPLIANCE,
        "counts": {"partners": len(nm.ONLINE_BANK_PARTNERS)},
        "summary": f"Recommended primary online-bank partner: {nm.ONLINE_BANK_PRIMARY}; backups: {', '.join(nm.ONLINE_BANK_BACKUPS)}. DIY (own bank) always offered. Nexus never opens accounts.",
        "safety": {**nm.SAFETY, "account_opened": False, "application_submitted": False, "report_only": True},
    }
    md = ["## Partners (validate against live terms)"]
    for bk in nm.ONLINE_BANK_PARTNERS:
        md.append(f"- {bk['partner']}: fits {', '.join(bk['fits'])}; no_monthly_fee={bk['no_monthly_fee']}; invoicing={bk['invoicing']}; statements_for_funding={bk['statements_for_funding']}")
    md += ["", f"## Recommended primary: {nm.ONLINE_BANK_PRIMARY}", f"- backups: {', '.join(nm.ONLINE_BANK_BACKUPS)}",
           f"- DIY: {nm.ONLINE_BANK_DIY}", f"- compliance: {nm.ONLINE_BANK_COMPLIANCE}"]
    nm.write_report("online_business_bank_affiliate_research_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
