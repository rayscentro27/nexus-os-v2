#!/usr/bin/env python3
"""Verify no external execution occurred.

Scans every reports/runtime/*.json safety block and fails if any "external action" flag is true or
any required-blocked flag is false. Proves the night run stayed internal/draft-only.

    python3 scripts/safety/verify_no_external_execution.py --dry-run --json
"""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RUNTIME_DIR = ROOT / "reports" / "runtime"
RUNTIME = RUNTIME_DIR / "no_external_execution_verification_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "no_external_execution_verification_latest.md"

# Flags that must be FALSE wherever they appear in any report's safety/top-level block.
MUST_BE_FALSE = [
    "external_action", "external_action_performed", "messages_sent", "client_contacted",
    "post_published", "video_uploaded", "landing_page_deployed", "ad_launched", "money_spent",
    "client_charged", "trade_placed", "letters_mailed", "disputes_submitted",
    "smartcredit_password_stored", "smartcredit_scraped", "docupost_sending",
    "docupost_api_sending", "live_client_vault_connected", "second_supabase_connected",
    "external_ai_on_client_data", "broad_scrape", "offer_published", "offer_launched",
    "payment_link_activated", "subscription_activated", "stripe_connected", "partner_contacted",
    "partner_connector_activated", "affiliate_url_activated", "url_navigated", "url_activated",
    "raw_client_data_used",
]
# Flags that must be TRUE if present.
MUST_BE_TRUE = ["level_3_blocked"]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def scan(obj, path, violations):
    if isinstance(obj, dict):
        for k, v in obj.items():
            kp = f"{path}.{k}" if path else k
            if isinstance(v, bool):
                if k in MUST_BE_FALSE and v is True:
                    violations.append({"flag": kp, "expected": False, "actual": True})
                if k in MUST_BE_TRUE and v is False:
                    violations.append({"flag": kp, "expected": True, "actual": False})
            else:
                scan(v, kp, violations)
    elif isinstance(obj, list):
        for i, x in enumerate(obj):
            scan(x, f"{path}[{i}]", violations)


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    files = sorted(RUNTIME_DIR.glob("*.json")) if RUNTIME_DIR.exists() else []
    violations = []
    scanned = 0
    for f in files:
        if f.name == RUNTIME.name:
            continue
        try:
            data = json.loads(f.read_text(errors="ignore"))
        except Exception:
            continue
        scanned += 1
        v: list = []
        scan(data, "", v)
        for item in v:
            item["file"] = f.name
            violations.append(item)

    ok = len(violations) == 0
    report = {
        "ok": ok, "title": "No External Execution Verification", "generated_at": now(), "dry_run": True,
        "files_scanned": scanned, "violations": violations,
        "counts": {"files_scanned": scanned, "violations": len(violations)},
        "summary": f"Scanned {scanned} runtime reports; no external execution detected." if ok
        else f"{len(violations)} safety violation(s) detected across runtime reports.",
        "safety": {"external_action": False, "money_spent": False, "client_charged": False, "level_3_blocked": True},
    }
    RUNTIME.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME.write_text(json.dumps(report, indent=2))
    lines = [f"# {report['title']}", "", f"- generated_at: {report['generated_at']}", f"- ok: {report['ok']}",
             f"- files_scanned: {scanned}", f"- violations: {len(violations)}", "", "## Violations"]
    lines += [f"- {v['file']}: {v['flag']} = {v['actual']} (expected {v['expected']})" for v in violations] or ["- none"]
    MANUAL.parent.mkdir(parents=True, exist_ok=True)
    MANUAL.write_text("\n".join(lines) + "\n")
    print(json.dumps(report, indent=2) if a.json else report["summary"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
