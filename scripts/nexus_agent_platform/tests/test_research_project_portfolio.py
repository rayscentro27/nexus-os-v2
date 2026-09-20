from __future__ import annotations

import json

from nexus_agent_platform.research_project_portfolio import aggregate_project, build_project_portfolio
from nexus_agent_platform.research_work_queue import ResearchWorkQueue


def row(work_id, objective_id, status, *, required=True, alpha=False, department=None, priority=10):
    return {
        "work_id": work_id,
        "objective_id": objective_id,
        "status": status,
        "required_work": required,
        "alpha_followup_required": alpha,
        "department_target": department,
        "priority": priority,
        "created_at": "2026-09-20T10:00:00+00:00",
    }


def test_project_does_not_complete_with_running_or_followup_child():
    project = aggregate_project("objective", [
        row("done", "objective", "COMPLETE"),
        row("running", "objective", "IN_PROGRESS"),
    ])
    assert project["status"] == "ACTIVE"

    project = aggregate_project("objective", [
        row("done", "objective", "COMPLETE"),
        row("followup", "objective", "QUEUED", alpha=True),
    ])
    assert project["status"] == "NEEDS_MORE_RESEARCH"


def test_optional_blocker_does_not_block_project():
    project = aggregate_project("objective", [
        row("done", "objective", "COMPLETE"),
        row("monitor", "objective", "BLOCKED_EXTERNAL", required=False),
    ])
    assert project["status"] == "COMPLETE"
    assert project["optional_work_remaining"] == 0


def test_archived_portfolio_rows_do_not_keep_project_active():
    project = aggregate_project("objective", [{
        "work_id": "old",
        "objective_id": "objective",
        "status": "PARKED",
        "blocker_type": "PORTFOLIO_TEST_WINDOW_CLOSED",
        "work_class": "ASSIGNED",
    }])
    assert project["status"] == "NOT_STARTED"
    assert project["child_work_count"] == 0
    assert project["ignored_historical_work_count"] == 1


def test_active_replacement_prevents_premature_completion():
    project = aggregate_project("objective", [
        row("done", "objective", "COMPLETE"),
        row("replacement", "objective", "QUEUED"),
    ])
    assert project["status"] == "ACTIVE"
    assert project["required_work_remaining"] == 1


def test_blocked_required_child_is_not_hidden_by_optional_completion():
    project = aggregate_project("objective", [
        row("blocked", "objective", "BLOCKED_EXTERNAL"),
        row("optional", "objective", "COMPLETE", required=False),
    ])
    assert project["status"] == "BLOCKED"


def test_department_wait_and_required_blocker_are_distinct():
    waiting = aggregate_project("objective", [row("mkt", "objective", "WAITING", department="MARKETING")])
    assert waiting["status"] == "WAITING_FOR_DEPARTMENT"
    blocked = aggregate_project("objective", [row("blocked", "objective", "BLOCKED_EXTERNAL")])
    assert blocked["status"] == "BLOCKED"


def test_portfolio_projection_groups_children(tmp_path):
    queue = ResearchWorkQueue(tmp_path / "queue.json")
    queue.enqueue(**row("a1", "a", "COMPLETE"))
    queue.enqueue(**row("a2", "a", "QUEUED", alpha=True))
    queue.enqueue(**row("b1", "b", "COMPLETE"))
    projection = build_project_portfolio(queue)
    assert projection["project_count"] == 2
    by_id = {item["objective_id"]: item for item in projection["projects"]}
    assert by_id["a"]["status"] == "NEEDS_MORE_RESEARCH"
    assert by_id["a"]["required_work_remaining"] == 1
    assert by_id["b"]["status"] == "COMPLETE"


def test_project_status_contract_covers_ten_shapes():
    cases = [
        ([row("w", "o", "QUEUED")], "ACTIVE"),
        ([row("w", "o", "WAITING")], "WAITING"),
        ([row("w", "o", "IN_PROGRESS")], "ACTIVE"),
        ([row("w", "o", "COMPLETE")], "COMPLETE"),
        ([row("w", "o", "BLOCKED_EXTERNAL")], "BLOCKED"),
        ([row("w", "o", "COMPLETE"), row("f", "o", "QUEUED", alpha=True)], "NEEDS_MORE_RESEARCH"),
        ([row("w", "o", "COMPLETE"), row("d", "o", "WAITING", department="MARKETING")], "WAITING_FOR_DEPARTMENT"),
        ([row("w", "o", "COMPLETE"), row("m", "o", "BLOCKED_EXTERNAL", required=False)], "COMPLETE"),
        ([row("w", "o", "COMPLETE"), row("r", "o", "QUEUED")], "ACTIVE"),
        ([row("w", "o", "COMPLETE"), row("s", "o", "SUPERSEDED")], "COMPLETE"),
    ]
    assert sum(aggregate_project("o", children)["status"] == expected for children, expected in cases) == 10
