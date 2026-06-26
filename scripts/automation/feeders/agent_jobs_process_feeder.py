"""Agent Jobs observability feeder. It summarizes existing rows/reports only."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from feeders.common import ROOT, make_candidate, run_candidates, score_value, table_rows, text

FEEDER_ID = "agent_jobs_process_feeder"
TASK_TYPE = "agent_job_project"
PROOF_EVENT = "agent_job_project_created"


def _agent_job(row: dict[str, Any]) -> dict[str, Any]:
    status = text(row.get("status"), "proposed")
    failed = "fail" in status.lower() or bool(row.get("error") or row.get("last_error"))
    return make_candidate(
        feeder_id=FEEDER_ID, task_type=TASK_TYPE, proof_event_type=PROOF_EVENT,
        department="agent_jobs", owner_tab="jobs", project_type="automation_job",
        unique_key=f"agent_jobs:{row.get('id')}", source_kind="agent_jobs", source_id=text(row.get("id")),
        title=f"Agent job review: {text(row.get('job_type') or row.get('name'), 'Automation job')}",
        summary=text(row.get("result_summary") or row.get("summary") or row.get("error") or row.get("last_error"), "Existing job needs status review."),
        pros=["Observability only.", "No job is run or scheduled."],
        cons=["Failures require manual diagnosis before rerun." if failed else "Reruns remain manual/dry-run unless separately approved."],
        recommendation="Create a safe diagnostic task." if failed else "Review proof/output before any rerun.",
        proposed_schedule="Manual review only; scheduler activation requires Ray approval.",
        next_action="Review job output/proof and decide whether to create a diagnostic task.",
        score=35 if failed else score_value(row.get("score"), fallback=55),
        status="needs_review" if failed else "proposed",
        risk_triggers=["scheduler_or_local_command"] if failed else [],
        approval_required=failed,
    )


def _task_request(row: dict[str, Any]) -> dict[str, Any] | None:
    task_type = text(row.get("task_type"))
    if task_type in {TASK_TYPE, "command_center_summary", "approval_decision_project", "event_ledger_project", "integration_status_project"}:
        return None
    return make_candidate(
        feeder_id=FEEDER_ID, task_type=TASK_TYPE, proof_event_type=PROOF_EVENT,
        department="agent_jobs", owner_tab="jobs", project_type="automation_job",
        unique_key=f"task_requests:{row.get('id')}", source_kind="task_requests", source_id=text(row.get("id")),
        title=f"Task request review: {task_type or 'Task request'}",
        summary=text(row.get("result_summary") or row.get("summary"), "Existing task request needs workforce status review."),
        pros=["Uses an existing task request.", "No worker is executed."],
        cons=["Execution remains gated by existing policy."],
        recommendation="Review status and create follow-up only if needed.",
        proposed_schedule="Manual review only; no scheduler activation.",
        next_action="Open Agent Jobs and inspect the related task request.",
        score=score_value(row.get("score"), fallback=50),
        status=text(row.get("status"), "proposed"),
    )


def _report(path: Path) -> dict[str, Any]:
    rel = str(path.relative_to(ROOT))
    return make_candidate(
        feeder_id=FEEDER_ID, task_type=TASK_TYPE, proof_event_type=PROOF_EVENT,
        department="agent_jobs", owner_tab="jobs", project_type="automation_job",
        unique_key=f"report:{rel}", source_kind="local_report", source_id=rel,
        title=f"Process report review: {path.name}",
        summary=f"Local report available for manual automation/workforce review: {rel}.",
        pros=["Uses local report metadata only.", "No job or scheduler is started."],
        cons=["Report content should be inspected manually before follow-up work."],
        recommendation="Review the report and create a focused diagnostic task if needed.",
        proposed_schedule="Manual review this week.",
        next_action="Open the report and decide whether a diagnostic task is needed.",
        score=45,
    )


def build_candidates(sb, limit: int) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for row in table_rows(sb, "agent_jobs", f"select=*&order=created_at.desc&limit={limit * 3}"):
        candidates.append(_agent_job(row))
    for row in table_rows(sb, "task_requests", f"select=*&order=created_at.desc&limit={limit * 3}"):
        c = _task_request(row)
        if c:
            candidates.append(c)
    for folder in (ROOT / "reports" / "runtime", ROOT / "reports" / "manual_publish"):
        for path in sorted(folder.glob("*latest.md"))[:limit]:
            candidates.append(_report(path))
    return candidates


def run(sb, *, dry_run: bool, limit: int) -> dict[str, Any]:
    return run_candidates(sb, feeder_id=FEEDER_ID, task_type=TASK_TYPE, proof_event_type=PROOF_EVENT,
                          dry_run=dry_run, limit=limit, candidates=build_candidates(sb, limit))
