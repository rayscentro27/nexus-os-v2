#!/usr/bin/env python3
"""Run five synthetic dispute workflows through mock connectors only."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "audit"))
from full_engine_common import SUPABASE, now, read_json, record, write_json, write_report  # noqa: E402


def build() -> dict:
    cases = read_json(ROOT / "configs" / "dispute_simulation_cases.json", {}).get("cases", [])
    registry = {item["connector_id"]: item for item in read_json(ROOT / "configs" / "connector_registry.json", {}).get("connectors", [])}
    workflows, tasks, letters, approvals, actions, events, guide, hermes = [], [], [], [], [], [], [], []
    for case in cases:
        case_id = case["case_id"]
        connector_id = "collector_dispute_connector" if "collection" in case_id else "creditor_dispute_connector" if "goodwill" in case_id else "bureau_dispute_connector"
        connector = registry[connector_id]
        workflows.append(record(f"workflow-{case_id}", "dispute_workflow_test", case_id.replace("_", " ").title(),
            client_id=case["synthetic_client_id"], status="ready_for_Ray_review", risk_level=case["risk_level"],
            automation_level="approval_gated", approval_required=True, summary=case["issue_claim"],
            required_documents=case["required_documents"], blocked_external_actions=case["blocked_external_actions"],
            recommended_next_action=case["expected_next_step"]))
        tasks.append(record(f"task-{case_id}", "dispute_client_task", f"Collect documents: {case_id}", client_id=case["synthetic_client_id"],
            status="ready_for_Supabase_insertion", priority="high", risk_level=case["risk_level"], client_visible=True,
            required_documents=case["required_documents"], recommended_next_action="Upload synthetic proof only, then request GoClear review."))
        letters.append(record(f"letter-{case_id}", "dispute_letter_draft", case["recommended_letter_type"].title(), client_id=case["synthetic_client_id"],
            status="ready_for_Ray_review", priority="high", risk_level=case["risk_level"], automation_level="approval_gated",
            approval_required=True, sent=False, recipient=f"{case['creditor_or_collector']} ({case['bureau']}) — simulation only",
            account_masked=case["account_masked"], draft_body=f"SIMULATION DRAFT ONLY. Please review the synthetic {case['item_type']} record for the stated accuracy/documentation issue. No external delivery is authorized.",
            recommended_next_action="Ray/GoClear reviews facts and wording; sending remains blocked."))
        approvals.append(record(f"approval-{case_id}", "dispute_approval_card", f"Review synthetic dispute case: {case_id}",
            client_id=case["synthetic_client_id"], status="ready_for_Ray_review", priority="high", risk_level=case["risk_level"],
            automation_level="approval_gated", approval_required=True, options=["approve_draft_only", "reject", "defer"],
            exact_decision_needed="Approve the internal draft/workflow only; do not authorize sending.", recommended_next_action="Review in Ray Review."))
        actions.append(record(f"connector-{case_id}", "dispute_connector_action", f"Mock {connector_id} action", client_id=case["synthetic_client_id"],
            status="mock", risk_level=case["risk_level"], automation_level="blocked", approval_required=True,
            connector_id=connector_id, connector_mode=connector["mode"], live_enabled=False, attempted=False, sent=False,
            recommended_next_action="Retain as proof; no external connector call."))
        events.append(record(f"proof-{case_id}", "dispute_proof_event", f"Synthetic case processed: {case_id}",
            client_id=case["synthetic_client_id"], status="internal_active", summary="Generated task, draft metadata, approval, Hermes note, Nexus Guide status, and mock connector proof."))
        guide.append(record(f"guide-{case_id}", "dispute_client_guide_status", "Nexus Guide case status", client_id=case["synthetic_client_id"],
            status="demo_static", client_visible=True, summary=case["client_visible_status"],
            recommended_next_action="Complete the listed documents and wait for GoClear review; nothing has been sent."))
        hermes.append(record(f"hermes-{case_id}", "dispute_hermes_review", "Hermes admin review note", client_id=case["synthetic_client_id"],
            status="ready_for_Ray_review", risk_level=case["risk_level"], automation_level="approval_gated", client_visible=False,
            summary=f"Review synthetic evidence for {case['dispute_reason']}. Keep all external actions blocked.",
            recommended_next_action="Validate documents and recommend approve/reject/defer to Ray."))

    exports = {
        "dispute_workflow_test_latest.json": workflows, "dispute_client_tasks_latest.json": tasks,
        "dispute_letter_drafts_latest.json": letters, "dispute_approval_cards_latest.json": approvals,
        "dispute_connector_actions_latest.json": actions, "dispute_proof_events_latest.json": events,
        "dispute_client_guide_status_latest.json": guide, "dispute_hermes_review_latest.json": hermes,
    }
    for filename, data in exports.items():
        write_json(SUPABASE / filename, data)
    blocked = sorted({action for case in cases for action in case["blocked_external_actions"]})
    report = {
        "ok": True, "mode": "mock", "external_action_performed": False, "real_client_data_used": False,
        "disputes_sent": 0, "creditors_contacted": 0, "collectors_contacted": 0, "bureaus_contacted": 0,
        "letters_drafted": len(letters), "approval_cards_created": len(approvals), "client_tasks_created": len(tasks),
        "mock_connector_actions_created": len(actions), "proof_events_created": len(events), "blocked_actions": blocked,
        "ready_for_ray_review": [item["id"] for item in approvals], "cases_tested": len(cases),
        "summary": "Five synthetic dispute workflows completed end-to-end through mock/blocked connector actions; nothing was sent.",
    }
    write_report("dispute_simulation_lab", "Dispute Simulation Lab", report, {"Cases": workflows, "Blocked actions": blocked})
    return report


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--json", action="store_true"); args = parser.parse_args()
    report = build(); print(json.dumps(report, indent=2) if args.json else report["summary"]); return 0


if __name__ == "__main__":
    raise SystemExit(main())
