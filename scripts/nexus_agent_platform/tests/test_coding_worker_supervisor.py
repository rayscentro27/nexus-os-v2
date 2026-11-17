import json

from nexus_agent_platform.coding_worker_supervisor import (
    CodingTask,
    OpenCodeExecuteAdapter,
    classify_failure,
    persist_campaign,
    persist_handoff,
    run_failover_canary,
    select_worker,
)


def test_opencode_adapter_executes_in_bounded_worktree_and_verifies_untracked_artifact(tmp_path, monkeypatch):
    import nexus_agent_platform.coding_worker_supervisor as supervisor
    import nexus_agent_platform.durable_objective_control as objective_control
    monkeypatch.setattr(objective_control, "ACTIVE_CAMPAIGN_PATH", tmp_path / "no-active-campaign.json")

    runner = tmp_path / "opencode"
    runner.write_text("#!/bin/sh\nmkdir -p reports/runtime\nprintf 'bounded-result\\n' > reports/runtime/adapter_canary.txt\n", encoding="utf-8")
    runner.chmod(0o755)
    task = CodingTask("adapter", "adapter", "create canary", ("reports/runtime/",), ("src/", "data/"), ("artifact exists",),
                      supervisor.subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=supervisor.ROOT, text=True).strip())
    result = OpenCodeExecuteAdapter().execute(task, runner=str(runner), timeout=10)
    assert result["status"] == "PASS"
    assert result["independent_verification"] is True
    assert result["files_changed"] == ["reports/runtime/adapter_canary.txt"]
    assert result["violations"] == []


def test_opencode_adapter_runs_new_python_file_inside_allowed_temp_workspace(tmp_path, monkeypatch):
    import nexus_agent_platform.coding_worker_supervisor as supervisor
    import nexus_agent_platform.durable_objective_control as objective_control
    monkeypatch.setattr(objective_control, "ACTIVE_CAMPAIGN_PATH", tmp_path / "no-active-campaign.json")
    runner = tmp_path / "opencode"
    runner.write_text("#!/bin/sh\nmkdir -p tmp/nova_coding_jobs/test-job\nprintf 'print(\\\"Nova OpenCode control test passed\\\")\\n' > tmp/nova_coding_jobs/test-job/nova_opencode_test.py\n", encoding="utf-8")
    runner.chmod(0o755)
    checkpoint = supervisor.subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=supervisor.ROOT, text=True).strip()
    task = CodingTask("test-job", "test-job", "create and run a simple test", ("tmp/nova_coding_jobs/test-job/",),
        ("scripts/", "services/", "configs/", "data/", "src/"),
        ("create requested Python file", "execute Python file once"), checkpoint)
    result = OpenCodeExecuteAdapter().execute(task, runner=str(runner), timeout=10)
    assert result["status"] == "PASS"
    assert result["execution"]["returncode"] == 0
    assert result["execution"]["stdout"].strip() == "Nova OpenCode control test passed"


def test_opencode_adapter_supports_clean_release_root_with_empty_task_workspace(tmp_path, monkeypatch):
    import nexus_agent_platform.coding_worker_supervisor as supervisor
    import nexus_agent_platform.durable_objective_control as objective_control
    monkeypatch.setattr(objective_control, "ACTIVE_CAMPAIGN_PATH", tmp_path / "no-active-campaign.json")
    # Production clean releases are not Git checkouts. The allowed tmp/ path
    # may contain only directories before the coding agent creates its file.
    release_root = tmp_path / "clean-release"
    release_root.mkdir()
    monkeypatch.setattr(supervisor, "ROOT", release_root)
    runner = tmp_path / "opencode"
    runner.write_text(
        "#!/bin/sh\nmkdir -p tmp/nova_coding_jobs/test-job\n"
        "printf 'print(\\\"Nova OpenCode control test passed\\\")\\n' "
        "> tmp/nova_coding_jobs/test-job/nova_opencode_test.py\n", encoding="utf-8")
    runner.chmod(0o755)
    task = CodingTask("test-job", "test-job", "create and run a simple test",
        ("tmp/nova_coding_jobs/test-job/",), ("scripts/", "services/", "configs/", "data/", "src/"),
        ("create requested Python file", "execute Python file once"), "release-hash")
    result = OpenCodeExecuteAdapter().execute(task, runner=str(runner), timeout=10)
    assert result["status"] == "PASS"
    assert result["execution"]["returncode"] == 0
    assert result["execution"]["stdout"].strip() == "Nova OpenCode control test passed"


def test_opencode_provider_failure_is_not_mislabeled_as_python_execution_failure(tmp_path, monkeypatch):
    import nexus_agent_platform.coding_worker_supervisor as supervisor
    import nexus_agent_platform.durable_objective_control as objective_control
    monkeypatch.setattr(objective_control, "ACTIVE_CAMPAIGN_PATH", tmp_path / "no-active-campaign.json")
    runner = tmp_path / "opencode"
    runner.write_text("#!/bin/sh\nprintf 'provider unavailable\n'\nexit 1\n", encoding="utf-8")
    runner.chmod(0o755)
    checkpoint = supervisor.subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=supervisor.ROOT, text=True).strip()
    task = CodingTask("provider-fail", "provider-fail", "create and run a test",
        ("tmp/nova_coding_jobs/provider-fail/",), ("scripts/", "services/", "configs/", "data/", "src/"),
        ("create requested Python file", "execute Python file once"), checkpoint)
    result = OpenCodeExecuteAdapter().execute(task, runner=str(runner), timeout=10)
    assert result["status"] == "FAIL"
    assert result["failure_class"] == "EXECUTION_FAILED"
    assert "provider unavailable" in result["stdout"]


def test_opencode_uses_disposable_data_home_and_copies_only_auth_file(tmp_path, monkeypatch):
    import nexus_agent_platform.coding_worker_supervisor as supervisor
    import nexus_agent_platform.durable_objective_control as objective_control
    monkeypatch.setattr(objective_control, "ACTIVE_CAMPAIGN_PATH", tmp_path / "no-active-campaign.json")
    monkeypatch.setattr(supervisor.Path, "home", classmethod(lambda cls: tmp_path / "owner-home"))
    auth = tmp_path / "owner-home/.local/share/opencode/auth.json"
    auth.parent.mkdir(parents=True)
    auth.write_text('{"provider":"fixture"}', encoding="utf-8")
    runner = tmp_path / "opencode"
    runner.write_text(
        "#!/bin/sh\ntest -f \"$XDG_DATA_HOME/opencode/auth.json\" || exit 8\n"
        "mkdir -p tmp/nova_coding_jobs/auth-test\n"
        "printf 'print(\\\"isolated auth state ok\\\")\\n' > tmp/nova_coding_jobs/auth-test/result.py\n",
        encoding="utf-8")
    runner.chmod(0o755)
    checkpoint = supervisor.subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=supervisor.ROOT, text=True).strip()
    task = CodingTask("auth-test", "auth-test", "create and run a test",
        ("tmp/nova_coding_jobs/auth-test/",), ("scripts/", "services/", "configs/", "data/", "src/"),
        ("create requested Python file", "execute Python file once"), checkpoint)
    result = OpenCodeExecuteAdapter().execute(task, runner=str(runner), timeout=10)
    assert result["status"] == "PASS"
    assert result["execution"]["stdout"].strip() == "isolated auth state ok"


def test_rate_limit_requires_explicit_evidence():
    assert classify_failure("HTTP 429 quota exceeded") == "RATE_LIMITED"
    assert classify_failure("temporary provider error", 1) == "EXECUTION_FAILED"


def test_opencode_runner_discovery_includes_service_install_paths(monkeypatch):
    import nexus_agent_platform.coding_worker_supervisor as supervisor
    seen = {}
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.delenv("NEXUS_OPENCODE_BIN", raising=False)
    monkeypatch.setattr(supervisor.shutil, "which", lambda name, path=None: seen.setdefault("path", path) and "/usr/local/bin/opencode")
    assert supervisor._resolve_opencode_runner() == "/usr/local/bin/opencode"
    assert "/usr/local/bin" in seen["path"]


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
