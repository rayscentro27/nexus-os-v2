#!/usr/bin/env python3
"""Part 0 — AI Access + Client Workflow project review (pre-build audit).

Deterministic, local-first. Documents the current state and what to reuse vs add for the AI
Department Access Controls + Client Vault contract layer. No external calls, no DB writes.

    python3 scripts/ai_access/generate_ai_client_workflow_project_review.py --dry-run --json
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RUNTIME = ROOT / "reports" / "runtime" / "ai_client_workflow_project_review_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "ai_client_workflow_project_review_latest.md"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def exists(rel: str) -> bool:
    return (ROOT / rel).exists()


def build() -> dict:
    automation_files = [
        "src/config/nexusAutomationLevels.ts",
        "src/config/nexusAutomationCategoryMatrix.ts",
        "src/config/nexusHighRiskGuards.ts",
        "src/config/nexusActionPolicy.ts",
        "src/config/rayReviewQueuePolicy.ts",
        "scripts/automation/generate_automation_control_report.py",
        "scripts/automation/verify_automation_policy.py",
        "scripts/automation/verify_high_risk_guards.py",
    ]
    client_workflow_files = [
        "src/config/clientWorkflow.ts",
        "src/config/clientWorkflowReminders.ts",
        "src/config/clientWorkflowAffiliate.ts",
        "src/lib/clientWorkflowEngine.ts",
        "src/lib/clientWorkflowHermes.ts",
        "supabase/migrations/20260629090000_client_workflow_engine.sql",
        "scripts/client_workflow/generate_client_workflow_report.py",
        "scripts/client_workflow/generate_affiliate_recommendation_report.py",
        "scripts/client_workflow/generate_stuck_client_report.py",
        "scripts/client_workflow/generate_hermes_client_recommendations.py",
        "scripts/client_workflow/verify_client_workflow_policy.py",
    ]
    automation_complete = all(exists(f) for f in automation_files)
    client_workflow_present = all(exists(f) for f in client_workflow_files)

    return {
        "ok": True,
        "title": "AI Access + Client Workflow Project Review (Pre-Build Audit)",
        "generated_at": now(),
        "dry_run": True,
        "q1_automation_control_center_complete": automation_complete,
        "q1_detail": {f: exists(f) for f in automation_files},
        "q2_reuse": [
            "task_requests + approvals + Ray Review Queue (rayReviewQueuePolicy.ts, build_ray_review_queue.py) for gating.",
            "nexus_events proof ledger; scripts/research/common.py write_report + scripts/social/_supabase.py conventions.",
            "Automation levels/guards (nexusAutomationLevels/Policy/Matrix/HighRiskGuards) — classify every AI action.",
            "Client workflow engine (clientWorkflow*.ts, clientWorkflowHermes.ts) already built in commit c75ffc0.",
            "MissionControl ClientWorkflowCard for Command Center visibility.",
            "scripts/compliance/classify_claim_risk.py for client-facing text gating.",
        ],
        "q3_client_workflow_exists": client_workflow_present,
        "q3_detail": "Client Workflow Engine V1 (stages, credit source flow, SmartCredit shell, scoring, business setup, letters/mailing, reminders, Hermes recs) shipped in commit c75ffc0. This task reuses it and adds the AI access + Client Vault contract layer in front of it.",
        "q4_approval_patterns": [
            "rayReviewQueuePolicy.ts classification + decision reasons (incl. blocked_high_risk_escalation).",
            "nexusActionPolicy.ts getAutomationApprovalDisposition / shouldCreateApprovalRow / isBlockedFromDirectApproval.",
        ],
        "q5_hermes_command_center_patterns": [
            "MissionControl chiprow + card pattern; buildHermesWorkflowDigest for sanitized aggregate counts.",
            "nexusResearchReports.ts + report reader for report visibility.",
        ],
        "q6_affiliate_revenue_patterns": [
            "partner_offers + client_recommendations tables; affiliateOpportunityTypes/Tracker.",
            "clientWorkflowAffiliate.ts (partner vs DIY map); goclearRevenueHub revenue scoring.",
        ],
        "q7_to_add": [
            "AI department roles + per-agent access policy + client data sensitivity policy + access-policy lib.",
            "Hermes no-raw-client-data redaction policy + sanitized client signals model.",
            "Credit Specialist Supabase-only access contract + Researcher AI no-PII contract.",
            "Client Vault CONTRACT + mock/dev adapter only (no live connection, no 2nd Supabase, no real data).",
            "Approved knowledge model; audit logging contract (mock events only).",
            "ai_access + client_vault verification/report scripts; Command Center AI access/vault status; CRM-eval-later doc.",
        ],
        "q8_do_not_duplicate": [
            "Do NOT rebuild the client workflow engine — reuse commit c75ffc0.",
            "Do NOT rebuild approvals/Ray Review/automation levels — reuse.",
            "Do NOT add a real Client Vault / 2nd Supabase / real client data — mock adapter only.",
            "Do NOT integrate any CRM repo (Twenty/Relaticle/Atomic/Open Mercato/NextCRM/crm-logic).",
        ],
        "q9_migrations_needed": "None required for v1. Client Vault is contract + mock adapter only; durable client tables (0012) already exist for the local engine. No second Supabase project.",
        "q10_plan": [
            "1. AI department roles + access policy + sensitivity policy + lib (Parts 2-5).",
            "2. Hermes redaction + sanitized signals (Parts 3, 8).",
            "3. Client Vault contract + mock adapter + data model + audit contract (Parts 6, 7, 12).",
            "4. Approved knowledge model + access views + blocked-access rules (Parts 9, 10, 11).",
            "5. ai_access + client_vault scripts (Part 11/23) reusing report conventions.",
            "6. Command Center AI access/vault status + CRM-eval doc (Parts 22, 25).",
            "7. Verify (build/watch/all dry-runs) then commit (Part 24).",
        ],
        "counts": {
            "automation_files_present": sum(1 for f in automation_files if exists(f)),
            "automation_files_total": len(automation_files),
            "client_workflow_files_present": sum(1 for f in client_workflow_files if exists(f)),
            "client_workflow_files_total": len(client_workflow_files),
        },
        "summary": (
            f"Automation Control Center complete={automation_complete}. Client Workflow Engine present={client_workflow_present}. "
            "This task adds the AI Department Access Controls + Client Vault CONTRACT (mock adapter only) in front of the existing "
            "engine. No real vault, no 2nd Supabase, no real client data, no CRM integration."
        ),
        "safety": {"db_writes": False, "external_calls": False, "real_vault_connected": False, "second_supabase_connected": False},
    }


def write_md(r: dict) -> None:
    L = [f"# {r['title']}", "", f"- generated_at: {r['generated_at']}", f"- ok: {r['ok']}",
         f"- automation_control_center_complete: {r['q1_automation_control_center_complete']}",
         f"- client_workflow_engine_present: {r['q3_client_workflow_exists']}", "", "## Summary", r["summary"], ""]
    L += ["## 2. Reuse"] + [f"- {x}" for x in r["q2_reuse"]] + [""]
    L += ["## 4. Approval / Ray Review patterns"] + [f"- {x}" for x in r["q4_approval_patterns"]] + [""]
    L += ["## 5. Hermes / Command Center patterns"] + [f"- {x}" for x in r["q5_hermes_command_center_patterns"]] + [""]
    L += ["## 6. Affiliate / revenue patterns"] + [f"- {x}" for x in r["q6_affiliate_revenue_patterns"]] + [""]
    L += ["## 7. To add"] + [f"- {x}" for x in r["q7_to_add"]] + [""]
    L += ["## 8. Do not duplicate"] + [f"- {x}" for x in r["q8_do_not_duplicate"]] + [""]
    L += ["## 9. Migrations needed", r["q9_migrations_needed"], ""]
    L += ["## 10. Plan"] + [f"- {x}" for x in r["q10_plan"]] + [""]
    MANUAL.parent.mkdir(parents=True, exist_ok=True)
    MANUAL.write_text("\n".join(L) + "\n")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", default=True)
    p.add_argument("--json", action="store_true")
    p.add_argument("--report-path", default="")
    a = p.parse_args()
    r = build()
    RUNTIME.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME.write_text(json.dumps(r, indent=2))
    write_md(r)
    if a.report_path:
        Path(a.report_path).write_text(json.dumps(r, indent=2))
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
