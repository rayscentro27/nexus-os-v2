#!/usr/bin/env python3
"""Affiliate Approval Waiting Room report (report-only). Tracks partner approval + URL intake status."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import launch_model as lm  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    records = lm.affiliate_approval_records()
    rank = {pid: i for i, pid in enumerate(lm.APPROVAL_PRIORITY)}
    records.sort(key=lambda r: rank.get(r["partner_offer_id"], 999))
    counts = {
        "total": len(records),
        "not_applied": sum(1 for r in records if r["application_status"] == "not_applied"),
        "approved": sum(1 for r in records if r["application_status"] == "approved"),
        "awaiting_urls": sum(1 for r in records if r["url_intake_status"] == "awaiting_urls"),
    }
    r = {
        "ok": True, "title": "Affiliate Approval Waiting Room", "generated_at": lm.now(), "dry_run": True,
        "records": records, "approval_priority": lm.APPROVAL_PRIORITY,
        "counts": counts,
        "summary": f"{counts['total']} partner programs tracked; {counts['not_applied']} not yet applied; "
                   f"{counts['approved']} approved; {counts['awaiting_urls']} awaiting URLs. No partner contacted or activated.",
        "safety": {**lm.SAFETY, "partner_contacted": False, "partner_connector_activated": False},
    }
    md = ["## Waiting room (by approval priority)"]
    for rec in records:
        md.append(f"- {rec['partner_name']} ({rec['category']}): {rec['application_status']} · {rec['url_intake_status']} — {rec['next_action']}")
    lm.write_report("affiliate_waiting_room_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
