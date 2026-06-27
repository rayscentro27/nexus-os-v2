#!/usr/bin/env python3
"""Part 1 — Client Workflow project review (pre-build audit).

Deterministic, local-first. Documents what already exists in Nexus OS v2 that the client workflow
engine should reuse, what is missing, and the recommended implementation plan. No external calls,
no DB writes, no publish/send/trade/deploy.

Usage:
    python3 scripts/client_workflow/generate_client_workflow_project_review.py --dry-run --json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RUNTIME = ROOT / "reports" / "runtime" / "client_workflow_project_review_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "client_workflow_project_review_latest.md"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


REUSE = [
    {"item": "task_requests table + lib/taskRequests.ts", "why": "Universal Ray-approved card system with sensitivity labels (credit_sensitive, funding_sensitive) and admin-only RLS. Use for workflow tasks, reminders, and recommendation cards."},
    {"item": "approvals table + Ray Review Queue (rayReviewQueuePolicy.ts, scripts/review/build_ray_review_queue.py)", "why": "Approval gating + one decision card per ready plan. Reuse instead of a new approval system."},
    {"item": "partner_offers + client_recommendations tables", "why": "Affiliate offers + per-client recommendations already modeled. Reuse for affiliate recommendation engine."},
    {"item": "affiliateOpportunityTypes.ts / affiliateOpportunityTracker.ts", "why": "Affiliate categories + scoring model already present; extend, do not duplicate."},
    {"item": "nexus_events (proof ledger)", "why": "Append-only proof events for every internal write. Reuse for workflow proof."},
    {"item": "nexusActionPolicy.ts + automation levels (nexusAutomationLevels/Policy/Matrix/HighRiskGuards)", "why": "Level 1/2/3 classification + guards already exist. Classify every client-workflow action through these."},
    {"item": "scripts/compliance/classify_claim_risk.py", "why": "Deterministic compliance classifier for credit/funding text. Reuse before any client-facing recommendation."},
    {"item": "goclearRevenueHub.ts + goclearRevenueMetrics.ts", "why": "Revenue potential scoring for upsell/affiliate opportunity scoring."},
    {"item": "scripts/research/common.py write_report + scripts/social/_supabase.py", "why": "Report JSON+MD writer and Supabase helpers (configured()/get/insert/q). Reuse conventions; scripts stay dry-run safe without DB."},
    {"item": "MissionControl.tsx + nexusDepartmentFeeders.ts", "why": "Command Center cards + feeder registry. Add a Client Workflow card; do not redesign UI."},
    {"item": "workspaces (tenant) + admin_users (RLS gate)", "why": "Tenant + admin RLS pattern. New tables reuse this exact RLS pattern."},
]

PARTIAL = [
    {"item": "GoClear / Apex tab (nexusTabs.ts)", "extend": "Exists as 'partial_connected' funding-readiness workspace using partner_offers/client_recommendations/task_requests. Extend with client workflow stages, credit/business scoring, letters, mailing, reminders."},
    {"item": "client_recommendations table", "extend": "Has client_label/title/recommendation_type/partner_offer_id. Extend usage for affiliate vs DIY path tracking via metadata; no schema change required for v1."},
    {"item": "Affiliate model", "extend": "AffiliateOpportunity is for monetization research, not per-client setup recommendations. Add a client-workflow affiliate recommendation layer that maps setup items -> partner/DIY options."},
]

MISSING = [
    "Client workflow status engine (signup -> funding-ready stages, days_stuck, progress %).",
    "Credit report source selection (SmartCredit recommended vs AnnualCreditReport.com free vs manual upload).",
    "SmartCredit connector shell (affiliate-link/partner statuses, NO password/scrape/login).",
    "Credit score history model + manual score entry.",
    "Credit analysis engine (utilization, negatives, blockers, readiness scores).",
    "Business setup engine (LLC/EIN/agent/address/phone/web/DUNS/bank/vendor) with partner vs DIY paths.",
    "Business bankability + funding readiness scoring.",
    "Credit repair letter packet + DocuPost/USPS mailing workflow (approval-gated, no auto-mail).",
    "Client progress reminder / stuck-client engine.",
    "Hermes client workflow recommendation layer (proactive, internal-only).",
    "Client workflow Python report generators + policy verification.",
    "Durable client-domain tables migration (client_profiles, score history, business setup, letters, mailings, reminders).",
]

DO_NOT_DUPLICATE = [
    "Do NOT build a new approval system — reuse approvals + Ray Review Queue.",
    "Do NOT build a new task/card table — reuse task_requests with new task_type values.",
    "Do NOT build a new affiliate table — reuse partner_offers + client_recommendations.",
    "Do NOT build a new proof system — reuse nexus_events.",
    "Do NOT build a new automation policy — reuse nexusActionPolicy + automation levels/guards.",
    "Do NOT build a new report writer — reuse scripts/research/common.py write_report.",
]

FILES_TO_UPDATE = [
    "src/components/command-center/MissionControl.tsx (add Client Workflow card).",
    "src/config/nexusDepartmentFeeders.ts (register client workflow feeders + automation levels).",
    "docs/operations/NEXUS_CLIENT_INTAKE_AUTOMATION_POLICY.md (cross-reference client workflow engine).",
]

FILES_TO_CREATE = [
    "src/config/clientWorkflow.ts, src/config/clientWorkflowReminders.ts, src/config/clientWorkflowAffiliate.ts",
    "src/lib/clientWorkflowEngine.ts, src/lib/clientWorkflowHermes.ts",
    "supabase/migrations/0012_client_workflow_engine.sql",
    "scripts/client_workflow/* (model + 6 generators/verifier)",
    "docs/operations/NEXUS_CLIENT_WORKFLOW_ENGINE.md",
]

TABLES_SUPPORTING = [
    "task_requests (cards/tasks/reminders/recommendations)",
    "approvals (approval gating)",
    "nexus_events (proof ledger)",
    "partner_offers + client_recommendations (affiliate)",
    "workspaces (tenant) + admin_users (RLS)",
]

MIGRATIONS_NEEDED = [
    "0012_client_workflow_engine.sql — additive, admin-only RLS (reusing existing pattern), sensitivity-labeled: client_profiles, client_workflow_stage_history, credit_score_history, business_setup_items, credit_letter_packets, client_mailings, client_reminders.",
]

APPROVAL_PATTERNS = [
    "Reuse rayReviewQueuePolicy.ts classification + build_ray_review_queue.py builder.",
    "One Ray Review card per READY plan (credit action plan / business action plan / client-facing plan), never per negative item.",
    "Level 2 (approval-gated): sends, client contact, mailing, dispute submission, funding applications, connector/scheduler activation.",
    "Level 3 (blocked): SmartCredit password storage/scrape/login, auto-mail, auto-file LLC/EIN, auto-open accounts, auto-apply funding, external AI on client credit data.",
]

COMMAND_CENTER_PATTERNS = [
    "Reuse MissionControl chiprow + ExecutiveOfficePanel card pattern (counts + notes).",
    "Reuse Hermes prep-brief/recommendation report pattern (nexusResearchReports.ts + report reader).",
    "Reuse nexusDepartmentFeeders automation-level registry for client workflow feeders.",
]

PART2_PLAN = [
    "1. TS models: clientWorkflow.ts (stages, sources, connector statuses, score model, business setup items, letter/mailing types), clientWorkflowReminders.ts (templates/timings), clientWorkflowAffiliate.ts (categories + partner/DIY map).",
    "2. TS engines: clientWorkflowEngine.ts (status/progress/days_stuck/scoring) + clientWorkflowHermes.ts (proactive recommendations).",
    "3. Migration 0012 (durable tables, admin RLS, sensitivity labels).",
    "4. Python: client_workflow_model.py (shared) + 6 dry-run generators/verifier with deterministic sample data.",
    "5. Command Center card + feeder registration + docs.",
    "6. Verify (build/watch/dry-runs) then commit.",
]


def build_report() -> dict:
    return {
        "ok": True,
        "title": "Client Workflow Project Review (Pre-Build Audit)",
        "generated_at": now(),
        "dry_run": True,
        "summary": "Audit complete. Strong reusable foundation exists (task_requests, approvals/Ray Review Queue, partner_offers/client_recommendations, nexus_events, automation levels, compliance classifier, report conventions). The durable client-domain tables and the workflow/scoring/letters/mailing/reminder/Hermes engines are missing and will be added additively without duplicating existing systems.",
        "q1_reusable": REUSE,
        "q2_partial_extend": PARTIAL,
        "q3_missing": MISSING,
        "q4_do_not_duplicate": DO_NOT_DUPLICATE,
        "q5_files_to_update": FILES_TO_UPDATE,
        "q5_files_to_create": FILES_TO_CREATE,
        "q6_tables_supporting": TABLES_SUPPORTING,
        "q7_migrations_needed": MIGRATIONS_NEEDED,
        "q8_approval_patterns": APPROVAL_PATTERNS,
        "q9_command_center_patterns": COMMAND_CENTER_PATTERNS,
        "q10_part2_plan": PART2_PLAN,
        "counts": {
            "reusable_items": len(REUSE),
            "partial_items": len(PARTIAL),
            "missing_items": len(MISSING),
            "migrations_needed": len(MIGRATIONS_NEEDED),
        },
        "safety": {"db_writes": False, "external_calls": False, "publish_send_trade_deploy": False},
    }


def write_md(report: dict) -> None:
    L = [f"# {report['title']}", "", f"- generated_at: {report['generated_at']}", f"- ok: {report['ok']}", "", "## Summary", report["summary"], ""]
    L += ["## 1. Reusable (do not rebuild)"] + [f"- **{r['item']}** — {r['why']}" for r in report["q1_reusable"]] + [""]
    L += ["## 2. Partial — extend"] + [f"- **{r['item']}** — {r['extend']}" for r in report["q2_partial_extend"]] + [""]
    L += ["## 3. Missing"] + [f"- {x}" for x in report["q3_missing"]] + [""]
    L += ["## 4. Do not duplicate"] + [f"- {x}" for x in report["q4_do_not_duplicate"]] + [""]
    L += ["## 5. Files to update"] + [f"- {x}" for x in report["q5_files_to_update"]] + [""]
    L += ["## 5. Files to create"] + [f"- {x}" for x in report["q5_files_to_create"]] + [""]
    L += ["## 6. Tables supporting this workflow"] + [f"- {x}" for x in report["q6_tables_supporting"]] + [""]
    L += ["## 7. Migrations needed"] + [f"- {x}" for x in report["q7_migrations_needed"]] + [""]
    L += ["## 8. Approval / Ray Review patterns to reuse"] + [f"- {x}" for x in report["q8_approval_patterns"]] + [""]
    L += ["## 9. Command Center / Hermes patterns to reuse"] + [f"- {x}" for x in report["q9_command_center_patterns"]] + [""]
    L += ["## 10. Part 2 implementation plan"] + [f"- {x}" for x in report["q10_part2_plan"]] + [""]
    MANUAL.parent.mkdir(parents=True, exist_ok=True)
    MANUAL.write_text("\n".join(L) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()
    report = build_report()
    RUNTIME.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME.write_text(json.dumps(report, indent=2))
    write_md(report)
    if args.report_path:
        Path(args.report_path).write_text(json.dumps(report, indent=2))
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(report["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
