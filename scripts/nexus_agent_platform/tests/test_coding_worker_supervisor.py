import json

from nexus_agent_platform.coding_worker_supervisor import (
    CodingTask,
    classify_failure,
    persist_campaign,
    persist_handoff,
    run_failover_canary,
    select_worker,
)


def test_rate_limit_requires_explicit_evidence():
    assert classify_failure("HTTP 429 quota exceeded") == "RATE_LIMITED"
    assert classify_failure("temporary provider error", 1) == "EXECUTION_FAILED"


def test_failover_canary_persists_handoff_and_selects_local_when_opencode_unproven(tmp_path, monkeypatch):
    import nexus_agent_platform.coding_worker_supervisor as supervisor
    monkeypatch.setattr(supervisor, "STATE_PATH", tmp_path / "campaign.json")
    monkeypatch.setattr(supervisor, "HANDOFF_PATH", tmp_path / "handoff.json")
    result = run_failover_canary()
    assert result["status"] == "PASS"
    assert result["selected_worker"] == "local"
    assert result["independent_verification"] is True
    assert (tmp_path / "campaign.json").exists()
    assert (tmp_path / "handoff.json").exists()
    assert json.loads((tmp_path / "handoff.json").read_text())["failure_class"] == "RATE_LIMITED"


def test_incompatible_task_truthfully_blocks_without_ai_worker():
    task = CodingTask("x", "x", "x", ("src/",), ("data/",), ("browser",), "a" * 40)
    workers = {"codex": {"state": "RATE_LIMITED", "capabilities": ["repo_edit"]},
               "opencode": {"state": "UNAVAILABLE", "capabilities": ["repo_edit"]},
               "local": {"state": "AVAILABLE", "capabilities": ["deterministic"]}}
    assert select_worker(task, workers, unavailable=("codex",)) == "BLOCKED_WORKER_CAPACITY"


def test_handoff_contract_contains_required_lineage(tmp_path, monkeypatch):
    import nexus_agent_platform.coding_worker_supervisor as supervisor
    monkeypatch.setattr(supervisor, "HANDOFF_PATH", tmp_path / "handoff.json")
    task = CodingTask("t", "o", "bounded", ("reports/",), ("src/",), ("artifact",), "b" * 40)
    handoff = persist_handoff(task=task, previous_worker="codex", next_worker="opencode", reason="429", failure_class="RATE_LIMITED", failure_evidence="HTTP 429")
    assert handoff["starting_sha"] == "b" * 40
    assert handoff["allowed_paths"] == ["reports/"]
    assert handoff["next_worker"] == "opencode"
