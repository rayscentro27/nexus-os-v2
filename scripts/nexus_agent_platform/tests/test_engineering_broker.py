from types import SimpleNamespace

from nexus_agent_platform.governed import engineering_broker as broker


def _worker(worker_id, state, adapter=True):
    return SimpleNamespace(
        worker_id=worker_id, installed=True, available=state == "AVAILABLE",
        _execute_fn=(lambda task: {}) if adapter else None,
        supports_worktrees=True, supports_repo_edit=True, supports_tests=True,
        capabilities=["repo_edit", "tests", "worktrees"],
        availability_reason=state.lower(),
        health_check=lambda: {"installed": True, "classification": state, "reason": state.lower()},
    )


def test_codex_busy_handoffs_to_opencode(monkeypatch, tmp_path):
    workers = [_worker("codex", "BUSY"), _worker("opencode", "AVAILABLE"), _worker("mimo", "INSTALLED_UNPROVEN", False)]
    monkeypatch.setattr(broker, "build_coding_worker_registry", lambda: workers)
    monkeypatch.setattr(broker, "POOL_PATH", tmp_path / "pool.json")
    monkeypatch.setattr(broker, "LEASE_PATH", tmp_path / "lease.json")
    monkeypatch.setattr(broker, "HANDOFF_PATH", tmp_path / "handoffs.jsonl")
    monkeypatch.setattr(broker, "run_builder_task", lambda task, selected, max_retries=0: {"status": "pass", "worker_id": selected[0].worker_id, "worker_report": {}})
    task = SimpleNamespace(metadata={"source_commit": "abc"})
    result = broker.run_voice_task(task=task, repair_id="VOICE-001", work_order_id="wo-1", run_id="run-1", engineering_run_id="eng-1", previous_worker="codex")
    assert result["worker"] == "opencode"
    assert result["_execution_status"] == "PATCH_READY"
    assert "CODEX_BUSY" in (tmp_path / "handoffs.jsonl").read_text()


def test_all_workers_unavailable_is_retryable(monkeypatch, tmp_path):
    workers = [_worker("codex", "BUSY"), _worker("opencode", "AUTH_BLOCKED"), _worker("mimo", "INSTALLED_UNPROVEN", False)]
    monkeypatch.setattr(broker, "build_coding_worker_registry", lambda: workers)
    monkeypatch.setattr(broker, "POOL_PATH", tmp_path / "pool.json")
    result = broker.run_voice_task(task=SimpleNamespace(metadata={}), repair_id="VOICE-001", work_order_id="wo-1", run_id="run-1", engineering_run_id="eng-1")
    assert result["_execution_status"] == "WAITING_WORKER"
    assert result["state"] == "WAITING_WORKER"
    assert result["failure"] == "NO_CERTIFIED_WORKER_AVAILABLE"


def test_lease_is_single_owner(monkeypatch, tmp_path):
    monkeypatch.setattr(broker, "LEASE_PATH", tmp_path / "lease.json")
    broker.acquire_lease(repair_id="VOICE-001", work_order_id="wo-1", run_id="run-1", worker="opencode", engineering_run_id="eng-1")
    try:
        broker.acquire_lease(repair_id="EMAIL-001", work_order_id="wo-2", run_id="run-1", worker="opencode", engineering_run_id="eng-2")
    except RuntimeError as exc:
        assert "another repair" in str(exc)
    else:
        raise AssertionError("second repair acquired the active worker lease")
