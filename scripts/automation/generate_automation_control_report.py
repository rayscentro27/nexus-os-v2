#!/usr/bin/env python3
"""Generate the Nexus Automation Control Center report across every category.

Dry-run, local-first, deterministic. Does not publish, send, trade, deploy, activate schedulers,
scrape, download media, call external AI, or touch v1 workers.

Usage:
    python3 scripts/automation/generate_automation_control_report.py --dry-run --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "automation"))
from automation_model import (  # noqa: E402
    CATEGORY_MATRIX,
    CONNECTOR_REQUIRED,
    EXTERNAL_API_REQUIRED,
    HIGH_RISK_GUARDS,
    LEVELS,
    SCHEDULE_READY,
    now,
)

RUNTIME = ROOT / "reports" / "runtime" / "automation_control_report_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "automation_control_report_latest.md"
CENTER_RUNTIME = ROOT / "reports" / "runtime" / "nexus_automation_control_center_latest.json"
CENTER_MANUAL = ROOT / "reports" / "manual_publish" / "nexus_automation_control_center_latest.md"


def build_report() -> dict:
    categories = []
    for c in CATEGORY_MATRIX:
        cid = c["category_id"]
        categories.append({
            "category_id": cid,
            "category_name": c["category_name"],
            "owner_department": c["owner_department"],
            "level_1_allowed_actions": c["level_1_allowed_actions"],
            "level_2_approval_gated_actions": c["level_2_approval_gated_actions"],
            "level_3_blocked_actions": c["level_3_blocked_actions"],
            "schedule_ready": cid in SCHEDULE_READY,
            "scheduler_approval_required": cid in SCHEDULE_READY or any("scheduler" in a.lower() for a in c["level_2_approval_gated_actions"]),
            "connector_required": cid in CONNECTOR_REQUIRED,
            "external_api_required": cid in EXTERNAL_API_REQUIRED,
            "high_risk_guard_required": len(c["level_3_blocked_actions"]) > 0,
            "safe_to_run_manually": bool(c["level_1_allowed_actions"]),
            "needs_ray_approval": bool(c["level_2_approval_gated_actions"]),
            "needs_separate_contract": bool(c["level_3_blocked_actions"]),
            "risk_notes": c["risk_notes"],
            "next_recommended_action": c["next_recommended_action"],
        })

    schedule_ready = [c["category_id"] for c in categories if c["schedule_ready"]]
    disabled_or_blocked = [c["category_id"] for c in categories if c["high_risk_guard_required"]]
    safe_manual = [c["category_id"] for c in categories if c["safe_to_run_manually"]]
    needs_contract = sorted({a for c in CATEGORY_MATRIX for a in c["level_3_blocked_actions"]})
    needs_connector = [c["category_id"] for c in categories if c["connector_required"]]
    needs_approval = [c["category_id"] for c in categories if c["needs_ray_approval"]]

    top_risks = [g["label"] for g in HIGH_RISK_GUARDS[:6]]
    hermes_next = "Enable schedule-ready Level 1 reports (research/SEO/affiliate/trading-paper) as manual runs; keep all connectors and schedulers approval-gated."
    ray_can_ignore = "Internal scoring/routing/reports and paper-only trading research — these run autonomously and do not need per-item approval."
    future_ui = "Automation Control Center: Level 1/2/3 counts, schedule-ready list, connector/external-API needs, high-risk guard status, top risk, and next safe automation."

    counts = {
        "total_categories": len(categories),
        "level_1_internal": sum(1 for c in categories if c["safe_to_run_manually"]),
        "level_2_gated": sum(1 for c in categories if c["needs_ray_approval"]),
        "level_3_blocked": sum(1 for c in categories if c["needs_separate_contract"]),
        "schedule_ready": len(schedule_ready),
        "scheduler_approval_required": sum(1 for c in categories if c["scheduler_approval_required"]),
        "connector_required": len(needs_connector),
        "external_api_required": sum(1 for c in categories if c["external_api_required"]),
        "high_risk_guard_required": len(disabled_or_blocked),
    }

    return {
        "ok": True,
        "title": "Nexus Automation Control Center",
        "generated_at": now(),
        "dry_run": True,
        "levels": LEVELS,
        "categories": categories,
        "schedule_ready": schedule_ready,
        "disabled_or_blocked": disabled_or_blocked,
        "safe_to_run_manually": safe_manual,
        "needs_separate_contract": needs_contract,
        "needs_connector": needs_connector,
        "needs_ray_approval": needs_approval,
        "hermes_recommended_next_automation": hermes_next,
        "top_automation_risks": top_risks,
        "what_ray_can_ignore_for_now": ray_can_ignore,
        "what_should_show_in_future_ui": future_ui,
        "counts": counts,
        "summary": f"Classified {len(categories)} categories across 3 automation levels. Nothing activated, published, sent, traded, or deployed.",
        "safety": {
            "scheduler_started": False,
            "cron_launchd_systemd_created": False,
            "publish_send_trade_deploy": False,
            "external_ai_called": False,
            "media_download": False,
            "broad_scrape": False,
            "secrets_printed": False,
        },
    }


def write_md(report: dict, path: Path) -> None:
    lines = [
        f"# {report['title']}",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- dry_run: {report['dry_run']}",
        f"- ok: {report['ok']}",
        "- scheduler_started: false",
        "- publish_send_trade_deploy: false",
        "- external_ai_called: false",
        "- media_download: false",
        "- broad_scrape: false",
        "",
        "## Counts",
    ]
    for k, v in report["counts"].items():
        lines.append(f"- {k}: {v}")
    lines += ["", "## Hermes recommended next automation", report["hermes_recommended_next_automation"]]
    lines += ["", "## Top automation risks"] + [f"- {r}" for r in report["top_automation_risks"]]
    lines += ["", "## Schedule-ready categories"] + [f"- {c}" for c in report["schedule_ready"]]
    lines += ["", "## Needs Ray approval"] + [f"- {c}" for c in report["needs_ray_approval"]]
    lines += ["", "## Blocked / needs separate contract"] + [f"- {c}" for c in report["needs_separate_contract"]]
    lines += ["", "## What Ray can ignore for now", report["what_ray_can_ignore_for_now"]]
    lines += ["", "## Per-category"]
    for c in report["categories"]:
        lines.append(f"### {c['category_name']} ({c['category_id']}) — {c['owner_department']}")
        lines.append(f"- Level 1 (autonomous): {', '.join(c['level_1_allowed_actions']) or '—'}")
        lines.append(f"- Level 2 (approval-gated): {', '.join(c['level_2_approval_gated_actions']) or '—'}")
        lines.append(f"- Level 3 (blocked): {', '.join(c['level_3_blocked_actions']) or '—'}")
        lines.append(f"- next: {c['next_recommended_action']}")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Automation Control Center report.")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()
    report = build_report()
    RUNTIME.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME.write_text(json.dumps(report, indent=2))
    CENTER_RUNTIME.write_text(json.dumps(report, indent=2))
    write_md(report, MANUAL)
    write_md(report, CENTER_MANUAL)
    if args.report_path:
        p = Path(args.report_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(report, indent=2))
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Automation control report written: {RUNTIME.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
