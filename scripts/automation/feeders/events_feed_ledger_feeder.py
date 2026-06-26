"""Events Feed ledger feeder. It summarizes recent proof rows without modifying history."""
from __future__ import annotations

from typing import Any

from feeders.common import make_candidate, run_candidates, table_rows, text

FEEDER_ID = "events_feed_ledger_feeder"
TASK_TYPE = "event_ledger_project"
PROOF_EVENT = "event_ledger_summary_created"


def _event(row: dict[str, Any]) -> dict[str, Any]:
    action = text(row.get("action"), "nexus_event")
    status = text(row.get("status"), "summarized")
    failed = "fail" in status.lower() or "error" in status.lower()
    return make_candidate(
        feeder_id=FEEDER_ID, task_type=TASK_TYPE, proof_event_type=PROOF_EVENT,
        department="events_feed", owner_tab="events", project_type="proof_event_summary",
        unique_key=f"nexus_events:{row.get('id')}", source_kind="nexus_events", source_id=text(row.get("id")),
        title=f"Proof event summary: {text(row.get('title') or action, 'Nexus event')}",
        summary=text(row.get("summary"), f"Recent proof event action={action}, status={status}."),
        pros=["Summarizes existing proof/history.", "Does not modify the historical event."],
        cons=["Use source event for full context if needed."],
        recommendation="Review related department if the event indicates risk or failed work." if failed else "Keep as proof; no action unless linked department needs follow-up.",
        proposed_schedule="Ledger review during manual operations.",
        next_action="Open Events Feed and inspect related proof if needed.",
        score=35 if failed else 50,
        status="needs_review" if failed else "summarized",
        approval_required=False,
    )


def build_candidates(sb, limit: int) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for row in table_rows(sb, "nexus_events", f"select=id,action,status,title,summary,payload,created_at&order=created_at.desc&limit={limit * 6}"):
        action = text(row.get("action")).lower()
        if action.endswith("_project_created") or action in {"command_center_summary_created", "event_ledger_summary_created"}:
            continue
        blob = " ".join([action, text(row.get("title")), text(row.get("summary"))]).lower()
        if any(term in blob for term in ("trading", "trade", "oanda", "paper_only", "demo connection")):
            continue
        candidates.append(_event(row))
    return candidates


def run(sb, *, dry_run: bool, limit: int) -> dict[str, Any]:
    return run_candidates(sb, feeder_id=FEEDER_ID, task_type=TASK_TYPE, proof_event_type=PROOF_EVENT,
                          dry_run=dry_run, limit=limit, candidates=build_candidates(sb, limit))
