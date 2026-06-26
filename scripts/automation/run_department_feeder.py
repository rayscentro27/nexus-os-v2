#!/usr/bin/env python3
"""Manual Nexus department feeder runner.

Default is dry-run/report-only. This script does not start schedulers, run capture, call yt-dlp,
call external AI, publish, send, trade, deploy, or touch v1 workers.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "social"))
import _supabase as sb  # noqa: E402

MAX_LIMIT = 50
DEFAULT_LIMIT = 5
RUNTIME = ROOT / "reports" / "runtime" / "nexus_department_automation_feeders_latest.md"
MANUAL = ROOT / "reports" / "manual_publish" / "nexus_department_automation_feeders_latest.md"

FEEDERS: list[dict[str, Any]] = [
    {
        "feeder_id": "source_intake_enrichment_backfill",
        "name": "Source Intake Enrichment Backfill",
        "department": "source_intake",
        "owner_tab": "intake",
        "source_type": "research_sources",
        "manual_command": "python3 scripts/intake/backfill_project_enrichment.py --dry-run --limit 10 --no-external-ai",
        "enabled_state": "manual_only",
        "risk_level": "low",
        "writes_to_tables": ["research_sources.metadata", "transcript_reviews.metadata", "nexus_events"],
        "proof_event_type": "project_enrichment_backfilled",
        "next_action": "Run dry-run, then bounded metadata-only live backfill when safe.",
    },
    {
        "feeder_id": "source_capture_queue_worker",
        "name": "Source Capture Queue Worker",
        "department": "source_intake",
        "owner_tab": "intake",
        "source_type": "task_requests",
        "manual_command": "python3 scripts/intake/run_capture_queue_worker.py --once --limit 1 --dry-run --no-external-ai",
        "enabled_state": "manual_only",
        "risk_level": "medium",
        "writes_to_tables": ["task_requests", "research_sources", "intake_events", "transcript_reviews", "nexus_events"],
        "proof_event_type": "source_enriched_for_project_card",
        "next_action": "Keep dry-run default; live run only for safe queued items.",
    },
    {
        "feeder_id": "ops_improvement_research_feeder",
        "name": "Ops Improvement Research Feeder",
        "department": "ops_improvements",
        "owner_tab": "ops",
        "source_type": "docs_and_reports",
        "manual_command": "python3 scripts/automation/run_department_feeder.py --feeder-id ops_improvement_research_feeder --dry-run --limit 5 --no-external-ai",
        "enabled_state": "manual_only",
        "risk_level": "low",
        "writes_to_tables": ["task_requests", "nexus_events"],
        "proof_event_type": "department_feeder_ops_improvement_reported",
        "next_action": "Dry-run candidate creation from existing safe reports; live writes deferred.",
    },
    {
        "feeder_id": "opportunity_lab_research_feeder",
        "name": "Opportunity Lab Research Feeder",
        "department": "opportunity_lab",
        "owner_tab": "opportunities",
        "source_type": "enriched_research",
        "manual_command": "python3 scripts/automation/run_department_feeder.py --feeder-id opportunity_lab_research_feeder --dry-run --limit 5 --no-external-ai",
        "enabled_state": "manual_only",
        "risk_level": "low",
        "writes_to_tables": ["task_requests", "nexus_events"],
        "proof_event_type": "department_feeder_opportunity_reported",
        "next_action": "Dry-run promotion candidates; live creation can be added after review.",
    },
    {
        "feeder_id": "creative_design_project_feeder",
        "name": "Creative and Design Project Feeder",
        "department": "creative_studio",
        "owner_tab": "creative",
        "source_type": "creative_assets",
        "manual_command": "python3 scripts/automation/run_department_feeder.py --feeder-id creative_design_project_feeder --dry-run --limit 5 --no-external-ai",
        "enabled_state": "manual_only",
        "risk_level": "medium",
        "writes_to_tables": ["task_requests", "creative_assets.metadata", "nexus_events"],
        "proof_event_type": "department_feeder_creative_design_reported",
        "next_action": "Dry-run candidate mapping; publish remains approval-gated.",
    },
    {
        "feeder_id": "seo_marketing_project_feeder",
        "name": "SEO / Marketing Project Feeder",
        "department": "growth",
        "owner_tab": "seo",
        "source_type": "seo_reports",
        "manual_command": "python3 scripts/automation/run_department_feeder.py --feeder-id seo_marketing_project_feeder --dry-run --limit 5 --no-external-ai",
        "enabled_state": "needs_connector",
        "risk_level": "medium",
        "writes_to_tables": ["task_requests", "seo_opportunities", "nexus_events"],
        "proof_event_type": "department_feeder_seo_reported",
        "next_action": "Seed or connect SEO inputs before live feeder writes.",
    },
    {
        "feeder_id": "design_library_asset_organizer",
        "name": "Design Library Asset Organizer",
        "department": "design_library",
        "owner_tab": "design",
        "source_type": "design_tables",
        "manual_command": "python3 scripts/automation/run_department_feeder.py --feeder-id design_library_asset_organizer --dry-run --limit 5 --no-external-ai",
        "enabled_state": "manual_only",
        "risk_level": "low",
        "writes_to_tables": ["task_requests", "nexus_events"],
        "proof_event_type": "department_feeder_design_reported",
        "next_action": "Dry-run existing design rows; live writes deferred.",
    },
    {
        "feeder_id": "agent_jobs_process_registry_feeder",
        "name": "Agent Jobs Process Registry Feeder",
        "department": "agent_jobs",
        "owner_tab": "jobs",
        "source_type": "agent_jobs",
        "manual_command": "python3 scripts/automation/run_department_feeder.py --feeder-id agent_jobs_process_registry_feeder --dry-run --limit 5 --no-external-ai",
        "enabled_state": "manual_only",
        "risk_level": "low",
        "writes_to_tables": ["task_requests", "nexus_events"],
        "proof_event_type": "department_feeder_agent_jobs_reported",
        "next_action": "Dry-run job/process summary.",
    },
    {
        "feeder_id": "command_center_executive_summary_feeder",
        "name": "Command Center Executive Summary Feeder",
        "department": "command_center",
        "owner_tab": "command",
        "source_type": "feeder_registry",
        "manual_command": "python3 scripts/automation/run_department_feeder.py --department command_center --dry-run --limit 5 --no-external-ai",
        "enabled_state": "manual_only",
        "risk_level": "low",
        "writes_to_tables": ["nexus_events"],
        "proof_event_type": "department_feeder_command_center_reported",
        "next_action": "Review feeder summary in Command Center.",
    },
    {
        "feeder_id": "approvals_decision_desk_feeder",
        "name": "Approvals Decision Desk Feeder",
        "department": "approvals",
        "owner_tab": "approvals",
        "source_type": "approvals",
        "manual_command": "Open Approvals tab",
        "enabled_state": "manual_only",
        "risk_level": "medium",
        "writes_to_tables": ["approvals", "nexus_events"],
        "proof_event_type": "approval_required",
        "next_action": "Ray reviews pending approvals manually.",
    },
    {
        "feeder_id": "events_feed_ledger_feeder",
        "name": "Events Feed Ledger Feeder",
        "department": "events_feed",
        "owner_tab": "events",
        "source_type": "nexus_events",
        "manual_command": "Open Events Feed tab",
        "enabled_state": "manual_only",
        "risk_level": "low",
        "writes_to_tables": ["nexus_events"],
        "proof_event_type": "nexus_event",
        "next_action": "Use as proof stream for feeder runs.",
    },
    {
        "feeder_id": "integrations_connection_status_feeder",
        "name": "Integrations Connection Status Feeder",
        "department": "integrations",
        "owner_tab": "integrations",
        "source_type": "integration_registry",
        "manual_command": "npm run nexus:watch",
        "enabled_state": "manual_only",
        "risk_level": "medium",
        "writes_to_tables": ["system_health", "nexus_events"],
        "proof_event_type": "integration_status_reported",
        "next_action": "Run manual watch report; never print secrets.",
    },
    {
        "feeder_id": "trading_lab_demo_research_feeder",
        "name": "Trading Lab Demo Research Feeder",
        "department": "trading_lab",
        "owner_tab": "trading",
        "source_type": "demo_research",
        "manual_command": "python3 scripts/automation/run_department_feeder.py --feeder-id trading_lab_demo_research_feeder --dry-run --limit 5 --no-external-ai",
        "enabled_state": "blocked",
        "risk_level": "high",
        "writes_to_tables": ["task_requests", "nexus_events"],
        "proof_event_type": "department_feeder_trading_demo_reported",
        "next_action": "Keep research-only; do not place trades.",
    },
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def select_feeders(args) -> list[dict[str, Any]]:
    rows = FEEDERS
    if args.feeder_id:
        rows = [f for f in rows if f["feeder_id"] == args.feeder_id]
    if args.department:
        rows = [f for f in rows if f["department"] == args.department or f["owner_tab"] == args.department]
    return rows[: max(1, min(args.limit, MAX_LIMIT))]


def local_candidates(feeder: dict[str, Any], limit: int) -> list[str]:
    if feeder["feeder_id"] == "ops_improvement_research_feeder":
        return [str(p.relative_to(ROOT)) for p in sorted((ROOT / "reports" / "manual_publish").glob("nexus_*latest.md"))[:limit]]
    if feeder["feeder_id"] == "opportunity_lab_research_feeder":
        return ["research_sources with project_enrichment destination Opportunity Lab/GoClear/Apex"]
    if feeder["feeder_id"] == "creative_design_project_feeder":
        return ["creative_assets", "social_posts", "publish_readiness_packages"]
    if feeder["feeder_id"] == "seo_marketing_project_feeder":
        return ["seo_opportunities or configured SEO connector required"]
    return [feeder["source_type"]]


def run_feeder(feeder: dict[str, Any], args) -> dict[str, Any]:
    candidates = local_candidates(feeder, args.limit)
    out = {
        "feeder_id": feeder["feeder_id"],
        "name": feeder["name"],
        "department": feeder["department"],
        "enabled_state": feeder["enabled_state"],
        "risk_level": feeder["risk_level"],
        "manual_command": feeder["manual_command"],
        "target_tables": feeder["writes_to_tables"],
        "proof_event_type": feeder["proof_event_type"],
        "candidates": candidates,
        "dry_run": args.dry_run,
        "would_write": [] if args.dry_run else ["nexus_events"],
        "status": "dry_run_reported" if args.dry_run else "reported",
        "next_action": feeder["next_action"],
    }
    if feeder["enabled_state"] in ("blocked", "needs_connector"):
        out["status"] = feeder["enabled_state"]
        out["would_write"] = []
    if not args.dry_run and out["would_write"]:
        if not sb.configured():
            out["status"] = "supabase_not_configured"
            return out
        sb.event("automation", "department_feeder_reported", "info", feeder["name"],
                 f"{feeder['feeder_id']} status={feeder['enabled_state']}",
                 payload={"feeder": feeder, "candidates": candidates, "no_external_ai": True})
    return out


def write_report(report: dict[str, Any]) -> None:
    lines = [
        "# Nexus Department Automation Feeders",
        "",
        f"- generated_at: {now()}",
        f"- mode: {'DRY-RUN (no Supabase writes)' if report['dry_run'] else 'LIVE status report only'}",
        f"- feeders: {report['feeders']} · no_external_ai: true",
        "- scheduler_started: false · capture_run: false · publish/send/trade/deploy: false",
        "",
        "## Results",
    ]
    for item in report["results"]:
        lines.append(f"- {json.dumps(item, sort_keys=True)}")
    for path in (RUNTIME, MANUAL):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--feeder-id", default="")
    ap.add_argument("--department", default="")
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    ap.add_argument("--dry-run", dest="dry_run", action="store_true")
    ap.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    ap.set_defaults(dry_run=True)
    ap.add_argument("--no-external-ai", action="store_true", default=True)
    ap.add_argument("--report-path", default="")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    selected = select_feeders(args)
    if not selected:
        print(json.dumps({"ok": False, "error": "no_matching_feeders", "feeder_id": args.feeder_id, "department": args.department}, indent=2))
        return 2
    results = [run_feeder(feeder, args) for feeder in selected]
    report = {
        "ok": True,
        "dry_run": args.dry_run,
        "no_external_ai": True,
        "limit": max(1, min(args.limit, MAX_LIMIT)),
        "feeders": len(results),
        "results": results,
    }
    write_report(report)
    if args.report_path:
        Path(args.report_path).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
