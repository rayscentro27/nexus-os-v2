#!/usr/bin/env python3
"""Manual daily department feeder digest.

Dry-run by default. Does not install/start schedulers, run capture, call external AI,
publish, send, trade, deploy, or touch v1 workers.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "social"))
import _supabase as sb  # noqa: E402

RUNTIME_JSON = ROOT / "reports" / "runtime" / "daily_department_digest_latest.json"
MANUAL_MD = ROOT / "reports" / "manual_publish" / "daily_department_digest_latest.md"

DEFAULT_FEEDERS = [
    "opportunity_lab_research_feeder",
    "ops_improvement_research_feeder",
    "creative_studio_project_feeder",
    "design_library_project_feeder",
    "seo_marketing_project_feeder",
    "agent_jobs_process_feeder",
    "command_center_summary_feeder",
    "approvals_decision_desk_feeder",
    "events_feed_ledger_feeder",
    "integrations_status_feeder",
    "goclear_revenue_hub_feeder",
    "trading_lab_demo_research_feeder",
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_feeder(feeder_id: str, *, dry_run: bool, limit: int) -> dict[str, Any]:
    cmd = [
        "python3",
        "scripts/automation/run_department_feeder.py",
        "--feeder-id",
        feeder_id,
        "--limit",
        str(limit),
        "--no-external-ai",
        "--json",
    ]
    cmd.append("--dry-run" if dry_run else "--no-dry-run")
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    parsed: dict[str, Any]
    try:
        parsed = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        parsed = {"ok": False, "raw_stdout": proc.stdout[-2000:]}
    return {
        "feeder_id": feeder_id,
        "returncode": proc.returncode,
        "ok": proc.returncode == 0 and bool(parsed.get("ok")),
        "stdout": parsed,
        "stderr_tail": proc.stderr[-1000:],
    }


def write_reports(report: dict[str, Any], explicit_path: str = "") -> None:
    RUNTIME_JSON.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME_JSON.write_text(json.dumps(report, indent=2))
    lines = [
        "# Daily Department Digest",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- dry_run: {report['dry_run']}",
        f"- limit_per_feeder: {report['limit_per_feeder']}",
        "- scheduler_started: false",
        "- capture_run: false",
        "- external_ai_called: false",
        "- publish_send_trade_deploy: false",
        "",
        "## Feeders",
    ]
    for item in report["results"]:
        summary = item.get("stdout", {})
        lines.append(f"- {item['feeder_id']}: ok={item['ok']} returncode={item['returncode']} results={summary.get('feeders', 'n/a')}")
    lines.extend(["", "## Skipped", *[f"- {s}" for s in report["skipped"]]])
    MANUAL_MD.parent.mkdir(parents=True, exist_ok=True)
    MANUAL_MD.write_text("\n".join(lines) + "\n")
    if explicit_path:
        p = Path(explicit_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(report, indent=2) if p.suffix.lower() == ".json" else "\n".join(lines) + "\n")


def maybe_write_event(report: dict[str, Any]) -> str | None:
    if report["dry_run"] or not sb.configured():
        return None
    _status, rows = sb.insert("nexus_events", {
        "lane": "automation",
        "source": "daily_department_digest",
        "action": "daily_department_digest_completed",
        "status": "success" if report["ok"] else "warning",
        "title": "Daily department digest completed",
        "summary": f"{len(report['results'])} feeders processed; scheduler_started=false",
        "payload": {
            "event_type": "daily_department_digest_completed",
            "dry_run": False,
            "limit_per_feeder": report["limit_per_feeder"],
            "feeders": [r["feeder_id"] for r in report["results"]],
            "scheduler_started": False,
            "capture_run": False,
            "external_ai_called": False,
        },
    })
    return rows[0]["id"] if isinstance(rows, list) and rows else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    parser.set_defaults(dry_run=True)
    parser.add_argument("--limit-per-feeder", type=int, default=3)
    parser.add_argument("--no-external-ai", action="store_true", default=True)
    parser.add_argument("--skip-trading", action="store_true")
    parser.add_argument("--skip-capture", action="store_true", default=True)
    parser.add_argument("--report-path", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.no_external_ai:
        print(json.dumps({"ok": False, "error": "no_external_ai_required"}, indent=2))
        return 2
    limit = max(1, min(args.limit_per_feeder, 5))
    feeders = list(DEFAULT_FEEDERS)
    skipped = ["source_capture_queue_worker", "NotebookLM live connector"]
    if args.skip_trading:
        feeders = [f for f in feeders if f != "trading_lab_demo_research_feeder"]
        skipped.append("trading_lab_demo_research_feeder")
    elif not args.dry_run:
        feeders = [f for f in feeders if f != "trading_lab_demo_research_feeder"]
        skipped.append("trading_lab_demo_research_feeder live run skipped; trading remains dry-run/status-only in digest")

    results = [run_feeder(feeder_id, dry_run=args.dry_run, limit=limit) for feeder_id in feeders]
    report = {
        "ok": all(r["ok"] for r in results),
        "generated_at": now(),
        "dry_run": args.dry_run,
        "limit_per_feeder": limit,
        "results": results,
        "skipped": skipped,
        "safety": {
            "scheduler_started": False,
            "capture_run": False,
            "external_ai_called": False,
            "publish_send_trade_deploy": False,
        },
        "nexus_event_id": None,
    }
    report["nexus_event_id"] = maybe_write_event(report)
    write_reports(report, args.report_path)
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
