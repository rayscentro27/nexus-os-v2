from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/systems"))

from change_target_resolver import post_change_check, resolve_target
from kaggle_artifact_packager import package_outputs
from kaggle_job_runner import validate_job
from secret_guard import redact_text


def test_change_target_resolver_accepts_registered_research_file_and_denies_historical_queue():
    manifest = {"change_target_registry": {"global_do_not_patch_paths": ["$REPO_ROOT/data/runtime/research_work_queue.json"], "components": {"research": {"authoritative_file_patterns": ["$REPO_ROOT/scripts/systems/*.py"], "do_not_patch_paths": []}}}}
    good = resolve_target(manifest, "research", "test target resolver", ["scripts/systems/secret_guard.py"])
    assert good["target_confirmation"] == "PASS"
    assert good["authority_check"] == "PASS"
    try:
        resolve_target(manifest, "research", "test legacy denial", ["data/runtime/research_work_queue.json"])
    except ValueError as exc:
        assert str(exc).startswith("OUT_OF_AUTHORITY_SCOPE")
    else:
        raise AssertionError("historical queue must be denied")


def test_post_change_check_reports_untracked_authorized_file_only():
    plan = {"authorized_files": [], "baseline_sha256": {}, "workspace_status_before": [], "workspace_status_available": False}
    assert post_change_check(plan)["post_change_drift_check"] == "PASS"


def test_scoped_drift_allows_target_and_unrelated_changes_but_reports_them(tmp_path, monkeypatch):
    target = tmp_path / "target.py"
    protected = tmp_path / "protected.json"
    target.write_text("before")
    protected.write_text("stable")
    plan = {
        "scope_mode": "SCOPED_TARGETS",
        "authorized_files": [str(target)],
        "baseline_sha256": {str(target): __import__("hashlib").sha256(b"before").hexdigest()},
        "allowed_dependency_files": [], "allowed_dependency_sha256": {},
        "prohibited_file_hashes": {str(protected): __import__("hashlib").sha256(b"stable").hexdigest()},
        "prohibited_path_patterns": [], "workspace_status_before_paths": ["existing.txt"],
        "workspace_status_available": True,
    }
    target.write_text("approved change")
    monkeypatch.setattr("change_target_resolver._git_status", lambda: {"existing.txt", "unrelated.txt"})
    result = post_change_check(plan)
    assert result["post_change_drift_check"] == "PASS"
    assert result["drift_classification"] == "AUTHORIZED_TARGET_DRIFT"
    assert result["unrelated_workspace_drift"]["classification"] == "INFORMATIONAL_NONBLOCKING"
    assert result["authorized_target_drift"] == [str(target)]


def test_scoped_drift_fails_when_prohibited_target_changes(tmp_path, monkeypatch):
    target = tmp_path / "target.py"
    protected = tmp_path / "protected.json"
    target.write_text("stable")
    protected.write_text("before")
    plan = {
        "scope_mode": "SCOPED_TARGETS", "authorized_files": [str(target)],
        "baseline_sha256": {str(target): __import__("hashlib").sha256(b"stable").hexdigest()},
        "allowed_dependency_files": [], "allowed_dependency_sha256": {},
        "prohibited_file_hashes": {str(protected): __import__("hashlib").sha256(b"before").hexdigest()},
        "prohibited_path_patterns": [], "workspace_status_before_paths": [],
        "workspace_status_available": True,
    }
    protected.write_text("prohibited change")
    monkeypatch.setattr("change_target_resolver._git_status", lambda: set())
    result = post_change_check(plan)
    assert result["post_change_drift_check"] == "FAIL"
    assert result["drift_classification"] == "PROHIBITED_TARGET_DRIFT"


def test_unavailable_workspace_baseline_does_not_turn_existing_paths_into_new_prohibited_drift(tmp_path, monkeypatch):
    target = tmp_path / "target.py"
    protected = tmp_path / "protected.json"
    target.write_text("stable")
    protected.write_text("stable")
    plan = {
        "scope_mode": "SCOPED_TARGETS", "authorized_files": [str(target)],
        "baseline_sha256": {str(target): __import__("hashlib").sha256(b"stable").hexdigest()},
        "allowed_dependency_files": [], "allowed_dependency_sha256": {},
        "prohibited_file_hashes": {str(protected): __import__("hashlib").sha256(b"stable").hexdigest()},
        "prohibited_path_patterns": [str(protected)], "workspace_status_before_paths": [],
        "workspace_status_available": False,
    }
    monkeypatch.setattr("change_target_resolver._git_status", lambda: {"data/protected.json"})
    result = post_change_check(plan)
    assert result["post_change_drift_check"] == "PASS"
    assert result["unrelated_workspace_drift"]["status"] == "BASELINE_UNAVAILABLE"


def test_secret_guard_redacts_common_secrets_without_exposing_values():
    sample = "Authorization: Bearer abcdefghijklmnop123456 api_key=abcdef1234567890 password=hunter2 123456:abcdefghijklmnopqrstuvwxyz0123456789"
    result = redact_text(sample)
    assert "[REDACTED]" in result
    assert "abcdefghijklmnop123456" not in result
    assert "hunter2" not in result
    assert "123456:abcdefghijklmnopqrstuvwxyz" not in result


def test_kaggle_job_contract_rejects_path_traversal_and_bounds_inputs(tmp_path):
    workdir = tmp_path.resolve()
    (workdir / "inputs").mkdir()
    (workdir / "inputs" / "a.txt").write_text("safe")
    job = {"job_id": "job-1", "objective": "bounded test", "workload_type": "batch_analysis", "command_argv": ["python3", "task.py"], "timeout_seconds": 30, "input_artifacts": [{"path": "inputs/a.txt"}], "expected_outputs": ["outputs/result.json"]}
    argv, files = validate_job(job, workdir)
    assert argv == job["command_argv"] and files[0]["size_bytes"] == 4
    job["input_artifacts"] = [{"path": "../outside.txt"}]
    try:
        validate_job(job, workdir)
    except ValueError as exc:
        assert str(exc) == "ARTIFACT_PATH_OUTSIDE_JOB_ROOT"
    else:
        raise AssertionError("traversal must be rejected")


def test_kaggle_packager_hashes_only_declared_bounded_outputs(tmp_path):
    (tmp_path / "outputs").mkdir()
    (tmp_path / "outputs" / "result.txt").write_text("model result")
    result = package_outputs(tmp_path, "job-2", ["outputs/result.txt"])
    archive = tmp_path / "outputs/packages/job-2.zip"
    assert result["archive_sha256"]
    with zipfile.ZipFile(archive) as z:
        assert "outputs/result.txt" in z.namelist()
        assert "result_manifest.json" in z.namelist()


def test_kaggle_packager_rejects_secret_like_output_content(tmp_path):
    (tmp_path / "outputs").mkdir()
    (tmp_path / "outputs" / "result.json").write_text('{"api_key":"synthetic_test_secret_123456"}')
    try:
        package_outputs(tmp_path, "job-3", ["outputs/result.json"])
    except ValueError as exc:
        assert str(exc) == "POTENTIAL_SECRET_IN_OUTPUT"
    else:
        raise AssertionError("secret-like output must not be packaged")


def test_install_technology_target_is_opencode_config_not_systems_document():
    import json
    manifest = json.loads((ROOT / "docs/systems/NEXUS_LIVING_MANIFEST.v1.json").read_text())
    action = manifest["systems_managed_work"]["action_targets"]["INSTALL_TECHNOLOGY"]
    assert action["component"] == "opencode"
    assert str((Path.home() / ".config/opencode/opencode.jsonc").resolve()) in action["requested_files"]
    assert not any("SYSTEMS_PHASE2_CONTROL_LAYER.md" in p for p in action["requested_files"])
    resolved = resolve_target(manifest, "opencode", "Configure native REA MCP", action["requested_files"])
    assert resolved["authority_check"] == "PASS"
    assert str((Path.home() / ".config/opencode/opencode.jsonc").resolve()) in resolved["authorized_files"]
    try:
        resolve_target(manifest, "opencode", "Reject documentation target", ["docs/systems/SYSTEMS_PHASE2_CONTROL_LAYER.md"])
    except ValueError:
        pass
    else:
        raise AssertionError("Systems documentation path must not resolve as an install target")
