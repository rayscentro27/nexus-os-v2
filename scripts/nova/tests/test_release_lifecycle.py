import hashlib
import json
import os
import sys
import tempfile
import hashlib
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from release_lifecycle import (  # noqa: E402
    ACTIVATE_ACTION, NovaReleaseCapability, NovaReleaseController, NovaReleasePolicy, create_manifest,
    validate_release, FixedNovaHost, GovernedApprovalStore, REQUIRED_FILES,
)


RELEASE_A = "nova-operator-v1-20261029-r90-clean-acceptance"
RELEASE_B = "nova-operator-v1-20261029-r91-clean-acceptance"


def make_release(root: Path, name: str) -> tuple[Path, str]:
    path = root / name
    for relative in REQUIRED_FILES:
        target = path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# fixture module\n", encoding="utf-8")
    digest, _ = create_manifest(path)
    for target in sorted(path.rglob("*"), reverse=True):
        target.chmod(0o555 if target.is_dir() else 0o444)
    path.chmod(0o555)
    return path, digest


def make_cert_release(root: Path, name: str) -> tuple[Path, str]:
    path = root / name
    fixture = path / "scripts/nova/lifecycle_fixture_worker.py"
    fixture.parent.mkdir(parents=True, exist_ok=True)
    fixture.write_text("import time\nwhile True: time.sleep(1)\n", encoding="utf-8")
    digest, _ = create_manifest(path)
    for target in sorted(path.rglob("*"), reverse=True):
        target.chmod(0o555 if target.is_dir() else 0o444)
    path.chmod(0o555)
    return path, digest


class FakeHost:
    def __init__(self, code_root="", pythonpath="", status="Active: active (running)"):
        self.calls = []
        self.rows = []
        self.status = status
        self.code_root = code_root
        self.pythonpath = pythonpath
        self.restart_hook = None

    def systemctl(self, action):
        assert action in {"daemon-reload", "restart", "status", "show"}
        self.calls.append(action)
        if action == "status":
            return f"● nova-telegram-oracle.service\n{self.status}"
        if action == "restart" and self.restart_hook:
            self.restart_hook(len([call for call in self.calls if call == "restart"]))
        return "ok"

    def pollers(self):
        return list(self.rows)


class FakeApproval:
    def __init__(self, allowed=True):
        self.allowed = allowed
        self.requests = []
        self.consumed = []

    def request(self, action_id, inputs, detail):
        self.requests.append((action_id, inputs, detail))
        return {"id": "approval-test", "action_id": action_id, "status": "pending", "input_summary": inputs}

    def consume(self, approval_id, action_id, inputs):
        if not self.allowed or approval_id != "approval-test" or action_id not in {ACTIVATE_ACTION, "nova.release.rollback"}:
            raise PermissionError("approval required")
        self.consumed.append((approval_id, action_id, inputs))
        return {"id": approval_id}


@pytest.fixture
def setup_controller(tmp_path):
    roots = [tmp_path / name for name in ("releases", "staging", "dropins", "receipts", "repo/data/runtime")]
    for root in roots:
        root.mkdir(parents=True, exist_ok=True)
    policy = NovaReleasePolicy(*roots)
    old, old_hash = make_release(policy.release_root, RELEASE_A)
    new, new_hash = make_release(policy.release_root, RELEASE_B)
    old_dropin = policy.dropin_root / "nova-active.conf"
    old_dropin.write_text(
        f"[Service]\nExecStart=\nExecStart=/usr/bin/python {old}/scripts/nova/nova_telegram_worker.py --poll\n"
        f"Environment=NOVA_CODE_ROOT={old}\nEnvironment=PYTHONPATH={old}/scripts\n", encoding="utf-8")
    host = FakeHost()
    approval = FakeApproval()
    test_runs = []
    def test_runner(candidate, paths):
        test_runs.append((candidate, paths))
        return {"test_commands": [["python", "-m", "pytest", *paths]],
                "test_result": "PASS", "test_count": 15}
    def provenance_provider(source_root, manifest_hash):
        return {"source_root": str(source_root), "source_commit_or_revision": "a" * 40,
                "source_tree_state": "DIRTY", "source_state_hash": "b" * 64,
                "source_trusted": True,
                "build_input_hash": hashlib.sha256(manifest_hash.encode()).hexdigest(),
                "manifest_hash": manifest_hash, "attested_at": "2026-11-03T00:00:00Z"}
    controller = NovaReleaseController(policy, host, approval, test_runner=test_runner,
                                       provenance_provider=provenance_provider)
    return controller, policy, old, old_hash, new, new_hash, host, approval


def stage_receipt(controller, candidate, manifest_hash, *, trusted=True, test_result="PASS", tested_hash=None):
    receipt = {"deployment_id": "stage_" + hashlib.sha256((candidate + manifest_hash).encode()).hexdigest()[:32],
               "operation": "STAGE", "candidate_release": candidate, "candidate_hash": manifest_hash,
               "provenance_attestation": {"source_root": "/trusted/nexus", "source_commit_or_revision": "a" * 40,
                   "source_tree_state": "DIRTY", "source_state_hash": "b" * 64, "source_trusted": trusted,
                   "build_input_hash": "c" * 64, "manifest_hash": manifest_hash},
               "test_attestation": None}
    controller._write_receipt(receipt)
    return receipt


def test_candidate_validation_and_manifest_mismatch(setup_controller):
    controller, policy, old, old_hash, new, new_hash, *_ = setup_controller
    assert validate_release(new, expected_manifest_hash=new_hash)["valid"]
    changed = new / "scripts/nova/context_authority.py"
    changed.chmod(0o644)
    changed.write_text("tampered\n", encoding="utf-8")
    result = controller.validate(candidate_release=RELEASE_B, expected_manifest_hash=new_hash)
    assert not result["valid"]
    assert result["mismatches"]


def test_mixed_release_and_multiple_dropins_are_rejected(setup_controller):
    controller, policy, old, *_ = setup_controller
    effective = controller.inspect_effective_config()
    assert effective["release"] == RELEASE_A
    (policy.dropin_root / "another.conf").write_text("[Service]\n", encoding="utf-8")
    assert controller.inspect_effective_config()["effective_dropin_count"] == 2
    (policy.dropin_root / "another.conf").unlink()
    path = policy.dropin_root / "nova-active.conf"
    path.chmod(0o644)
    path.write_text(path.read_text().replace(f"NOVA_CODE_ROOT={old}", "NOVA_CODE_ROOT=/other"), encoding="utf-8")
    assert controller.inspect_effective_config()["code_root"] == "/other"
    assert not controller.verify(expected_release=RELEASE_A)["pass"]


def test_stage_is_immutable_and_receipted_without_service_mutation(setup_controller):
    controller, policy, *_rest, host, _approval = setup_controller
    bundle = policy.staging_root / "nova-operator-v1-20261029-r92-clean-acceptance"
    make_release(policy.staging_root, bundle.name)
    # The staging manifest is input metadata; stage writes its own manifest.
    result = controller.stage(candidate_release="nova-operator-v1-20261029-r92-clean-acceptance",
                              bundle_id=bundle.name)
    assert result["immutable"] and result["validation"]["valid"]
    assert result["receipt"]["verification_result"] == "STAGED"
    assert result["receipt"]["provenance_attestation"]["manifest_hash"] == result["manifest_hash"]
    assert "build_input_hash" in result["receipt"]["provenance_attestation"]
    assert controller.receipt(deployment_id=result["receipt"]["deployment_id"])["status"] == "FOUND"
    assert not host.calls
    with pytest.raises(FileExistsError):
        controller.stage(candidate_release=bundle.name, bundle_id=bundle.name)


def test_activation_approval_bound_to_candidate_before_any_mutation(setup_controller):
    controller, policy, old, old_hash, new, new_hash, host, approval = setup_controller
    plan = controller.request_activation_approval(deployment_id="deploy_" + "a" * 32,
        candidate_release=RELEASE_B, candidate_hash=new_hash, current_release=RELEASE_A,
        dropin_name="nova-release-active.conf")
    assert plan["approval_required"] and not host.calls
    assert approval.requests[0][0] == ACTIVATE_ACTION
    approval.allowed = False
    with pytest.raises(PermissionError):
        controller.activate(deployment_id="deploy_" + "a" * 32, candidate_release=RELEASE_B,
            candidate_hash=new_hash, previous_release=RELEASE_A, dropin_name="nova-release-active.conf",
            approval_id="approval-test")
    assert not host.calls


def test_trusted_candidate_with_manifest_bound_pass_tests_activates_without_approval(setup_controller):
    controller, policy, old, old_hash, new, new_hash, host, approval = setup_controller
    stage_receipt(controller, RELEASE_B, new_hash)
    validation = controller.validate(candidate_release=RELEASE_B, expected_manifest_hash=new_hash)
    assert validation["test_attestation"]["test_result"] == "PASS"
    assert validation["test_attestation"]["tested_manifest_hash"] == new_hash
    host.rows = [{"pid": 501, "code_root": str(new), "pythonpath": str(new / "scripts")}]
    result = NovaReleaseCapability(controller).invoke("nova.release.activate", {
        "deployment_id": "deploy_" + "1" * 32, "candidate_release": RELEASE_B,
        "candidate_hash": new_hash, "current_release": RELEASE_A,
        "dropin_name": "nova-release-active.conf"})
    assert result["status"] == "COMPLETE"
    assert result["receipt"]["approval_mode"] == "ATTESTED_INTERNAL"
    assert not approval.requests


def test_validate_runs_tests_against_exact_staged_release(setup_controller):
    controller, policy, _old, _old_hash, _new, _new_hash, _host, _approval = setup_controller
    bundle_name = "nova-operator-v1-20261029-r92-clean-acceptance"
    bundle = policy.staging_root / bundle_name
    make_release(policy.staging_root, bundle_name)
    staged = controller.stage(candidate_release=bundle_name, bundle_id=bundle_name)
    result = controller.validate(candidate_release=bundle_name,
        expected_manifest_hash=staged["manifest_hash"])
    saved = controller.receipt(deployment_id=staged["receipt"]["deployment_id"])["receipt"]
    assert result["test_attestation"]["test_result"] == "PASS"
    assert result["test_attestation"]["tested_manifest_hash"] == staged["manifest_hash"]
    assert saved["test_attestation"] == result["test_attestation"]


def test_failed_tests_deny_activation_even_if_manual_approval_is_attempted(setup_controller):
    controller, policy, old, old_hash, new, new_hash, host, approval = setup_controller
    stage_receipt(controller, RELEASE_B, new_hash)
    controller.test_runner = lambda _path, _tests: {"test_commands": [["pytest"]], "test_result": "FAIL", "test_count": 0}
    validation = controller.validate(candidate_release=RELEASE_B, expected_manifest_hash=new_hash)
    assert validation["test_attestation"]["test_result"] == "FAIL"
    with pytest.raises(PermissionError, match="ATTESTATION_INVALID:TESTS_FAILED"):
        controller.activate(deployment_id="deploy_" + "2" * 32, candidate_release=RELEASE_B,
            candidate_hash=new_hash, previous_release=RELEASE_A, dropin_name="nova-release-active.conf",
            approval_id="approval-test")
    assert not host.calls


def test_post_test_manifest_mutation_invalidates_activation_attestation(setup_controller):
    controller, policy, old, old_hash, new, new_hash, host, _approval = setup_controller
    stage_receipt(controller, RELEASE_B, new_hash)
    controller.validate(candidate_release=RELEASE_B, expected_manifest_hash=new_hash)
    changed = new / "scripts/nova/context_authority.py"
    changed.chmod(0o644)
    changed.write_text("changed after tests\n", encoding="utf-8")
    with pytest.raises(ValueError, match="CANDIDATE_OR_ROLLBACK_VALIDATION_FAILED"):
        controller.activate(deployment_id="deploy_" + "3" * 32, candidate_release=RELEASE_B,
            candidate_hash=new_hash, previous_release=RELEASE_A, dropin_name="nova-release-active.conf")
    assert not host.calls


def test_untrusted_source_requires_existing_manual_approval_path(setup_controller):
    controller, policy, old, old_hash, new, new_hash, host, approval = setup_controller
    stage_receipt(controller, RELEASE_B, new_hash, trusted=False)
    controller.validate(candidate_release=RELEASE_B, expected_manifest_hash=new_hash)
    result = controller.activate(deployment_id="deploy_" + "4" * 32, candidate_release=RELEASE_B,
        candidate_hash=new_hash, previous_release=RELEASE_A, dropin_name="nova-release-active.conf")
    assert result["approval_required"] is True
    assert approval.requests[-1][0] == ACTIVATE_ACTION
    assert not host.calls


def test_different_tested_manifest_is_rejected(setup_controller):
    controller, policy, old, old_hash, new, new_hash, host, _approval = setup_controller
    receipt = stage_receipt(controller, RELEASE_B, new_hash)
    receipt["test_attestation"] = {"test_result": "PASS", "test_count": 3,
        "test_commands": [["pytest", "-q"]], "test_timestamp": "2026-11-03T00:00:00Z",
        "tested_manifest_hash": "d" * 64,
        "source_build_input_hash": receipt["provenance_attestation"]["build_input_hash"]}
    controller._write_receipt(receipt)
    with pytest.raises(PermissionError, match="ATTESTATION_INVALID:ATTESTATION_MANIFEST_MISMATCH"):
        controller.activate(deployment_id="deploy_" + "5" * 32, candidate_release=RELEASE_B,
            candidate_hash=new_hash, previous_release=RELEASE_A, dropin_name="nova-release-active.conf")
    assert not host.calls


def test_source_provenance_records_dirty_tree_and_binds_candidate_hash(tmp_path):
    source = tmp_path / "nexus-source"
    source.mkdir()
    subprocess = __import__("subprocess")
    subprocess.run(["git", "init", str(source)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(source), "config", "user.email", "nexus-test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(source), "config", "user.name", "Nexus Test"], check=True)
    (source / "tracked.txt").write_text("base\n")
    subprocess.run(["git", "-C", str(source), "add", "tracked.txt"], check=True)
    subprocess.run(["git", "-C", str(source), "commit", "-m", "fixture"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(source), "remote", "add", "origin",
                    "https://github.com/rayscentro27/nexus-os-v2.git"], check=True)
    roots = [tmp_path / name for name in ("rels", "stage", "drop", "receipts", "nexus-source/data/runtime")]
    for root in roots: root.mkdir(parents=True, exist_ok=True)
    policy = NovaReleasePolicy(*roots)
    controller = NovaReleaseController(policy)
    clean = controller._source_provenance(source, "a" * 64)
    (source / "tracked.txt").write_text("dirty\n")
    dirty = controller._source_provenance(source, "b" * 64)
    assert clean["source_trusted"] and clean["source_tree_state"] == "CLEAN"
    assert dirty["source_trusted"] and dirty["source_tree_state"] == "DIRTY"
    assert dirty["source_state_hash"] != clean["source_state_hash"]
    assert dirty["build_input_hash"] != clean["build_input_hash"]


def test_candidate_tests_run_in_secret_free_environment(tmp_path, monkeypatch):
    candidate = tmp_path / "candidate"
    tests = candidate / "scripts/nova/tests"
    tests.mkdir(parents=True)
    (tests / "test_environment.py").write_text(
        "import os\ndef test_candidate_test_environment_has_no_parent_secrets():\n"
        "    assert os.environ.get('NEXUS_TEST_SECRET_SENTINEL') is None\n", encoding="utf-8")
    monkeypatch.setenv("NEXUS_TEST_SECRET_SENTINEL", "never-forward")
    controller = NovaReleaseController(NovaReleasePolicy(
        tmp_path / "releases", tmp_path / "staging", tmp_path / "dropins",
        tmp_path / "receipts", tmp_path / "repo/data/runtime", test_paths=("scripts/nova/tests/test_environment.py",)))
    result = controller._run_candidate_tests(candidate, controller.policy.test_paths)
    assert result["test_result"] == "PASS"
    assert result["test_count"] == 1
    assert "test_output" not in result


def test_only_fixed_nova_systemd_actions_are_allowed():
    calls = []
    def runner(argv, **kwargs):
        calls.append(argv)
        class Result: returncode = 0; stdout = "ok"; stderr = ""
        return Result()
    host = FixedNovaHost(runner=runner)
    host.systemctl("daemon-reload")
    host.systemctl("restart")
    host.systemctl("status")
    assert calls == [
        ["systemctl", "--user", "daemon-reload"],
        ["systemctl", "--user", "restart", "nova-telegram-oracle.service"],
        ["systemctl", "--user", "status", "nova-telegram-oracle.service"],
    ]
    with pytest.raises(ValueError):
        host.systemctl("restart hermes")


def test_activation_receipt_and_single_dropin(setup_controller):
    controller, policy, old, old_hash, new, new_hash, host, approval = setup_controller
    approval_id = "approval-test"
    deployment = "deploy_" + "b" * 32
    controller.request_activation_approval(deployment_id=deployment, candidate_release=RELEASE_B,
        candidate_hash=new_hash, current_release=RELEASE_A, dropin_name="nova-release-active.conf")
    host.rows = [{"pid": 300, "code_root": str(new), "pythonpath": str(new / "scripts")}]
    result = controller.activate(deployment_id=deployment, candidate_release=RELEASE_B,
        candidate_hash=new_hash, previous_release=RELEASE_A, dropin_name="nova-release-active.conf",
        approval_id=approval_id)
    assert result["status"] == "COMPLETE"
    assert result["verification"]["pass"]
    assert result["receipt"]["dropin_changed"]
    assert result["receipt"]["service_restarted"]
    assert {"deployment_id", "operation", "candidate_release", "candidate_hash", "previous_release",
            "previous_hash", "approval_id", "dropin_changed", "service_restarted", "process_pid_before",
            "process_pid_after", "verification_result", "rollback_performed", "mutation_list", "started_at",
            "completed_at"}.issubset(result["receipt"])
    assert len(list(policy.dropin_root.glob("*.conf"))) == 1
    assert (policy.receipt_root / f"{deployment}.json").is_file()
    assert controller.receipt(deployment_id=deployment)["receipt"]["candidate_release"] == RELEASE_B
    assert host.calls == ["daemon-reload", "restart", "status"]


def test_failed_verification_auto_rolls_back_only_under_bound_approval(setup_controller):
    controller, policy, old, old_hash, new, new_hash, host, approval = setup_controller
    deployment = "deploy_" + "c" * 32
    controller.request_activation_approval(deployment_id=deployment, candidate_release=RELEASE_B,
        candidate_hash=new_hash, current_release=RELEASE_A, dropin_name="nova-release-active.conf")
    # No poller means verification fails and the approval pre-authorizes rollback.
    host.restart_hook = lambda count: setattr(host, "rows", ([{"pid": 301, "code_root": str(old),
        "pythonpath": str(old / "scripts")}] if count == 2 else []))
    result = controller.activate(deployment_id=deployment, candidate_release=RELEASE_B,
        candidate_hash=new_hash, previous_release=RELEASE_A, dropin_name="nova-release-active.conf",
        approval_id="approval-test")
    assert result["status"] == "ROLLED_BACK"
    assert result["rollback"]["pass"]
    assert result["receipt"]["rollback_performed"]
    rollback_receipt_id = result["receipt"]["rollback_receipt_id"]
    assert controller.receipt(deployment_id=rollback_receipt_id)["receipt"]["operation"] == "AUTOMATIC_ROLLBACK"
    assert (policy.receipt_root / f"{deployment}.json").is_file()
    assert len(list(policy.dropin_root.glob("*.conf"))) == 1
    assert host.calls == ["daemon-reload", "restart", "status", "daemon-reload", "restart", "status"]


def test_arbitrary_release_bundle_path_and_dropin_names_are_rejected(setup_controller):
    controller, policy, *_ = setup_controller
    with pytest.raises(ValueError):
        controller.validate(candidate_release="../etc")
    with pytest.raises(ValueError):
        controller._validate_dropin_name("../../hermes.conf")
    with pytest.raises(ValueError, match="INVALID_DROPIN_SNAPSHOT"):
        controller._restore_dropins({"..": b"[Service]\n"})
    with pytest.raises(ValueError):
        controller.stage(candidate_release=RELEASE_B, bundle_id="../hermes")
    facade = NovaReleaseCapability(controller)
    with pytest.raises(ValueError, match="CAPABILITY_NOT_ALLOWED"):
        facade.invoke("shell.execute", {"command": "systemctl restart hermes"})
    with pytest.raises(ValueError, match="ARGUMENT_SCHEMA_INVALID"):
        facade.invoke("nova.release.validate", {"candidate_release": RELEASE_B, "path": "/etc/passwd"})
    with pytest.raises(ValueError):
        NovaReleasePolicy(*([policy.release_root, policy.staging_root, policy.dropin_root,
                             policy.receipt_root, policy.runtime_state_root]), service="hermes.service")


def test_nova_only_scope_leaves_other_services_unaddressable(setup_controller):
    controller, _policy, *_rest, host, _approval = setup_controller
    assert controller.policy.service == "nova-telegram-oracle.service"
    assert host.calls == []
    # The host adapter has no generic service argument; every service call is fixed.
    assert "service" not in controller.activate.__annotations__
    assert all(call != "hermes.service" for call in host.calls)


def test_operator_facade_exposes_exactly_six_typed_operations(setup_controller):
    controller, _policy, _old, _old_hash, _new, _new_hash, host, approvals = setup_controller
    facade = NovaReleaseCapability(controller)
    assert set(facade.CONTRACTS) == {"nova.release.status", "nova.release.stage", "nova.release.validate",
        "nova.release.activate", "nova.release.verify", "nova.release.rollback"}
    result = facade.invoke("nova.release.activate", {"deployment_id": "deploy_" + "1" * 32,
        "candidate_release": RELEASE_B, "candidate_hash": _new_hash, "current_release": RELEASE_A,
        "dropin_name": "nova-release-active.conf"})
    assert result["approval_required"] is True
    assert not host.calls
    assert approvals.requests[-1][1]["automatic_rollback_on_failure"] is True


def test_operator_registry_contains_only_typed_nova_release_operations():
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
    from nexus_agent_platform.capabilities.python_registry import get_default_registry
    registry = get_default_registry()
    expected = {"nova.release.status", "nova.release.stage", "nova.release.validate",
                "nova.release.activate", "nova.release.verify", "nova.release.rollback"}
    actual = {row["capability_id"] for row in registry.list_capabilities() if row["capability_id"].startswith("nova.release.")}
    assert actual == expected
    for capability_id in expected:
        assert registry.get(capability_id).enabled
        assert not registry.get(capability_id).approval_required


def test_typed_lifecycle_is_not_duplicated_in_generic_action_registry():
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
    from nexus_agent_platform.governed.action_registry import action_exists
    assert not action_exists("nova.release.activate")
    assert not action_exists("nova.release.rollback")
    from nexus_agent_platform.capabilities.python_registry import get_default_registry
    registry = get_default_registry()
    for capability_id in (
        "nova.release.status", "nova.release.stage", "nova.release.validate",
        "nova.release.activate", "nova.release.verify", "nova.release.rollback",
    ):
        capability = registry.get(capability_id)
        assert capability and capability.enabled and not capability.approval_required


def test_governed_approval_adapter_requires_ray_and_exact_bound_inputs(monkeypatch):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
    from nexus_agent_platform.governed import approvals
    expected = {"deployment_id": "deploy_" + "f" * 32, "candidate_release": RELEASE_B,
                "candidate_hash": "a" * 64, "current_release": RELEASE_A,
                "dropin_name": "nova-release-active.conf", "automatic_rollback_on_failure": True}
    row = {"id": "approved-1", "action_id": ACTIVATE_ACTION, "status": "approved",
           "resolved_by": "Ray", "input_summary": expected}
    monkeypatch.setattr(approvals, "get_approval", lambda _aid: row)
    monkeypatch.setattr(approvals, "is_approval_valid_for", lambda item, action, inputs:
                        "" if item["input_summary"] == inputs and item["action_id"] == action else "mismatch")
    consumed = []
    monkeypatch.setattr(approvals, "mark_approval_consumed", lambda aid: consumed.append(aid))
    store = GovernedApprovalStore()
    assert store.consume("approved-1", ACTIVATE_ACTION, expected)["id"] == "approved-1"
    assert consumed == ["approved-1"]
    with pytest.raises(PermissionError):
        store.consume("approved-1", ACTIVATE_ACTION, {**expected, "candidate_hash": "b" * 64})
    row["resolved_by"] = "nexus"
    with pytest.raises(PermissionError, match="RAY_APPROVAL"):
        store.consume("approved-1", ACTIVATE_ACTION, expected)


def test_single_poller_verification_rejects_multiple_pollers(setup_controller):
    controller, _policy, _old, _old_hash, _new, _new_hash, host, _approval = setup_controller
    host.rows = [{"pid": 1}, {"pid": 2}]
    result = controller.verify(expected_release=RELEASE_B)
    assert not result["pass"]
    assert result["poller_count"] == 2


def test_status_and_receipt_reads_are_read_only(setup_controller):
    controller, _policy, _old, _old_hash, _new, _new_hash, host, _approval = setup_controller
    host.rows = [{"pid": 77}]
    status = NovaReleaseCapability(controller).invoke("nova.release.status")
    assert status["read_only"] is True
    assert status["poller_count"] == 1
    assert host.calls == ["status", "show"]


def test_known_good_rollback_restores_persisted_snapshot_without_approval(setup_controller):
    controller, policy, old, old_hash, new, new_hash, host, approval = setup_controller
    deployment = "deploy_" + "d" * 32
    controller.request_activation_approval(deployment_id=deployment, candidate_release=RELEASE_B,
        candidate_hash=new_hash, current_release=RELEASE_A, dropin_name="nova-release-active.conf")
    host.rows = [{"pid": 400, "code_root": str(new), "pythonpath": str(new / "scripts")}]
    controller.activate(deployment_id=deployment, candidate_release=RELEASE_B,
        candidate_hash=new_hash, previous_release=RELEASE_A, dropin_name="nova-release-active.conf",
        approval_id="approval-test")
    rollback_id = "deploy_" + "e" * 32
    host.restart_hook = lambda _count: setattr(host, "rows", [{"pid": 401, "code_root": str(old),
        "pythonpath": str(old / "scripts")}])
    result = controller.request_rollback_approval(deployment_id=rollback_id, target_release=RELEASE_A,
        target_hash=old_hash, current_release=RELEASE_B, source_deployment_id=deployment)
    assert result["status"] == "COMPLETE"
    assert result["approval_required"] is False
    assert result["rollback_mode"] == "KNOWN_GOOD_AUTONOMOUS"
    assert result["receipt"]["rollback_performed"]
    assert result["receipt"]["approval_mode"] == "KNOWN_GOOD_AUTONOMOUS"
    assert len(approval.requests) == 1  # no separate rollback approval was requested
    assert approval.requests[0][0] == ACTIVATE_ACTION
    assert len(list(policy.dropin_root.glob("*.conf"))) == 1


def test_certification_mode_targets_only_inert_fixture_service(tmp_path):
    release_root = tmp_path / "releases"
    staging_root = tmp_path / "staging"
    dropin_root = tmp_path / "cert-unit.service.d"
    receipt_root = tmp_path / "cert-receipts"
    runtime_root = tmp_path / "cert-state"
    for root in (release_root, staging_root, dropin_root, receipt_root, runtime_root):
        root.mkdir(parents=True)
    previous, previous_hash = make_cert_release(release_root, "nova-operator-v1-20261029-r98-cert-fixture")
    candidate, candidate_hash = make_cert_release(release_root, "nova-operator-v1-20261029-r99-cert-fixture")
    (dropin_root / "cert-active.conf").write_text(
        f"[Service]\nExecStart=\nExecStart=/usr/bin/python3 {previous}/scripts/nova/lifecycle_fixture_worker.py --hold\n"
        f"Environment=NOVA_CODE_ROOT={previous}\nEnvironment=PYTHONPATH={previous}/scripts\n", encoding="utf-8")
    policy = NovaReleasePolicy(release_root, staging_root, dropin_root, receipt_root, runtime_root,
                               mode="certification")
    host = FakeHost(status=f"● {policy.service}\nActive: active (running)")
    approvals = FakeApproval()
    controller = NovaReleaseController(policy, host, approvals)
    assert policy.service == "nova-release-lifecycle-cert.service"
    assert "nova-release-lifecycle-cert.service" in controller.status()["service"]
    host.calls.clear()
    approvals.requests.clear()
    candidate_hash = controller.validate(candidate_release=candidate.name, expected_manifest_hash=candidate_hash)["manifest_hash"]
    plan = controller.request_activation_approval(deployment_id="deploy_" + "9" * 32,
        candidate_release=candidate.name, candidate_hash=candidate_hash,
        current_release=previous.name, dropin_name="nova-cert-active.conf")
    assert plan["approval_required"] and not host.calls
    host.rows = [{"pid": 901, "code_root": str(candidate), "pythonpath": str(candidate / "scripts"),
                  "cert_release_id": candidate.name}]
    result = controller.activate(deployment_id="deploy_" + "9" * 32,
        candidate_release=candidate.name, candidate_hash=candidate_hash,
        previous_release=previous.name, dropin_name="nova-cert-active.conf", approval_id="approval-test")
    assert result["verification"]["pass"]
    config_text = (dropin_root / "nova-cert-active.conf").read_text()
    assert "lifecycle_fixture_worker.py --hold" in config_text
    assert "nova_telegram_worker.py" not in config_text
    assert "EnvironmentFile=" not in config_text
    assert policy.service not in {"nova-telegram-oracle.service", "nexus-hermes-0225.service"}
