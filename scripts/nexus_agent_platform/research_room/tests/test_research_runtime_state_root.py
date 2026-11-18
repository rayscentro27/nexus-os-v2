from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from nexus_agent_platform.runtime import paths


def _under(path: Path, root: Path) -> bool:
    return path.resolve().is_relative_to(root.resolve())


def test_research_runtime_state_defaults_outside_immutable_release(monkeypatch, tmp_path):
    release = tmp_path / "releases" / "r99"
    release.mkdir(parents=True)
    (release / "RELEASE_MANIFEST.sha256").write_text("immutable")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("NEXUS_RESEARCH_STATE_ROOT", raising=False)
    monkeypatch.setattr(paths, "get_nexus_repo_root", lambda: release)
    root = paths.nexus_research_state_root()
    assert root == tmp_path / ".nexus/state/research"
    assert not _under(root, release)


def test_explicit_research_state_root_is_release_independent(monkeypatch, tmp_path):
    release = tmp_path / "releases" / "r99"
    release.mkdir(parents=True)
    external = tmp_path / "stable" / "research"
    monkeypatch.setenv("NEXUS_RESEARCH_STATE_ROOT", str(external))
    monkeypatch.setattr(paths, "get_nexus_repo_root", lambda: release)
    assert paths.nexus_research_state_root() == external
    assert paths.nexus_research_state_path("runtime", "queue.json") == external / "runtime/queue.json"


def test_governed_research_records_resolve_under_external_root(monkeypatch, tmp_path):
    from nexus_agent_platform.governed import persistence
    external = tmp_path / "state"
    monkeypatch.setenv("NEXUS_RESEARCH_STATE_ROOT", str(external))
    monkeypatch.delenv("NEXUS_GOVERNED_DATA_DIR", raising=False)
    assert persistence.collection_path("research_runtime_states") == external / "governed/research_runtime_states.jsonl"


def test_advisor_attempt_payload_is_written_outside_release(monkeypatch, tmp_path):
    from nexus_agent_platform import durable_jobs
    from nexus_agent_platform.research_room import production_controller as controller
    release = tmp_path / "release"
    release.mkdir()
    external = tmp_path / "state"
    monkeypatch.setenv("NEXUS_RESEARCH_STATE_ROOT", str(external))
    case = {"case_id": "cert-case", "research_room_controller": {}}

    def save(_case_id, *, controller=None, **_kwargs):
        case["research_room_controller"] = controller
        return {"saved": True}

    class Store:
        def enqueue(self, _department, _job_type, **kwargs):
            return SimpleNamespace(job_id=kwargs["job_id"])

    monkeypatch.setattr(controller, "_load", lambda _identity: case)
    monkeypatch.setattr(controller, "_save_controller", save)
    monkeypatch.setattr(durable_jobs, "default_store", Store)
    result = controller.advisor_request("cert-case", "obj", "project", "parent", "analyze input")
    payload = external / "runtime/research_room_advisor" / f"{result['attempt_id']}.json"
    assert result["status"] == "queued"
    assert payload.is_file()
    assert not _under(payload, release)


def test_local_job_state_is_written_outside_release(monkeypatch, tmp_path):
    from nexus_agent_platform.durable_jobs import default_store
    release = tmp_path / "release"
    release.mkdir()
    external = tmp_path / "state"
    monkeypatch.setenv("NEXUS_RESEARCH_STATE_ROOT", str(external))
    monkeypatch.setenv("NEXUS_DURABLE_JOBS_LOCAL", "1")
    monkeypatch.delenv("NEXUS_DURABLE_JOBS_DB", raising=False)
    store = default_store()
    job = store.enqueue("RESEARCH", "RESEARCH_ROOM_ADVISOR", idempotency_key="outside-release")
    assert store.path == external / "runtime/nexus_durable_jobs.sqlite3"
    assert store.path.is_file() and store.get(job.job_id)
    assert not _under(store.path, release)


def test_source_attempt_uses_external_governed_case_store(monkeypatch, tmp_path):
    from nexus_agent_platform.governed import persistence
    external = tmp_path / "state"
    monkeypatch.setenv("NEXUS_RESEARCH_STATE_ROOT", str(external))
    monkeypatch.delenv("NEXUS_GOVERNED_DATA_DIR", raising=False)
    receipt = {"case_id": "case-cert", "attempt_id": "source-a", "result": "SEARCH_FAILED"}
    persistence.append_record("research_runtime_states", {"memory_kind": "RESEARCH_CASE",
        "case_id": "case-cert", "research_room_controller": {"source_attempts": [receipt]}})
    path = external / "governed/research_runtime_states.jsonl"
    assert path.is_file()
    assert "source-a" in path.read_text()


def test_certification_case_persistence_uses_external_state_root(monkeypatch, tmp_path):
    from research.proactive_research_memory import persist_state
    external = tmp_path / "cert-state"
    monkeypatch.setenv("NEXUS_RESEARCH_STATE_ROOT", str(external))
    monkeypatch.setenv("NEXUS_RESEARCH_CASE_LOCAL_ONLY", "1")
    persist_state({"memory_kind": "RESEARCH_CASE", "case_id": "isolated-cert-case",
        "status": "PROMISING"})
    path = external / "governed/research_runtime_states.jsonl"
    assert path.is_file() and "isolated-cert-case" in path.read_text()


def test_release_manifest_stays_valid_after_external_research_write(monkeypatch, tmp_path):
    from nexus_agent_platform.governed import persistence
    release = tmp_path / "release"
    release.mkdir()
    packaged = release / "scripts/runtime.py"
    packaged.parent.mkdir()
    packaged.write_text("immutable runtime")
    expected = hashlib.sha256(packaged.read_bytes()).hexdigest()
    manifest = release / "RELEASE_MANIFEST.sha256"
    manifest.write_text(f"{expected}  ./scripts/runtime.py\n")
    release.chmod(0o555)
    packaged.chmod(0o444)
    external = tmp_path / "state"
    monkeypatch.setenv("NEXUS_RESEARCH_STATE_ROOT", str(external))
    monkeypatch.setenv("NEXUS_RESEARCH_CASE_LOCAL_ONLY", "1")
    persistence.append_record("research_runtime_states", {"memory_kind": "RESEARCH_CASE",
        "case_id": "cert-case", "status": "PROMISING"})
    assert hashlib.sha256(packaged.read_bytes()).hexdigest() == expected
    assert (external / "governed/research_runtime_states.jsonl").exists()


def test_mcp_and_dispatcher_worker_are_packaged_from_one_release():
    from pathlib import Path
    from build_nexus_mcp_release import runtime_files_for_source
    source = Path(__file__).resolve().parents[4]
    files = runtime_files_for_source(source)
    assert Path("scripts/nexus_agent_platform/dispatcher_once.py") in files
    assert Path("scripts/nexus_agent_platform/job_worker_once.py") in files
    assert Path("scripts/ops/run_with_canonical_runtime_env.sh") in files


def test_dispatcher_service_binding_points_to_same_release_as_worker(tmp_path):
    from build_nexus_mcp_release import bind_durable_dispatcher_to_release
    release = tmp_path / "release"
    (release / "launchd").mkdir(parents=True)
    source = Path(__file__).resolve().parents[4] / "launchd/com.nexus.durable-dispatcher.plist"
    (release / "launchd/com.nexus.durable-dispatcher.plist").write_bytes(source.read_bytes())
    final = Path.home() / ".nexus/releases/nexus-capability-actions-test-r99"
    bind_durable_dispatcher_to_release(release, final, tmp_path / "stable-state")
    import plistlib
    plist = plistlib.loads((release / "launchd/com.nexus.durable-dispatcher.plist").read_bytes())
    args = plist["ProgramArguments"]
    assert args[0] == str(final / "scripts/ops/run_with_canonical_runtime_env.sh")
    assert args[2] == str(final / "scripts/nexus_agent_platform/dispatcher_once.py")
    assert plist["WorkingDirectory"] == str(final)
    assert "nexus-research-runtime-isolated-closure-20261020-r4" not in " ".join(args)


def test_external_runtime_state_survives_process_restart(monkeypatch, tmp_path):
    external = tmp_path / "state"
    monkeypatch.setenv("NEXUS_RESEARCH_STATE_ROOT", str(external))
    path = paths.nexus_research_state_path("certification/restart.json")
    path.parent.mkdir(parents=True)
    path.write_text('{"survives":true}')
    env = dict(os.environ)
    repo = Path(__file__).resolve().parents[4]
    env["PYTHONPATH"] = str(repo / "scripts")
    code = "from nexus_agent_platform.runtime.paths import nexus_research_state_path; print(nexus_research_state_path('certification/restart.json').read_text())"
    proc = subprocess.run([sys.executable, "-c", code], cwd=repo, env=env, text=True,
        capture_output=True, check=True)
    assert '"survives":true' in proc.stdout


def test_external_runtime_state_survives_simulated_release_change(monkeypatch, tmp_path):
    external = tmp_path / "stable-state"
    rel_a, rel_b = tmp_path / "r-a", tmp_path / "r-b"
    rel_a.mkdir(); rel_b.mkdir()
    monkeypatch.setenv("NEXUS_RESEARCH_STATE_ROOT", str(external))
    monkeypatch.setattr(paths, "get_nexus_repo_root", lambda: rel_a)
    saved = paths.nexus_research_state_path("certification/promotion.json")
    saved.parent.mkdir(parents=True); saved.write_text("survives")
    monkeypatch.setattr(paths, "get_nexus_repo_root", lambda: rel_b)
    assert paths.nexus_research_state_path("certification/promotion.json").read_text() == "survives"


def test_certification_namespace_isolated_from_production_state(monkeypatch, tmp_path):
    from nexus_agent_platform.governed import persistence
    production = tmp_path / "production-state"
    certification = tmp_path / "cert-state"
    monkeypatch.setenv("NEXUS_RESEARCH_STATE_ROOT", str(production))
    production_path = persistence.collection_path("research_runtime_states")
    monkeypatch.setenv("NEXUS_RESEARCH_STATE_ROOT", str(certification))
    certification_path = persistence.collection_path("research_runtime_states")
    persistence.append_record("research_runtime_states", {"memory_kind": "RESEARCH_CASE",
        "case_id": "cert-only"})
    assert production_path != certification_path
    assert not production_path.exists()
    assert certification_path.exists()


def test_release_directory_remains_read_only_during_advisor_request(monkeypatch, tmp_path):
    from nexus_agent_platform import durable_jobs
    from nexus_agent_platform.research_room import production_controller as controller
    release = tmp_path / "release"
    release.mkdir()
    marker = release / "manifested.txt"
    marker.write_text("frozen")
    digest = hashlib.sha256(marker.read_bytes()).hexdigest()
    marker.chmod(0o444); release.chmod(0o555)
    external = tmp_path / "state"
    monkeypatch.setenv("NEXUS_RESEARCH_STATE_ROOT", str(external))
    case = {"case_id": "readonly-case", "research_room_controller": {}}
    monkeypatch.setattr(controller, "_load", lambda _identity: case)
    monkeypatch.setattr(controller, "_save_controller", lambda _case, **_kwargs: {"saved": True})
    monkeypatch.setattr(durable_jobs, "default_store", lambda: SimpleNamespace(
        enqueue=lambda *_a, **kw: SimpleNamespace(job_id=kw["job_id"])))
    result = controller.advisor_request("readonly-case", "obj", "project", "parent", "read supplied text")
    assert result["status"] == "queued"
    assert hashlib.sha256(marker.read_bytes()).hexdigest() == digest


def test_worker_governance_and_egress_state_use_external_research_root(monkeypatch, tmp_path):
    import importlib
    external = tmp_path / "durable-state"
    monkeypatch.setenv("NEXUS_RESEARCH_STATE_ROOT", str(external))
    from nexus_agent_platform import resource_spend_governor, supabase_egress_guard
    importlib.reload(resource_spend_governor)
    importlib.reload(supabase_egress_guard)
    assert resource_spend_governor.DEFAULT_DB == external / "runtime/resource_spend_governor.sqlite3"
    assert supabase_egress_guard.JOB_EGRESS_DIR == external / "runtime/job_egress"


def test_research_checkpoints_needle_and_job_health_use_external_root(monkeypatch, tmp_path):
    import importlib
    external = tmp_path / "research-state"
    monkeypatch.setenv("NEXUS_RESEARCH_STATE_ROOT", str(external))
    from nexus_agent_platform import notebooklm_discovery, needle_research_workflow, job_health
    from nexus_agent_platform import research_ai_orchestrator, research_continuation
    from research import notebook_completion_contracts, notebook_playbook_runner
    for module in (notebooklm_discovery, needle_research_workflow, job_health,
                   research_ai_orchestrator, research_continuation,
                   notebook_completion_contracts, notebook_playbook_runner):
        importlib.reload(module)
    assert notebooklm_discovery._checkpoint_path("job-cert").is_relative_to(external)
    assert needle_research_workflow.PAYLOAD_ROOT.is_relative_to(external)
    assert job_health.nexus_research_state_path("runtime", "durable_job_health_latest.json").is_relative_to(external)
    assert research_ai_orchestrator.RECEIPT_ROOT.is_relative_to(external)
    assert research_continuation.GENERATED_PATH.is_relative_to(external)
    assert notebook_completion_contracts.CONTRACT_STATE_ROOT.is_relative_to(external)
    assert notebook_playbook_runner.RECEIPTS.is_relative_to(external)
