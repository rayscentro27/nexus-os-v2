from __future__ import annotations

import json

from nexus_agent_platform.research_work_queue import ResearchWorkQueue
from nexus_agent_platform import research_continuation as rc


def _goal():
    return {
        "goal_id": "goal.test.revenue",
        "title": "Bounded revenue planning",
        "description": "Reduce uncertainty around a legitimate repeatable revenue path.",
        "status": "ACTIVE",
        "priority": "P2",
        "success_condition": ["evidence-backed path"],
    }


def test_empty_queue_generates_goal_objective_and_persists_lineage(tmp_path, monkeypatch):
    queue = ResearchWorkQueue(tmp_path / "queue.json")
    monkeypatch.setattr(rc, "CHARTER_PATH", tmp_path / "charter.json")
    monkeypatch.setattr(rc, "GENERATED_PATH", tmp_path / "generated.jsonl")
    monkeypatch.setattr(rc, "read_company_goals", lambda: [_goal()])
    monkeypatch.setattr(rc, "_model_plan", lambda *args, **kwargs: ([], {"planner_mode": "test"}))

    result = rc.continue_when_empty(queue=queue)
    assert result["trigger"] == "empty_queue_goal_continuation"
    assert len(result["generated"]) == 1
    item = queue.load()["items"][0]
    assert item["parent_goal_id"] == "goal.test.revenue"
    assert item["work_class"] == "ASSIGNED"
    assert item["status"] == "QUEUED"
    assert item["dedup_key"]


def test_same_goal_question_is_deduplicated(tmp_path, monkeypatch):
    queue = ResearchWorkQueue(tmp_path / "queue.json")
    monkeypatch.setattr(rc, "CHARTER_PATH", tmp_path / "charter.json")
    monkeypatch.setattr(rc, "GENERATED_PATH", tmp_path / "generated.jsonl")
    monkeypatch.setattr(rc, "read_company_goals", lambda: [_goal()])
    candidate = {"question": "What customer need is strongest?", "why_it_matters": "demand", "unknown_to_resolve": "demand", "required_evidence": ["source"], "likely_capabilities": ["WEB_ACQUISITION"], "priority": 20, "stop_condition": "one package"}
    monkeypatch.setattr(rc, "_model_plan", lambda *args, **kwargs: ([candidate], {"planner_mode": "model", "model": "test"}))

    first = rc.generate_objectives(queue=queue, goal=_goal(), count=1)
    second = rc.generate_objectives(queue=queue, goal=_goal(), count=1)
    assert len(first["generated"]) == 1
    assert second["status"] == "DEDUPLICATED"
    assert len(queue.load()["items"]) == 1


def test_continuation_snapshot_exposes_goal_and_charter(tmp_path, monkeypatch):
    queue = ResearchWorkQueue(tmp_path / "queue.json")
    monkeypatch.setattr(rc, "CHARTER_PATH", tmp_path / "charter.json")
    monkeypatch.setattr(rc, "GENERATED_PATH", tmp_path / "generated.jsonl")
    monkeypatch.setattr(rc, "read_company_goals", lambda: [_goal()])
    snapshot = rc.continuation_snapshot(queue)
    assert snapshot["status"] == "READY"
    assert snapshot["active_goal_count"] == 1
    assert snapshot["empty_queue_rule"].startswith("QUEUE EMPTY")
