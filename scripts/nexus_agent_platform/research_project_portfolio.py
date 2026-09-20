"""Objective/project aggregation above the existing Research work queue.

The queue remains authoritative for work-item scheduling.  This module is a
read model only: it groups children by objective_id and derives a project
status from all relevant children, leases, evaluator returns, and handoffs.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Iterable

from nexus_agent_platform.research_work_queue import STATUS, WORK_CLASSES, default_queue

TERMINAL = {"COMPLETE", "BLOCKED_EXTERNAL", "FAILED_FINAL", "PARKED", "SUPERSEDED"}
ACTIVE = {"QUEUED", "WAITING", "IN_PROGRESS", "MONITORING", "FAILED_RETRYABLE"}


def _ignored_for_portfolio(item: dict[str, Any]) -> bool:
    """Keep archived certification/history out of live project obligations."""
    if item.get("status") != "PARKED":
        return False
    marker = str(item.get("blocker_type") or item.get("terminal_reason") or "").upper()
    return marker.startswith(("PORTFOLIO_TEST_WINDOW_CLOSED", "STALE_", "LEGACY_"))


def _time(value: Any) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return datetime.min.replace(tzinfo=timezone.utc)


def _required(item: dict[str, Any]) -> bool:
    explicit = item.get("required_work")
    if explicit is not None:
        return bool(explicit)
    role = str(item.get("work_role") or "").upper()
    if role in {"OPTIONAL", "MONITORING", "BACKGROUND"}:
        return False
    return str(item.get("work_class") or "").upper() not in {"MONITORED", "GENERAL_DISCOVERY"}


def _needs_more(item: dict[str, Any]) -> bool:
    # A completed follow-up represents returned evidence.  Only an unresolved
    # child may keep its parent in NEEDS_MORE_RESEARCH; otherwise every
    # historical Alpha request would permanently pin the project.
    if item.get("status") in TERMINAL:
        return False
    result = item.get("last_result") or {}
    if item.get("alpha_followup_required") or str(item.get("selection_reason") or "").lower() == "alpha_followup":
        return True
    return str(result.get("alpha_status") or result.get("decision") or "").upper() in {"RESEARCH_MORE", "MORE_RESEARCH_REQUIRED"}


def _department_wait(item: dict[str, Any]) -> bool:
    return bool(item.get("department_target")) and item.get("status") in {"QUEUED", "WAITING", "IN_PROGRESS"}


def _project_status(children: list[dict[str, Any]]) -> str:
    required = [row for row in children if _required(row)]
    if not required:
        required = children
    if any(row.get("status") == "IN_PROGRESS" for row in required):
        return "ACTIVE"
    if any(_needs_more(row) for row in required if row.get("status") not in {"SUPERSEDED", "PARKED"}):
        return "NEEDS_MORE_RESEARCH"
    if any(_department_wait(row) for row in required):
        return "WAITING_FOR_DEPARTMENT"
    viable_active = [row for row in required if row.get("status") in {"QUEUED", "WAITING", "FAILED_RETRYABLE"}]
    if viable_active:
        return "WAITING" if any(row.get("status") == "WAITING" for row in viable_active) else "ACTIVE"
    required_blocked = [row for row in required if row.get("status") in {"BLOCKED_EXTERNAL", "FAILED_FINAL"}]
    required_terminal = [row for row in required if row.get("status") in TERMINAL]
    if required_blocked and not any(row.get("status") == "COMPLETE" for row in required):
        return "BLOCKED"
    if required_terminal and all(row.get("status") in TERMINAL for row in required):
        if any(row.get("status") == "COMPLETE" for row in required):
            return "COMPLETE"
        return "BLOCKED"
    return "NOT_STARTED"


def aggregate_project(objective_id: str, children: Iterable[dict[str, Any]]) -> dict[str, Any]:
    all_rows = [dict(row) for row in children if str(row.get("objective_id") or "") == str(objective_id)]
    rows = [row for row in all_rows if not _ignored_for_portfolio(row)]
    required = [row for row in rows if _required(row)]
    optional = [row for row in rows if not _required(row)]
    status = _project_status(rows)
    active = [row for row in rows if row.get("status") in ACTIVE]
    blocked = [row for row in rows if row.get("status") in {"BLOCKED_EXTERNAL", "FAILED_FINAL"}]
    followups = [row for row in rows if _needs_more(row)]
    departments = sorted({str(row.get("department_target")) for row in rows if row.get("department_target")})
    required_terminal = [row for row in required if row.get("status") in TERMINAL]
    priority_rows = [row for row in required if row.get("status") not in TERMINAL] or required or rows
    project_priority = min((int(row.get("priority", 50)) for row in priority_rows), default=50)
    oldest = min((_time(row.get("created_at")) for row in active), default=None)
    return {
        "objective_id": str(objective_id),
        "status": status,
        "child_work_count": len(rows),
        "ignored_historical_work_count": len(all_rows) - len(rows),
        "child_states": dict(Counter(str(row.get("status") or "UNKNOWN") for row in rows)),
        "required_work_count": len(required),
        "required_work_completed": sum(1 for row in required if row.get("status") == "COMPLETE"),
        "required_work_remaining": sum(1 for row in required if row.get("status") not in TERMINAL),
        "optional_work_remaining": sum(1 for row in optional if row.get("status") not in TERMINAL),
        "active_work_count": len(active),
        "blocked_work_count": len(blocked),
        "followups_outstanding": len(followups),
        "department_dependencies": departments,
        "project_priority": project_priority,
        "oldest_active_at": oldest.isoformat() if oldest else None,
        "active_work_ids": [row.get("work_id") for row in active],
        "blocked_work_ids": [row.get("work_id") for row in blocked],
        "followup_work_ids": [row.get("work_id") for row in followups],
        "source": "research_work_queue.objective_aggregation",
    }


def build_project_portfolio(queue=None) -> dict[str, Any]:
    queue = queue or default_queue()
    rows = queue.load().get("items", [])
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        objective_id = str(row.get("objective_id") or "").strip()
        if objective_id:
            grouped[objective_id].append(row)
    projects = []
    for objective_id, children in grouped.items():
        if not any(not _ignored_for_portfolio(row) for row in children):
            continue
        projects.append(aggregate_project(objective_id, children))
    projects.sort(key=lambda row: (int(row.get("project_priority", 50)), str(row.get("oldest_active_at") or "9999"), row["objective_id"]))
    counts = Counter(row["status"] for row in projects)
    return {
        "project_count": len(projects),
        "status_counts": dict(counts),
        "projects": projects,
        "highest_priority_projects": projects[:5],
        "oldest_active_project": next((row for row in projects if row.get("oldest_active_at")), None),
        "source": "data/runtime/research_work_queue.json",
    }
