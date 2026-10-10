import json
from datetime import datetime, timezone

from nexus_agent_platform import executive_status as status_module
from nexus_agent_platform.executive_status import build_executive_status, executive_status_delta, executive_status_for_prompt, render_executive_status_answer
from nexus_agent_platform.nova_company_context import context_for_prompt


def test_executive_status_has_one_contract_and_all_departments():
    status = build_executive_status()

    assert status["schema_version"] == "nexus.executive-status.v1"
    assert set(status["departments"]) == {"research", "alpha", "clyde", "systems", "creative"}
    for department in status["departments"].values():
        assert {"status", "current_objective", "current_task", "last_useful_activity", "completed_recently", "failed_recently", "blockers", "human_gate", "next_action", "last_updated", "evidence_refs"} <= set(department)
    assert status["evidence_refs"]


def test_executive_status_prompt_is_structured_and_bounded():
    rendered = executive_status_for_prompt({"schema_version": "nexus.executive-status.v1", "departments": {}})
    value = json.loads(rendered)
    assert value["schema_version"] == "nexus.executive-status.v1"
    assert len(rendered) < 18001


def test_delta_reports_only_real_department_changes():
    before = {"generated_at": "t1", "departments": {"alpha": {"status": "STALE", "next_action": "Revalidate"}}}
    after = {"generated_at": "t2", "departments": {"alpha": {"status": "RUNNING", "next_action": "Evaluate"}}}
    delta = executive_status_delta(before, after)
    assert delta["changed"] is True
    assert delta["changed_departments"][0]["department"] == "alpha"
    assert delta["changed_departments"][0]["changes"]["status"]["after"] == "RUNNING"

    unchanged = executive_status_delta(after, {**after, "generated_at": "t3"})
    assert unchanged["changed"] is False
    assert unchanged["changed_departments"] == []


def test_next_actions_separate_nexus_work_from_ray_gates():
    status = build_executive_status()
    owners = {item["department"]: item["owner"] for item in status["next_actions"]}
    assert owners["research"] == "NEXUS"
    assert owners["clyde"] == "RAY"


def test_prompt_context_preserves_the_same_status_object():
    status = {"schema_version": "nexus.executive-status.v1", "generated_at": "t1", "departments": {"research": {"status": "QUEUED"}}}
    rendered = json.loads(context_for_prompt({"executive_status": status, "research_operational_state": {}}))
    assert rendered["executive_status"] == status


def test_required_executive_questions_enter_the_bounded_status_path(monkeypatch):
    from nexus_agent_platform.bridge import oracle_hermes_cli

    sentinel = '{"schema_version":"nexus.executive-status.v1","departments":{"research":{"status":"QUEUED"}}}'
    monkeypatch.setattr("nexus_agent_platform.executive_status.executive_status_for_prompt", lambda: sentinel)
    questions = (
        "What is Nexus doing right now?", "What happened recently?", "What needs me?",
        "What is Research doing?", "What is Alpha doing?", "What is Systems doing?",
        "What is Clyde waiting on?", "What is Creative waiting on?", "What happens next?",
    )
    for question in questions:
        assert sentinel in oracle_hermes_cli._bounded_executive_context(question)
    assert oracle_hermes_cli._bounded_executive_context("hello Nova") == ""


def test_prompt_preserves_queued_stale_running_and_ray_gate_states():
    status = {
        "schema_version": "nexus.executive-status.v1",
        "departments": {
            "research": {"status": "QUEUED", "next_action": "Wait for the next queue wake"},
            "alpha": {"status": "STALE", "next_action": "Revalidate Alpha"},
            "systems": {"status": "RUNNING", "next_action": "Continue bounded discovery"},
            "clyde": {"status": "WAITING_HUMAN", "human_gate": {"required": True}},
            "creative": {"status": "WAITING_HUMAN", "human_gate": {"required": True}},
        },
    }
    rendered = json.loads(executive_status_for_prompt(status))
    states = {name: value["status"] for name, value in rendered["departments"].items()}
    assert states == {"research": "QUEUED", "alpha": "STALE", "systems": "RUNNING", "clyde": "WAITING_HUMAN", "creative": "WAITING_HUMAN"}


def test_stale_next_wake_is_not_presented_as_future():
    now = datetime(2026, 9, 28, 12, tzinfo=timezone.utc)
    assert status_module._fresh_next_action("RUN_BOUNDED_WORK (next wake 2026-09-27T13:50:56+00:00)", now) == "Wait for the next deterministic execution slot."
    assert status_module._fresh_next_action("RUN_BOUNDED_WORK (next wake 2026-09-29T13:50:56+00:00)", now).startswith("RUN_BOUNDED_WORK")


def test_missing_department_sources_are_unknown_not_healthy(monkeypatch, tmp_path):
    empty_research = status_module._department(status="UNKNOWN", next_action="No current Research state")
    monkeypatch.setattr(status_module, "ROOT", tmp_path)
    monkeypatch.setattr(status_module, "_research_status", lambda now: (empty_research, [], [], []))
    status = build_executive_status(now=datetime(2026, 9, 28, tzinfo=timezone.utc))
    assert status["departments"]["alpha"]["status"] == "UNKNOWN"
    assert status["departments"]["systems"]["status"] == "UNKNOWN"
    assert status["departments"]["creative"]["status"] == "UNKNOWN"
    assert status["departments"]["clyde"]["status"] == "NO_CURRENT_WORK"


def test_rendered_answers_preserve_live_states_and_gate_ownership():
    status = {
        "overall_status": "BLOCKED",
        "departments": {
            "research": {"status": "QUEUED", "next_action": "Wait for queue wake", "current_task": "Research task"},
            "alpha": {"status": "STALE", "next_action": "Revalidate Alpha"},
            "systems": {"status": "RUNNING", "next_action": "Continue discovery"},
            "clyde": {"status": "WAITING_HUMAN", "next_action": "Review lender gate", "current_task": "Funding readiness"},
            "creative": {"status": "WAITING_HUMAN", "next_action": "Approve design", "current_task": "Admin command center"},
        },
        "human_gates": [{"department": "clyde"}, {"department": "creative"}],
        "next_actions": [
            {"department": "research", "owner": "NEXUS", "action": "Wait for queue wake"},
            {"department": "clyde", "owner": "RAY", "action": "Review lender gate"},
        ],
        "completed_since_last_brief": [], "failures": [],
    }
    answer = render_executive_status_answer("What is Nexus doing right now?", status)
    assert "Research: has work queued" in answer
    assert "Alpha: has not reported recent useful activity" in answer
    assert "Systems: is running" in answer
    gates = render_executive_status_answer("What needs me?", status)
    assert "Clyde" in gates and "Creative" in gates
    assert "Research" not in gates
    next_answer = render_executive_status_answer("What happens next?", status)
    assert "NEXUS: research" in next_answer and "RAY: clyde" in next_answer


def test_status_questions_use_local_canonical_snapshot_before_remote(monkeypatch):
    from nexus_agent_platform.bridge import oracle_hermes_cli
    monkeypatch.setattr(oracle_hermes_cli, "ORACLE_KEY", "/definitely/missing")
    result = oracle_hermes_cli.run_oracle_hermes("What is Nexus doing right now?", "status-canary")
    assert result.status == "SUCCEEDED"
    assert result.provider == "nexus"
    assert "Research:" in result.response
    assert "queued" in result.response
