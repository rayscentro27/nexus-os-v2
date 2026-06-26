"""Approvals Decision Desk feeder. Advisory only; it never approves or rejects."""
from __future__ import annotations

from typing import Any

from feeders.common import make_candidate, run_candidates, score_value, table_rows, text

FEEDER_ID = "approvals_decision_desk_feeder"
TASK_TYPE = "approval_decision_project"
PROOF_EVENT = "approval_decision_project_created"


def _approval(row: dict[str, Any]) -> dict[str, Any]:
    status = text(row.get("status"), "pending")
    pending = status.lower() == "pending"
    return make_candidate(
        feeder_id=FEEDER_ID, task_type=TASK_TYPE, proof_event_type=PROOF_EVENT,
        department="approvals", owner_tab="approvals", project_type="decision_item",
        unique_key=f"approvals:{row.get('id')}", source_kind="approvals", source_id=text(row.get("id")),
        title=f"Approval decision: {text(row.get('title') or row.get('item_type'), 'Approval item')}",
        summary=text(row.get("summary"), "Approval item needs Ray decision review."),
        pros=["Centralizes decision context.", "No approval/rejection is performed."],
        cons=["Any downstream publish/send/deploy/trade action remains gated."],
        recommendation="Ray should review risk and approve, reject, or request changes in Approvals.",
        proposed_schedule="Review pending approvals today; completed approvals need no action.",
        next_action="Open Approvals and make a human decision if still pending.",
        score=75 if pending else 40,
        status="needs_review" if pending else status,
        approval_required=pending,
        risk_triggers=["approval_required"] if pending else [],
    )


def _task(row: dict[str, Any]) -> dict[str, Any] | None:
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    if not payload.get("approval_required"):
        return None
    return make_candidate(
        feeder_id=FEEDER_ID, task_type=TASK_TYPE, proof_event_type=PROOF_EVENT,
        department="approvals", owner_tab="approvals", project_type="decision_item",
        unique_key=f"task_requests:{row.get('id')}", source_kind="task_requests", source_id=text(row.get("id")),
        title=f"Approval-required task: {text(payload.get('title') or row.get('task_type'), 'Task request')}",
        summary=text(payload.get("summary") or row.get("result_summary"), "Task request is marked approval-required."),
        pros=["Makes the approval requirement visible.", "No decision is executed."],
        cons=["Human review is still required."],
        recommendation=text(payload.get("recommendation"), "Ray should review before any risky next action."),
        proposed_schedule="Review before work continues.",
        next_action="Open Approvals or the owning department for the decision.",
        score=score_value(payload.get("score"), fallback=65),
        status="needs_review",
        approval_required=True,
        risk_triggers=["approval_required"],
    )


def build_candidates(sb, limit: int) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for row in table_rows(sb, "approvals", f"select=id,status,item_type,title,summary,payload,created_at&order=created_at.desc&limit={limit * 3}"):
        candidates.append(_approval(row))
    for row in table_rows(sb, "task_requests", f"select=*&order=created_at.desc&limit={limit * 4}"):
        c = _task(row)
        if c:
            candidates.append(c)
    return candidates


def run(sb, *, dry_run: bool, limit: int) -> dict[str, Any]:
    return run_candidates(sb, feeder_id=FEEDER_ID, task_type=TASK_TYPE, proof_event_type=PROOF_EVENT,
                          dry_run=dry_run, limit=limit, candidates=build_candidates(sb, limit))
