#!/usr/bin/env python3
"""Verify Nexus high-risk (Level 3) guards default to blocked.

Confirms each blocked action classifies as blocked_high_risk and is documented with a guard.
Where feasible, lightly inspects repo files for obvious unsafe patterns (read-only).
Deterministic, local-first. No publish/send/trade/deploy/scheduler/external-AI.

Usage:
    python3 scripts/automation/verify_high_risk_guards.py --dry-run --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "automation"))
from automation_model import HIGH_RISK_GUARDS, classify_automation_level, now  # noqa: E402

RUNTIME = ROOT / "reports" / "runtime" / "high_risk_guards_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "high_risk_guards_latest.md"

# Map a guard action to a representative phrase the classifier should mark as blocked_high_risk.
PROBE = {
    "live_trade": "live trading order",
    "broker_order": "broker order execution",
    "funded_account_execution": "funded account execution",
    "auto_executor_exposure": "auto_executor exposure",
    "payment_charge": "payment charge",
    "payment_refund": "payment refund",
    "ad_spend_activation": "ad spend activation",
    "production_deploy": "production deploy",
    "rls_weaken": "rls weaken",
    "destructive_db_write": "destructive db write",
    "secret_print": "print secret",
    "env_commit": "commit .env",
    "broad_scrape": "broad scrape",
    "youtube_media_download": "youtube media download",
    "external_ai_sensitive_data": "external ai sensitive customer data",
    "bulk_send": "bulk send",
    "spam_automation": "spam automation",
    "client_data_exposure": "client data exposure",
    "tenant_isolation_bypass": "tenant isolation bypass",
}


def env_committed() -> bool:
    """True only if .env is NOT gitignored (i.e., a real risk)."""
    gitignore = ROOT / ".gitignore"
    if not gitignore.exists():
        return True
    text = gitignore.read_text(errors="ignore")
    return ".env" not in text


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify high-risk guards.")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()

    guards = []
    failures = []
    for g in HIGH_RISK_GUARDS:
        probe = PROBE.get(g["action"], g["action"])
        level = classify_automation_level(probe)
        blocked = level == "blocked_high_risk"
        files_checked = []
        if g["action"] == "env_commit":
            blocked = blocked and not env_committed()
            files_checked = [".gitignore"]
        if not blocked:
            failures.append(g["action"])
        guards.append({
            "action": g["action"],
            "label": g["label"],
            "guard_exists": True,
            "guard_status": "blocked" if blocked else "NOT_BLOCKED",
            "default_blocked_proof": f"classifier('{probe}') = {level}",
            "why_blocked": g["why_blocked"],
            "guard_note": g["guard_note"],
            "requires_contract": True,
            "rollback_required": True,
            "files_checked": files_checked,
            "next_recommended_hardening": "Add an executable guard test in CI before any contract lifts this block." if blocked else "URGENT: action not classified as blocked.",
        })

    ok = len(failures) == 0
    report = {
        "ok": ok,
        "title": "Nexus High-Risk Guard Verification",
        "generated_at": now(),
        "dry_run": True,
        "counts": {
            "total_guards": len(guards),
            "blocked": sum(1 for g in guards if g["guard_status"] == "blocked"),
            "not_blocked": len(failures),
        },
        "guards": guards,
        "failures": failures,
        "summary": "All high-risk actions are blocked by default." if ok
        else f"{len(failures)} high-risk action(s) not blocked: {', '.join(failures)}",
        "safety": {"publish_send_trade_deploy": False, "scheduler_started": False, "external_ai_called": False, "secrets_printed": False},
    }
    RUNTIME.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME.write_text(json.dumps(report, indent=2))
    lines = [
        f"# {report['title']}",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- ok: {report['ok']}",
        f"- blocked: {report['counts']['blocked']}/{report['counts']['total_guards']}",
        "",
        "## Guards",
    ]
    for g in guards:
        lines.append(f"- {g['guard_status']} · {g['label']} ({g['action']}) — {g['why_blocked']}")
    MANUAL.parent.mkdir(parents=True, exist_ok=True)
    MANUAL.write_text("\n".join(lines) + "\n")
    if args.report_path:
        p = Path(args.report_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(report, indent=2))
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(report["summary"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
