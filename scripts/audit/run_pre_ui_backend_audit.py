#!/usr/bin/env python3
"""Pre-UI backend audit for YouTube research automation foundation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
import sys
sys.path.insert(0, str(ROOT / "scripts" / "research"))
from common import now, read_json, write_report  # noqa: E402

RUNTIME = ROOT / "reports" / "runtime" / "nexus_pre_ui_backend_audit_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "nexus_pre_ui_backend_audit_latest.md"

CHECKS = [
    ("watched_resources", "reports/runtime/watched_resource_registry_latest.json"),
    ("youtube_metadata_connector", "reports/runtime/youtube_metadata_connector_latest.json"),
    ("youtube_metadata_check", "reports/runtime/youtube_metadata_check_latest.json"),
    ("youtube_backfill", "reports/runtime/watched_resource_backfill_latest.json"),
    ("transcript_availability", "reports/runtime/youtube_transcript_availability_latest.json"),
    ("transcript_review", "reports/runtime/youtube_transcript_review_latest.json"),
    ("youtube_report", "reports/runtime/youtube_research_report_latest.json"),
    ("hermes_prep", "reports/runtime/hermes_youtube_prep_brief_latest.json"),
    ("seo_affiliate_conversion", "reports/runtime/youtube_to_seo_affiliate_plan_latest.json"),
    ("content_experiments", "reports/runtime/youtube_to_content_experiments_latest.json"),
    ("scheduler_candidates", "reports/runtime/scheduler_approval_candidates_latest.json"),
    ("ray_review_queue", "reports/runtime/ray_review_queue_builder_latest.json"),
]


def status_for(path: str) -> dict:
    p = ROOT / path
    if not p.exists():
        return {"status": "missing", "path": path}
    data = read_json(p)
    if data.get("ok") is True:
        return {"status": "ready" if data.get("dry_run") else "live_or_reported", "path": path, "counts": data.get("counts", {})}
    return {"status": "partial", "path": path, "error": data.get("error")}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()
    checks = {name: status_for(path) for name, path in CHECKS}
    report = {
        "ok": True,
        "title": "Nexus Pre-UI Backend Audit",
        "generated_at": now(),
        "dry_run": True,
        "checks": checks,
        "ready": [k for k, v in checks.items() if v["status"] in {"ready", "live_or_reported"}],
        "partial": [k for k, v in checks.items() if v["status"] == "partial"],
        "disabled": ["scheduler_activation", "media_download", "publish_send_trade_deploy", "live_trading"],
        "needs_ray_decision": ["scheduler approval candidates only"],
        "can_run_autonomously": ["metadata dry-runs", "transcript scoring from safe text", "reports", "Hermes prep", "internal experiment candidates"],
        "next_ui_image_set": ["Command Center YouTube status", "Source Intake watched channels", "YouTube report cards", "Hermes prep brief panel", "Scheduler Approval Center"],
        "counts": {"checks": len(checks), "ready": sum(1 for v in checks.values() if v["status"] in {"ready", "live_or_reported"}), "missing": sum(1 for v in checks.values() if v["status"] == "missing")},
        "safety": {"publish_send_trade_deploy": False, "scheduler_started": False, "media_downloaded": False, "external_ai_called": False},
    }
    write_report(report, RUNTIME, MANUAL, args.report_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
