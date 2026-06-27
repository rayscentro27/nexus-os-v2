#!/usr/bin/env python3
"""Part 11 — Business setup + online banking monetization (internal/report-only)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import night_run_model as nm  # noqa: E402

SETUP_ITEMS = [
    ("llc_entity", "Formation partner", "State SoS filing (DIY)", True),
    ("ein", "Formation partner", "IRS.gov (free)", True),
    ("registered_agent", "Registered agent partner", "Self as agent", False),
    ("business_address", "Virtual address partner", "Commercial address (DIY)", True),
    ("business_phone", "VoIP partner", "Any business line", False),
    ("website_domain_email", "Website/domain partner", "Self-built (DIY)", False),
    ("duns_profile", "Business credit tool", "Free DUNS (D&B)", True),
    ("business_bank_account", "Bluevine (primary online bank)", "Client's own bank/credit union", True),
    ("bookkeeping", "Bookkeeping partner", "DIY spreadsheet", False),
    ("vendor_accounts", "Vendor credit partner", "Net-30 vendors (DIY)", True),
    ("licenses_permits", None, "State/local licensing (DIY)", True),
    ("bank_statements", None, "From client bank", True),
]


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    items = [{"setup_item_key": k, "recommended_partner": pn, "diy_option": diy, "proof_required": pr,
              "already_completed_option": True} for (k, pn, diy, pr) in SETUP_ITEMS]
    r = {
        "ok": True, "title": "Business Setup + Online Banking Monetization", "generated_at": nm.now(), "dry_run": True,
        "setup_items": items,
        "online_bank": {"recommended_primary": nm.ONLINE_BANK_PRIMARY, "backups": nm.ONLINE_BANK_BACKUPS,
                        "diy_option": nm.ONLINE_BANK_DIY, "compliance_note": nm.ONLINE_BANK_COMPLIANCE},
        "counts": {"setup_items": len(items), "with_partner": sum(1 for i in items if i["recommended_partner"]),
                   "with_proof": sum(1 for i in items if i["proof_required"])},
        "summary": f"{len(items)} business setup items each offer partner + DIY + already-completed + proof. Online business bank account added (primary {nm.ONLINE_BANK_PRIMARY}). Nexus never opens accounts or submits applications.",
        "safety": {**nm.SAFETY, "account_opened": False, "application_submitted": False, "funding_guaranteed": False},
    }
    md = ["## Setup items (partner / DIY / proof)"]
    for i in items:
        md.append(f"- {i['setup_item_key']}: partner={i['recommended_partner']} · DIY={i['diy_option']} · proof_required={i['proof_required']}")
    md += ["", "## Online business bank account",
           f"- recommended primary: {nm.ONLINE_BANK_PRIMARY}", f"- backups: {', '.join(nm.ONLINE_BANK_BACKUPS)}",
           f"- DIY: {nm.ONLINE_BANK_DIY}", f"- compliance: {nm.ONLINE_BANK_COMPLIANCE}"]
    nm.write_report("business_setup_banking_monetization_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
