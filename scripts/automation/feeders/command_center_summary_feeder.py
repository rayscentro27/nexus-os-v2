"""Command Center summary feeder. It creates an executive summary card only."""
from __future__ import annotations

from collections import Counter
from typing import Any

from feeders.common import make_candidate, run_candidates, table_rows, text

FEEDER_ID = "command_center_summary_feeder"
TASK_TYPE = "command_center_summary"
PROOF_EVENT = "command_center_summary_created"


def build_candidates(sb, limit: int) -> list[dict[str, Any]]:
    tasks = table_rows(sb, "task_requests", "select=id,task_type,status,payload,result_summary,created_at&order=created_at.desc&limit=100")
    approvals = table_rows(sb, "approvals", "select=id,status,item_type,title,created_at&order=created_at.desc&limit=50")
    events = table_rows(sb, "nexus_events", "select=id,action,status,title,created_at&order=created_at.desc&limit=50")

    departments = Counter(text((t.get("payload") or {}).get("department") or (t.get("payload") or {}).get("owner_tab") or "unknown") for t in tasks)
    needs_review = sum(1 for t in tasks if "review" in text(t.get("status")).lower() or bool((t.get("payload") or {}).get("approval_required")))
    blocked = sum(1 for t in tasks if "block" in text(t.get("status")).lower() or "fail" in text(t.get("status")).lower())
    pending_approvals = sum(1 for a in approvals if text(a.get("status")).lower() == "pending")
    event_count = len(events)

    summary = (
        f"Departments active: {', '.join(k for k, v in departments.most_common(6) if k != 'unknown') or 'none yet'}. "
        f"Needs review: {needs_review}. Blocked/failed: {blocked}. Pending approvals: {pending_approvals}. "
        f"Recent proof events checked: {event_count}."
    )
    recommendation = (
        "Review needs-review and pending approval cards first; keep scheduler activation disabled until Ray approves it."
        if needs_review or pending_approvals else
        "Review active department cards and choose the next feeder to run manually."
    )
    return [make_candidate(
        feeder_id=FEEDER_ID, task_type=TASK_TYPE, proof_event_type=PROOF_EVENT,
        department="command_center", owner_tab="command", project_type="executive_summary",
        unique_key="command_center:latest_manual_summary", source_kind="department_summary",
        title="Command Center feeder summary",
        summary=summary,
        pros=["Summarizes existing project cards and proof rows.", "No approvals or actions are modified."],
        cons=["Snapshot is only as fresh as current tables and manual feeder runs."],
        recommendation=recommendation,
        proposed_schedule="Manual summary now; future schedule requires approval.",
        next_action="Open Command Center, review risks, then choose approve/change/park decisions.",
        score=70 if needs_review or pending_approvals else 55,
        status="needs_review" if needs_review or pending_approvals else "summarized",
        metadata_extra={"department_counts": dict(departments), "pending_approvals": pending_approvals, "recent_events": event_count},
    )]


def run(sb, *, dry_run: bool, limit: int) -> dict[str, Any]:
    return run_candidates(sb, feeder_id=FEEDER_ID, task_type=TASK_TYPE, proof_event_type=PROOF_EVENT,
                          dry_run=dry_run, limit=limit, candidates=build_candidates(sb, limit))
