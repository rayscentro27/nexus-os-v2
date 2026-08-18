from __future__ import annotations

import json
from pathlib import Path

import pytest

from nexus_agent_platform.builders.runtime import (
    BuildTaskSpec,
    CodingWorker,
    append_builder_ledger,
    build_coding_worker_registry,
    normalize_build_spec,
    run_builder_task,
    select_coding_worker,
    _combine_verification,
    _verify_protected_paths,
)
from nexus_agent_platform.creative.lab import build_creative_lab_report


def _task() -> BuildTaskSpec:
    return normalize_build_spec(build_creative_lab_report()["build_spec"])


def _worker(worker_id: str, *, available: bool, browser: bool = False, tests: bool = True, repo_edit: bool = True, cost_class: str = "ZERO_MODEL_COST", execute_fn=None) -> CodingWorker:
    return CodingWorker(
        worker_id=worker_id,
        worker_type="test",
        display_name=worker_id.title(),
        available=available,
        capabilities=["repo_edit"] if repo_edit else [],
        cost_class=cost_class,
        supports_repo_edit=repo_edit,
        supports_tests=tests,
        supports_browser=browser,
        supports_images=False,
        supports_worktrees=True,
        supports_resume=False,
        supports_structured_output=True,
        availability_reason="test",
        installed=available,
        execute_fn=execute_fn,
    )


def test_unavailable_worker_is_skipped():
    task = _task()
    workers = build_coding_worker_registry()
    selected = select_coding_worker(task, workers)
    assert selected.worker_id in {"local_python", "codex", "opencode", "mimo"}
    assert all(worker.available == (worker.health_check().get("classification") == "AVAILABLE") for worker in workers if worker.worker_type == "cli")
    assert all(worker.health_check().get("classification") != "AUTH_BLOCKED" or "authentication" in worker.availability_reason.lower() for worker in workers)


def test_rate_limited_worker_falls_back_to_another_compatible_worker():
    task = _task()
    unavailable = _worker("codex", available=False)
    fallback = _worker("local_python", available=True, execute_fn=lambda t: {"status": "success", "artifact_refs": [], "files_changed": [], "tests_run": [], "tests_passed": 0, "tests_failed": 0, "visual_check": {"required": False, "verified": False, "status": "not_required"}, "protected_path_violation": False, "cost_provenance": {"tier": "ZERO_MODEL_COST", "provider": "local_python", "estimated_cost_usd": 0.0}})
    selected = select_coding_worker(task, [unavailable, fallback])
    assert selected.worker_id == "local_python"


def test_protected_paths_enforced():
    task = _task()
    result = {"files_changed": ["src/client-v2/pages/Unsafe.tsx"], "artifact_refs": [], "protected_path_violation": False}
    assert _verify_protected_paths(task, result)["status"] == "fail"


def test_structured_spec_used_instead_of_conversation_replay():
    raw = build_creative_lab_report()["build_spec"]
    raw["conversation_history"] = ["too much"]
    raw["full_history"] = ["too much"]
    task = normalize_build_spec(raw)
    rendered = task.to_dict()
    assert "conversation_history" not in rendered
    assert "full_history" not in rendered
    assert task.approval_state == "approved"
    assert task.protected_paths


def test_deterministic_worker_selection_works():
    task = _task()
    workers = [
        _worker("worker_b", available=True, cost_class="AI_TIER_2"),
        _worker("worker_a", available=True, cost_class="ZERO_MODEL_COST"),
    ]
    first = select_coding_worker(task, workers)
    second = select_coding_worker(task, workers)
    assert first.worker_id == second.worker_id == "worker_a"


def test_retry_count_bounded_and_failure_delta_only(monkeypatch, tmp_path):
    from nexus_agent_platform.builders import runtime as builder_runtime

    ledger = tmp_path / "ledger.jsonl"
    monkeypatch.setattr(builder_runtime, "LEDGER_PATH", ledger)

    seen_deltas = []

    def execute_fn(task):
        seen_deltas.append(dict(task.previous_failure_delta))
        if not task.previous_failure_delta:
            artifact = tmp_path / "artifact.txt"
            artifact.write_text("ok", encoding="utf-8")
            return {
                "status": "success",
                "artifact_refs": [str(artifact)],
                "files_changed": [str(artifact)],
                "tests_run": ["first"],
                "tests_passed": 0,
                "tests_failed": 1,
                "visual_check": {"required": False, "verified": False, "status": "not_required"},
                "protected_path_violation": False,
                "cost_provenance": {"tier": "ZERO_MODEL_COST", "provider": "local_python", "estimated_cost_usd": 0.0},
            }
        artifact = tmp_path / "artifact_2.txt"
        artifact.write_text("ok", encoding="utf-8")
        return {
            "status": "success",
            "artifact_refs": [str(artifact)],
            "files_changed": [str(artifact)],
            "tests_run": ["retry"],
            "tests_passed": 1,
            "tests_failed": 0,
            "visual_check": {"required": False, "verified": False, "status": "not_required"},
            "protected_path_violation": False,
            "cost_provenance": {"tier": "ZERO_MODEL_COST", "provider": "local_python", "estimated_cost_usd": 0.0},
        }

    task = normalize_build_spec(build_creative_lab_report()["build_spec"])
    task = BuildTaskSpec(**{**task.to_dict(), "max_retries": 1})
    worker = _worker("local_python", available=True, execute_fn=execute_fn)
    result = run_builder_task(task, [worker], max_retries=1)

    assert result["status"] == "pass"
    assert result["result"]["retry_count"] == 1
    assert seen_deltas[0] == {}
    assert seen_deltas[1] == {"tests_failed": 1, "tests_run": ["first"]}
    assert ledger.exists()


def test_worker_self_report_cannot_bypass_verification():
    task = _task()
    worker = _worker(
        "local_python",
        available=True,
        execute_fn=lambda t: {
            "status": "success",
            "artifact_refs": ["/tmp/does-not-exist.txt"],
            "files_changed": ["/tmp/does-not-exist.txt"],
            "tests_run": [],
            "tests_passed": 0,
            "tests_failed": 0,
            "visual_check": {"required": False, "verified": False, "status": "not_required"},
            "protected_path_violation": False,
            "cost_provenance": {"tier": "ZERO_MODEL_COST", "provider": "local_python", "estimated_cost_usd": 0.0},
            "self_report": "done",
        },
    )
    verification = worker.verify_result(task, worker.collect_result(worker.execute(task)))
    assert verification["status"] == "fail"


def test_failed_tests_produce_failed_or_retry(tmp_path):
    task = _task()
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("ok", encoding="utf-8")
    worker = _worker(
        "local_python",
        available=True,
        execute_fn=lambda t: {
            "status": "success",
            "artifact_refs": [str(artifact)],
            "files_changed": [str(artifact)],
            "tests_run": ["lint"],
            "tests_passed": 0,
            "tests_failed": 1,
            "visual_check": {"required": False, "verified": False, "status": "not_required"},
            "protected_path_violation": False,
            "cost_provenance": {"tier": "ZERO_MODEL_COST", "provider": "local_python", "estimated_cost_usd": 0.0},
        },
    )
    verification = worker.verify_result(task, worker.collect_result(worker.execute(task)))
    assert verification["status"] == "retry"


def test_successful_verification_produces_pass(tmp_path):
    task = _task()
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("ok", encoding="utf-8")
    worker = _worker(
        "local_python",
        available=True,
        execute_fn=lambda t: {
            "status": "success",
            "artifact_refs": [str(artifact)],
            "files_changed": [str(artifact)],
            "tests_run": ["py_compile"],
            "tests_passed": 1,
            "tests_failed": 0,
            "visual_check": {"required": False, "verified": False, "status": "not_required"},
            "protected_path_violation": False,
            "cost_provenance": {"tier": "ZERO_MODEL_COST", "provider": "local_python", "estimated_cost_usd": 0.0},
        },
    )
    verification = worker.verify_result(task, worker.collect_result(worker.execute(task)))
    assert verification["status"] == "pass"


def test_execution_ledger_populated(monkeypatch, tmp_path):
    from nexus_agent_platform.builders import runtime as builder_runtime

    ledger = tmp_path / "ledger.jsonl"
    monkeypatch.setattr(builder_runtime, "LEDGER_PATH", ledger)
    result = builder_runtime.run_builder_pilot()
    assert result["ok"] is True
    lines = ledger.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["status"] == "pass"
    assert entry["protected_path_violation"] is False
    assert entry["worker_id"] == "local_python"


def test_frontend_task_cannot_pass_without_visual_verification_flag_when_required():
    task = _task()
    task = BuildTaskSpec(**{**task.to_dict(), "visual_requirements": True})
    worker = _worker(
        "browserless",
        available=True,
        browser=False,
        execute_fn=lambda t: {
            "status": "success",
            "artifact_refs": [],
            "files_changed": [],
            "tests_run": [],
            "tests_passed": 0,
            "tests_failed": 0,
            "visual_check": {"required": True, "verified": False, "status": "missing"},
            "protected_path_violation": False,
            "cost_provenance": {"tier": "ZERO_MODEL_COST", "provider": "local_python", "estimated_cost_usd": 0.0},
        },
    )
    verification = worker.verify_result(task, worker.collect_result(worker.execute(task)))
    assert verification["status"] == "fail"
