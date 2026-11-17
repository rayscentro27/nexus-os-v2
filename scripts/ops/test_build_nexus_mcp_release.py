from pathlib import Path

import pytest

from build_nexus_mcp_release import (
    bind_durable_dispatcher_to_release,
    freeze,
    merge_dispatcher_allowed_sources,
    runtime_files_for_source,
    seed_files,
    static_seed_files,
    validate_executable_path_closure,
    validate_runtime_match,
    worker_executable_paths,
)


ROOT = Path(__file__).resolve().parents[2]
WORKER = Path("scripts/nexus_agent_platform/job_worker_once.py")


def test_durable_advisor_worker_is_in_release_runtime_closure():
    files = runtime_files_for_source(ROOT)
    assert Path("scripts/opportunities/engine.py") in files
    assert Path("scripts/opportunities/source_adapters/openaffiliate.py") in files
    assert not any("scripts/opportunities/tests" in path.as_posix() for path in files)
    assert WORKER in files
    assert Path("scripts/nexus_agent_platform/dispatcher_once.py") in files
    assert Path("scripts/ops/run_with_canonical_runtime_env.sh") in files
    assert Path("scripts/ops/nexus_runtime_env.py") in files
    assert Path("scripts/nova/research_room_dispatch.py") in files
    assert Path("scripts/nexus_agent_platform/research_room/business_opportunity_proof.py") in files
    assert Path("scripts/nexus_agent_platform/creative/performance_intelligence.py") in files
    assert Path("scripts/nexus_agent_platform/creative/avatar_registry.py") in files
    assert Path("scripts/research/run_dispatched_research_job.py") in files
    assert worker_executable_paths(ROOT) <= files


def test_missing_intake_runner_fails_executable_path_validation(tmp_path):
    files = runtime_files_for_source(ROOT)
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    assert "scripts/research/run_dispatched_research_job.py" in (ROOT / WORKER).read_text(encoding="utf-8")
    with pytest.raises(RuntimeError, match="EXECUTABLE_PATH_MISSING_FROM_RELEASE"):
        validate_executable_path_closure(ROOT, candidate, files)


def test_release_seed_excludes_mutable_and_unrelated_content(tmp_path):
    base = tmp_path / "base"
    for relative in (
        "configs/research_safety_policy.json",
        "configs/systems_notebooks/diagnostic.ipynb",
        "config/remote_capability_memory.json",
        "config/hermes/nova-profile/config.yaml",
        "config/hermes/nova-profile/memories/MEMORY.md",
        "data/first_3_testers_seed_template.json",
        "data/runtime/state.json",
        "reports/certification/old.json",
        "scripts/nexus_mcp/http_server.py",
        "scripts/ops/nexus_mcp_gateway.sh",
    ):
        path = base / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("seed")
    selected = seed_files(base)
    assert Path("scripts/ops/nexus_mcp_gateway.sh") in selected
    assert Path("configs/research_safety_policy.json") in selected
    assert Path("config/hermes/nova-profile/config.yaml") not in selected
    assert Path("data/first_3_testers_seed_template.json") in selected
    assert not any("runtime" in path.parts or "reports" in path.parts for path in selected)
    assert Path("config/remote_capability_memory.json") not in selected
    assert Path("config/hermes/nova-profile/memories/MEMORY.md") not in selected
    assert Path("configs/systems_notebooks/diagnostic.ipynb") not in selected


def test_base_seed_does_not_overwrite_canonical_runtime_files(tmp_path):
    base = tmp_path / "base"
    wrapper = base / "scripts/ops/run_with_canonical_runtime_env.sh"
    wrapper.parent.mkdir(parents=True)
    wrapper.write_text("stale base wrapper")
    selected = static_seed_files(base, {Path("scripts/ops/run_with_canonical_runtime_env.sh")})
    assert Path("scripts/ops/run_with_canonical_runtime_env.sh") not in selected
    assert Path("scripts/nexus_mcp/http_server.py") not in selected


def test_freeze_only_changes_candidate_descendants(tmp_path):
    release = tmp_path / "candidate"
    file_path = release / "scripts" / "entry.py"
    file_path.parent.mkdir(parents=True)
    (release / "reports").mkdir()
    file_path.write_text("pass\n")
    parent_mode = tmp_path.stat().st_mode
    freeze(release, [file_path])
    assert release.stat().st_mode & 0o777 == 0o555
    assert file_path.parent.stat().st_mode & 0o777 == 0o555
    assert (release / "reports").stat().st_mode & 0o777 == 0o555
    assert tmp_path.stat().st_mode == parent_mode


def test_canonical_worker_mismatch_fails_release_validation(tmp_path):
    source = tmp_path / "source"
    release = tmp_path / "release"
    worker = source / WORKER
    worker.parent.mkdir(parents=True)
    worker.write_text("canonical worker")
    packaged = release / WORKER
    packaged.parent.mkdir(parents=True)
    packaged.write_text("stale packaged worker")

    with pytest.raises(RuntimeError, match="job_worker_once.py"):
        validate_runtime_match(source, release, {WORKER})


def test_dispatcher_and_worker_bind_to_one_release_without_r4(tmp_path):
    import plistlib
    source = ROOT / "launchd/com.nexus.durable-dispatcher.plist"
    release = tmp_path / "candidate"
    plist_path = release / "launchd/com.nexus.durable-dispatcher.plist"
    plist_path.parent.mkdir(parents=True)
    plist_path.write_bytes(source.read_bytes())
    target = Path.home() / ".nexus/releases/nexus-capability-actions-fixture-r99"
    bind_durable_dispatcher_to_release(release, target, ROOT / "data")
    payload = plistlib.loads(plist_path.read_bytes())
    joined = " ".join(payload["ProgramArguments"])
    assert str(target) in joined
    assert str(target) in payload["WorkingDirectory"]
    assert str(ROOT / "data") == payload["EnvironmentVariables"]["NEXUS_RESEARCH_STATE_ROOT"]
    assert "nexus-research-runtime-isolated-closure-20261020-r4" not in joined
    assert "RESEARCH_ROOM_ADVISOR" in payload["EnvironmentVariables"]["NEXUS_DISPATCH_ALLOWED_JOB_SOURCES"]


def test_canonical_dispatcher_sources_merge_without_dropping_seed_sources(tmp_path):
    import plistlib
    release, source = tmp_path / "release", tmp_path / "source"
    seed_path = release / "launchd/com.nexus.durable-dispatcher.plist"
    canonical_path = source / "launchd/com.nexus.durable-dispatcher.plist"
    seed_path.parent.mkdir(parents=True)
    canonical_path.parent.mkdir(parents=True)
    seed_path.write_bytes(plistlib.dumps({"EnvironmentVariables": {
        "NEXUS_DISPATCH_ALLOWED_JOB_SOURCES": "BASE_ONLY,NOVA_BOUNDED_CONTROL_ACTION"}}))
    canonical_path.write_bytes(plistlib.dumps({"EnvironmentVariables": {
        "NEXUS_DISPATCH_ALLOWED_JOB_SOURCES": "RESEARCH_ROOM_ADVISOR,CANONICAL_ONLY"}}))
    merged = merge_dispatcher_allowed_sources(release, source)
    assert merged == ["BASE_ONLY", "NOVA_BOUNDED_CONTROL_ACTION", "RESEARCH_ROOM_ADVISOR", "CANONICAL_ONLY"]
    packaged = plistlib.loads(seed_path.read_bytes())
    assert packaged["EnvironmentVariables"]["NEXUS_DISPATCH_ALLOWED_JOB_SOURCES"] == ",".join(merged)
