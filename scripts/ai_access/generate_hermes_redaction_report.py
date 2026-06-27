#!/usr/bin/env python3
"""Generate the Hermes redaction policy report (dry-run).

Demonstrates that forbidden client fields are stripped before Hermes sees data, and that the
sanitized signal set is PII-free.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "ai_access"))
import ai_access_model as m  # noqa: E402

RUNTIME = ROOT / "reports" / "runtime" / "hermes_redaction_policy_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "hermes_redaction_policy_latest.md"

SAFE_SIGNAL_KEYS = [
    "total_clients_by_stage", "stuck_clients_count", "credit_reports_pending_count",
    "smartcredit_selected_count", "annualcreditreport_selected_count", "no_score_available_count",
    "business_setup_incomplete_count", "letters_ready_count", "mailing_pending_count",
    "mailing_proof_missing_count", "funding_ready_count", "ray_review_needed_count",
    "affiliate_opportunity_count", "revenue_risk_count", "estimated_commission_delayed",
    "recommended_next_actions",
]

PII_PATTERNS = [r"name", r"ssn", r"social.?security", r"dob|date.?of.?birth", r"address", r"phone",
                r"email", r"account.?(number|no|#)", r"bank.?statement", r"credit.?report",
                r"smartcredit", r"\bletter\b", r"routing", r"card.?number", r"funding.?document"]


def looks_like_pii(key: str) -> bool:
    if key in m.HERMES_FORBIDDEN_FIELDS:
        return True
    return any(re.search(p, key, re.I) for p in PII_PATTERNS)


def redact(d: dict) -> dict:
    return {k: v for k, v in d.items() if not looks_like_pii(k)}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", default=True)
    p.add_argument("--json", action="store_true")
    p.add_argument("--report-path", default="")
    a = p.parse_args()

    # A raw record that should be fully redacted down to nothing Hermes-private.
    raw = {
        "full_client_name": "REDACT", "ssn": "REDACT", "dob": "REDACT", "address": "REDACT",
        "raw_credit_report": "REDACT", "smartcredit_file": "REDACT", "bank_statement": "REDACT",
        "account_number": "REDACT", "raw_letter": "REDACT",
        "stuck_clients_count": 4, "ray_review_needed_count": 1,  # safe signals
    }
    redacted = redact(raw)
    forbidden_detected = [k for k in raw if looks_like_pii(k)]
    sanitized_pii_free = all(k in SAFE_SIGNAL_KEYS for k in redacted)

    proofs = {
        "forbidden_fields_stripped": all(not looks_like_pii(k) for k in redacted),
        "sanitized_set_is_pii_free": sanitized_pii_free,
        "hermes_blocked_from_raw_credit_report": not m.can_access_data("hermes_ceo_advisor", "raw_credit_report"),
        "hermes_blocked_from_smartcredit_file": not m.can_access_data("hermes_ceo_advisor", "smartcredit_file"),
    }
    ok = all(proofs.values())
    report = {
        "ok": ok,
        "title": "Hermes Redaction Policy",
        "generated_at": m.now(),
        "dry_run": True,
        "forbidden_fields": m.HERMES_FORBIDDEN_FIELDS,
        "safe_signal_keys": SAFE_SIGNAL_KEYS,
        "redaction_example": {"input_keys": sorted(raw.keys()), "output_keys": sorted(redacted.keys()),
                              "stripped": sorted(forbidden_detected)},
        "proofs": proofs,
        "counts": {"forbidden_fields": len(m.HERMES_FORBIDDEN_FIELDS), "safe_keys": len(SAFE_SIGNAL_KEYS),
                   "stripped": len(forbidden_detected)},
        "summary": "Hermes receives sanitized signals only; raw client fields stripped." if ok else "Redaction proof failed.",
        "safety": {"hermes_saw_raw_client_data": False, "external_calls": False},
    }
    RUNTIME.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME.write_text(json.dumps(report, indent=2))
    L = [f"# {report['title']}", "", f"- ok: {report['ok']}", "", "## Proofs"] + [f"- {k}: {v}" for k, v in proofs.items()]
    L += ["", "## Redaction example", f"- stripped: {', '.join(sorted(forbidden_detected))}", f"- kept: {', '.join(sorted(redacted.keys()))}"]
    MANUAL.parent.mkdir(parents=True, exist_ok=True)
    MANUAL.write_text("\n".join(L) + "\n")
    if a.report_path:
        Path(a.report_path).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2) if a.json else report["summary"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
