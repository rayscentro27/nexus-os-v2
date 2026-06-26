#!/usr/bin/env python3
"""Verify Nexus automation policy classification.

Fails if any Level 3 action is treated as Level 1/2, or a Level 1/2 action is misclassified.
Deterministic, local-first. No publish/send/trade/deploy/scheduler/external-AI.

Usage:
    python3 scripts/automation/verify_automation_policy.py --dry-run --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "automation"))
from automation_model import classify_automation_level, now  # noqa: E402

RUNTIME = ROOT / "reports" / "runtime" / "automation_policy_verification_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "automation_policy_verification_latest.md"

# (action_text, expected_level)
EXPECTATIONS = [
    ("transcript review", "autonomous_internal"),
    ("SEO keyword scoring", "autonomous_internal"),
    ("affiliate opportunity scoring", "autonomous_internal"),
    ("generate internal report", "autonomous_internal"),
    ("Hermes prep brief", "autonomous_internal"),
    ("paper-only trading research", "autonomous_internal"),
    ("route to department internal card", "autonomous_internal"),
    ("campaign publish", "approval_gated"),
    ("send email to subscribers", "approval_gated"),
    ("post to social", "approval_gated"),
    ("client contact", "approval_gated"),
    ("scheduler activation", "approval_gated"),
    ("connector activation", "approval_gated"),
    ("production change proposal", "approval_gated"),
    ("live trading order", "blocked_high_risk"),
    ("broker execution", "blocked_high_risk"),
    ("payment charge", "blocked_high_risk"),
    ("production deploy", "blocked_high_risk"),
    ("destructive db write", "blocked_high_risk"),
    ("rls weaken", "blocked_high_risk"),
    ("external ai on sensitive customer data", "blocked_high_risk"),
    ("youtube media download", "blocked_high_risk"),
    ("broad scrape competitor sites", "blocked_high_risk"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify automation policy.")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()

    checks = []
    failures = []
    for action, expected in EXPECTATIONS:
        actual = classify_automation_level(action)
        ok = actual == expected
        # Critical: a Level 3 action must NEVER be classified lower.
        downgraded = expected == "blocked_high_risk" and actual != "blocked_high_risk"
        upgraded_block = expected != "blocked_high_risk" and actual == "blocked_high_risk"
        if not ok:
            failures.append({"action": action, "expected": expected, "actual": actual,
                             "level3_downgrade": downgraded, "false_block": upgraded_block})
        checks.append({"action": action, "expected": expected, "actual": actual, "ok": ok})

    level3_downgrades = sum(1 for f in failures if f["level3_downgrade"])
    ok = len(failures) == 0
    report = {
        "ok": ok,
        "title": "Nexus Automation Policy Verification",
        "generated_at": now(),
        "dry_run": True,
        "counts": {
            "total_checks": len(checks),
            "passed": sum(1 for c in checks if c["ok"]),
            "failed": len(failures),
            "level3_downgrades": level3_downgrades,
        },
        "checks": checks,
        "failures": failures,
        "summary": "All automation actions classified at the correct level." if ok
        else f"{len(failures)} misclassification(s); {level3_downgrades} dangerous Level 3 downgrade(s).",
        "safety": {"publish_send_trade_deploy": False, "scheduler_started": False, "external_ai_called": False},
    }
    RUNTIME.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME.write_text(json.dumps(report, indent=2))
    lines = [
        f"# {report['title']}",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- ok: {report['ok']}",
        f"- passed: {report['counts']['passed']}/{report['counts']['total_checks']}",
        f"- level3_downgrades: {level3_downgrades}",
        "",
        "## Failures",
    ]
    lines += [f"- {f['action']}: expected {f['expected']}, got {f['actual']}" for f in failures] or ["- none"]
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
