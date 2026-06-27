#!/usr/bin/env python3
"""Partner URL intake (dry-run, validation-only).

Validates approved partner URLs without navigating to, activating, or persisting them. Provide an
intake JSON file via --intake-file, or rely on the built-in dev sample for a self-test. Real URL
placement happens later behind Ray approval.

    python3 scripts/partners/intake_partner_urls.py --dry-run --json
    python3 scripts/partners/intake_partner_urls.py --dry-run --json --intake-file path/to/intake.json
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import launch_model as lm  # noqa: E402

# Dev self-test sample (NOT real URLs / NOT persisted): proves the validator accepts/rejects correctly.
DEV_SAMPLE_INTAKES = [
    {"partner_offer_id": "smartcredit", "affiliate_url": "https://example.com/ref/sample",
     "disclosure_text": "Recommended partner; we may earn a commission. DIY option available.",
     "diy_option_name": "AnnualCreditReport.com (free)", "submitted_by": "dev_self_test"},
    {"partner_offer_id": "bluevine", "referral_url": "http://insecure.example.com",  # invalid: not https
     "submitted_by": "dev_self_test"},
    {"partner_offer_id": "docupost", "affiliate_url": "https://PLACEHOLDER.invalid/pay",  # invalid: placeholder
     "submitted_by": "dev_self_test"},
]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", default=True)
    p.add_argument("--json", action="store_true")
    p.add_argument("--intake-file", default="")
    a = p.parse_args()

    if a.intake_file:
        data = json.loads(Path(a.intake_file).read_text())
        intakes = data if isinstance(data, list) else [data]
        source = a.intake_file
    else:
        intakes = DEV_SAMPLE_INTAKES
        source = "dev_self_test_sample (not persisted, not real URLs)"

    results = [lm.intake_partner_urls(i) for i in intakes]
    accepted = [x for x in results if x["accepted"]]
    rejected = [x for x in results if not x["accepted"]]
    r = {
        "ok": True, "title": "Partner URL Intake", "generated_at": lm.now(), "dry_run": True,
        "source": source, "results": results,
        "counts": {"submitted": len(results), "accepted": len(accepted), "rejected": len(rejected)},
        "summary": f"Validated {len(results)} intake(s): {len(accepted)} accepted, {len(rejected)} rejected. "
                   "No URL navigated, activated, or persisted.",
        "safety": {**lm.SAFETY, "url_navigated": False, "url_activated": False, "url_persisted": False},
    }
    md = ["## Intake results", f"- source: {source}"]
    for x in results:
        md.append(f"- {x['partner_name']}: {'ACCEPTED' if x['accepted'] else 'REJECTED'} → {x['resulting_config_status']} ({x['next_action']})")
    lm.write_report("partner_url_intake_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
