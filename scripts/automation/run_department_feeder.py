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
sys.path.insert(0, str(ROOT / "scripts" / "automation"))
import _supabase as sb  # noqa: E402
from feeders import (  # noqa: E402
    agent_jobs_process_feeder,
    approvals_decision_desk_feeder,
    command_center_summary_feeder,
    creative_studio_project_feeder,
    design_library_project_feeder,
    events_feed_ledger_feeder,
    integrations_status_feeder,
    opportunity_lab_research_feeder,
    seo_marketing_project_feeder,
    trading_lab_demo_research_feeder,
)

MAX_LIMIT = 50
DEFAULT_LIMIT = 5
RUNTIME = ROOT / "reports" / "runtime" / "nexus_department_automation_feeders_latest.md"
MANUAL = ROOT / "reports" / "manual_publish" / "nexus_department_automation_feeders_latest.md"
OPP_RUNTIME = ROOT / "reports" / "runtime" / "nexus_opportunity_lab_feeder_latest.md"
OPP_MANUAL = ROOT / "reports" / "manual_publish" / "nexus_opportunity_lab_feeder_latest.md"
REMAINING_RUNTIME = ROOT / "reports" / "runtime" / "nexus_remaining_department_feeders_latest.md"
REMAINING_MANUAL = ROOT / "reports" / "manual_publish" / "nexus_remaining_department_feeders_latest.md"

IMPLEMENTED_FEEDERS = {
    opportunity_lab_research_feeder.FEEDER_ID: opportunity_lab_research_feeder,
    creative_studio_project_feeder.FEEDER_ID: creative_studio_project_feeder,
    design_library_project_feeder.FEEDER_ID: design_library_project_feeder,
    seo_marketing_project_feeder.FEEDER_ID: seo_marketing_project_feeder,
    agent_jobs_process_feeder.FEEDER_ID: agent_jobs_process_feeder,
    command_center_summary_feeder.FEEDER_ID: command_center_summary_feeder,
    approvals_decision_desk_feeder.FEEDER_ID: approvals_decision_desk_feeder,
    events_feed_ledger_feeder.FEEDER_ID: events_feed_ledger_feeder,
    integrations_status_feeder.FEEDER_ID: integrations_status_feeder,
    trading_lab_demo_research_feeder.FEEDER_ID: trading_lab_demo_research_feeder,
}

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
        "proof_event_type": "opportunity_lab_project_created",
        "next_action": "Dry-run promotion candidates, then run bounded live creation only after reviewing candidates.",
    },
    {
        "feeder_id": "creative_studio_project_feeder",
        "name": "Creative Studio Project Feeder",
        "department": "creative_studio",
        "owner_tab": "creative",
        "source_type": "creative_assets/social_posts/enriched_research",
        "manual_command": "python3 scripts/automation/run_department_feeder.py --feeder-id creative_studio_project_feeder --dry-run --limit 5 --no-external-ai",
        "enabled_state": "manual_only",
        "risk_level": "medium",
        "writes_to_tables": ["task_requests", "nexus_events"],
        "proof_event_type": "creative_studio_project_created",
        "next_action": "Dry-run creative draft candidates; publish remains approval-gated and unexecuted.",
    },
    {
        "feeder_id": "seo_marketing_project_feeder",
        "name": "SEO / Marketing Project Feeder",
        "department": "growth",
        "owner_tab": "seo",
        "source_type": "seo_reports/enriched_research",
        "manual_command": "python3 scripts/automation/run_department_feeder.py --feeder-id seo_marketing_project_feeder --dry-run --limit 5 --no-external-ai",
        "enabled_state": "manual_only",
        "risk_level": "medium",
        "writes_to_tables": ["task_requests", "nexus_events"],
        "proof_event_type": "seo_marketing_project_created",
        "next_action": "Dry-run existing growth inputs; connector-backed scans remain future work.",
    },
    {
        "feeder_id": "design_library_project_feeder",
        "name": "Design Library Project Feeder",
        "department": "design_library",
        "owner_tab": "design",
        "source_type": "design_tables/creative_assets/enriched_research",
        "manual_command": "python3 scripts/automation/run_department_feeder.py --feeder-id design_library_project_feeder --dry-run --limit 5 --no-external-ai",
        "enabled_state": "manual_only",
        "risk_level": "low",
        "writes_to_tables": ["task_requests", "nexus_events"],
        "proof_event_type": "design_library_project_created",
        "next_action": "Dry-run existing design rows; no public use or image generation.",
    },
    {
        "feeder_id": "agent_jobs_process_feeder",
        "name": "Agent Jobs Process Feeder",
        "department": "agent_jobs",
        "owner_tab": "jobs",
        "source_type": "agent_jobs/task_requests/reports",
        "manual_command": "python3 scripts/automation/run_department_feeder.py --feeder-id agent_jobs_process_feeder --dry-run --limit 5 --no-external-ai",
        "enabled_state": "manual_only",
        "risk_level": "low",
        "writes_to_tables": ["task_requests", "nexus_events"],
        "proof_event_type": "agent_job_project_created",
        "next_action": "Dry-run job/process summaries; do not run or schedule jobs.",
    },
    {
        "feeder_id": "command_center_summary_feeder",
        "name": "Command Center Summary Feeder",
        "department": "command_center",
        "owner_tab": "command",
        "source_type": "feeder_registry",
        "manual_command": "python3 scripts/automation/run_department_feeder.py --feeder-id command_center_summary_feeder --dry-run --limit 5 --no-external-ai",
        "enabled_state": "manual_only",
        "risk_level": "low",
        "writes_to_tables": ["task_requests", "nexus_events"],
        "proof_event_type": "command_center_summary_created",
        "next_action": "Dry-run executive summary; no actions are executed.",
    },
    {
        "feeder_id": "approvals_decision_desk_feeder",
        "name": "Approvals Decision Desk Feeder",
        "department": "approvals",
        "owner_tab": "approvals",
        "source_type": "approvals",
        "manual_command": "python3 scripts/automation/run_department_feeder.py --feeder-id approvals_decision_desk_feeder --dry-run --limit 5 --no-external-ai",
        "enabled_state": "manual_only",
        "risk_level": "medium",
        "writes_to_tables": ["task_requests", "nexus_events"],
        "proof_event_type": "approval_decision_project_created",
        "next_action": "Dry-run approval decision cards; never approve or reject.",
    },
    {
        "feeder_id": "events_feed_ledger_feeder",
        "name": "Events Feed Ledger Feeder",
        "department": "events_feed",
        "owner_tab": "events",
        "source_type": "nexus_events",
        "manual_command": "python3 scripts/automation/run_department_feeder.py --feeder-id events_feed_ledger_feeder --dry-run --limit 5 --no-external-ai",
        "enabled_state": "manual_only",
        "risk_level": "low",
        "writes_to_tables": ["task_requests", "nexus_events"],
        "proof_event_type": "event_ledger_summary_created",
        "next_action": "Dry-run proof summaries; never modify historical events.",
    },
    {
        "feeder_id": "integrations_status_feeder",
        "name": "Integrations Status Feeder",
        "department": "integrations",
        "owner_tab": "integrations",
        "source_type": "integration_registry",
        "manual_command": "python3 scripts/automation/run_department_feeder.py --feeder-id integrations_status_feeder --dry-run --limit 5 --no-external-ai",
        "enabled_state": "manual_only",
        "risk_level": "medium",
        "writes_to_tables": ["task_requests", "nexus_events"],
        "proof_event_type": "integration_status_project_created",
        "next_action": "Dry-run connector status cards; never modify credentials.",
    },
    {
        "feeder_id": "trading_lab_demo_research_feeder",
        "name": "Trading Lab Demo Research Feeder",
        "department": "trading_lab",
        "owner_tab": "trading",
        "source_type": "vibe_trading_status/backtests/paper_reports",
        "manual_command": "python3 scripts/automation/run_department_feeder.py --feeder-id trading_lab_demo_research_feeder --dry-run --limit 5 --no-external-ai",
        "enabled_state": "manual_only",
        "risk_level": "high",
        "writes_to_tables": ["task_requests", "nexus_events"],
        "proof_event_type": "trading_lab_research_project_created",
        "next_action": "Dry-run paper/demo research cards only; live trading remains blocked.",
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
    if feeder["feeder_id"] == "creative_studio_project_feeder":
        return ["creative_assets", "social_posts", "publish_readiness_packages"]
    if feeder["feeder_id"] == "seo_marketing_project_feeder":
        return ["seo_opportunities or configured SEO connector required"]
    return [feeder["source_type"]]


def run_feeder(feeder: dict[str, Any], args) -> dict[str, Any]:
    if feeder["enabled_state"] in ("blocked", "disabled"):
        return {**feeder, "status": feeder["enabled_state"], "dry_run": args.dry_run, "results": [], "would_write": []}
    module = IMPLEMENTED_FEEDERS.get(feeder["feeder_id"])
    if module:
        if not sb.configured():
            return {**feeder, "status": "supabase_not_configured", "dry_run": args.dry_run, "results": []}
        res = module.run(sb, dry_run=args.dry_run, limit=args.limit)
        return {
            "feeder_id": feeder["feeder_id"],
            "name": feeder["name"],
            "department": feeder["department"],
            "enabled_state": feeder["enabled_state"],
            "risk_level": feeder["risk_level"],
            "manual_command": feeder["manual_command"],
            "target_tables": res["target_tables"],
            "proof_event_type": res["proof_event_type"],
            "dry_run": args.dry_run,
            "status": "dry_run_reported" if args.dry_run else "live_completed",
            "next_action": feeder["next_action"],
            **res,
        }
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
    if any(r.get("feeder_id") == opportunity_lab_research_feeder.FEEDER_ID for r in report["results"]):
        for path in (OPP_RUNTIME, OPP_MANUAL):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("\n".join(lines) + "\n")
    remaining_ids = set(IMPLEMENTED_FEEDERS) - {opportunity_lab_research_feeder.FEEDER_ID}
    if any(r.get("feeder_id") in remaining_ids for r in report["results"]):
        for path in (REMAINING_RUNTIME, REMAINING_MANUAL):
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
