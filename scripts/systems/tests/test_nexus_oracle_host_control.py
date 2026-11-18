from __future__ import annotations

import hashlib
import json
import os
import threading
import sys
import tarfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nexus_oracle_host_control as hc


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _manifest(root: Path) -> str:
    rows = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "RELEASE_MANIFEST.sha256"):
        rows.append(f"{_sha(path.read_bytes())}  {path.relative_to(root).as_posix()}")
    data = ("\n".join(rows) + "\n").encode()
    (root / "RELEASE_MANIFEST.sha256").write_bytes(data)
    return _sha(data)


def _make_readonly(root: Path) -> None:
    for path in root.rglob("*"):
        path.chmod(0o555 if path.is_dir() else 0o444)
    root.chmod(0o555)


def _policy(tmp_path: Path, **overrides) -> hc.Policy:
    rel = tmp_path / "releases"
    state = tmp_path / "state"
    incoming = state / "incoming"
    unitroot = tmp_path / "systemd"
    dropins = unitroot / (hc.PRODUCTION_SERVICE + ".d")
    base = unitroot / hc.PRODUCTION_SERVICE
    return hc.Policy(release_root=rel, state_root=state, incoming_root=incoming,
                     unit_root=unitroot, dropin_root=dropins, base_unit=base,
                     cgroup_root=tmp_path / "cgroup", proc_root=tmp_path / "proc",
                     test_mode=True, **overrides)


def _runner_for(policy: hc.Policy):
    def runner(argv, **kwargs):
        action = argv[2]
        if action == "show":
            return type("Result", (), {"returncode": 0, "stdout":
                f"MainPID=501\nFragmentPath={policy.base_unit}\nDropInPaths={policy.dropin_root / '10-base.conf'}\n"
                f"ExecStart={hc.PRODUCTION_PYTHON} /x/scripts/nova/nova_telegram_worker.py --poll\n"
                f"WorkingDirectory=/x\nEnvironment=API_TOKEN=secret OTHER=ok\nControlGroup=/test/novaservice.slice\n",
                "stderr": ""})()
        if action == "status":
            return type("Result", (), {"returncode": 0, "stdout": "active (running)\n", "stderr": ""})()
        if action == "is-active":
            return type("Result", (), {"returncode": 0, "stdout": "active\n", "stderr": ""})()
        return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()
    return runner


def _write_approval(policy: hc.Policy, op: str, binding: dict, *, consumed=False) -> str:
    approval_id = "appr_" + "a" * 32
    path = policy.state_root / "approvals" / (approval_id + ".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"approved": True, "consumed": consumed, "operation": op,
                                "binding": binding, "binding_hash": hc._json_hash(binding)}))
    return approval_id


def test_capability_allowlist_and_fixed_services():
    assert hc.CAPABILITIES == {
        "systems.oracle.release.inspect", "systems.oracle.release.stage",
        "systems.oracle.nova.snapshot", "systems.oracle.nova.snapshot_validate",
        "systems.oracle.nova.poller_status", "systems.oracle.nova.activate",
        "systems.oracle.nova.verify", "systems.oracle.nova.rollback",
        "systems.oracle.receipt.read",
    }
    with pytest.raises(ValueError, match="SERVICE_POLICY_FIXED"):
        hc.Policy(service="hermes.service")
    with pytest.raises(ValueError, match="CAPABILITY_NOT_ALLOWED"):
        hc.HostControl().invoke("shell.exec", {"command": "id"})


def test_release_inspect_and_hash_mismatch(tmp_path):
    p = _policy(tmp_path); root = p.release_root / "fixture-release-a"; root.mkdir(parents=True)
    (root / "worker.py").write_text("ok\n"); digest = _manifest(root); _make_readonly(root)
    c = hc.HostControl(p)
    assert c.inspect("fixture-release-a", digest)["mismatches"] == []
    assert c.inspect("fixture-release-a", "0" * 64)["mismatches"]
    with pytest.raises(ValueError, match="RELEASE_NAME_INVALID"):
        c.inspect("../etc", digest)


def test_stage_requires_bound_approval_and_emits_receipt_without_systemd(tmp_path):
    p = _policy(tmp_path); p.incoming_root.mkdir(parents=True)
    src = tmp_path / "payload"; src.mkdir(); (src / "worker.py").write_text("payload")
    digest = _manifest(src)
    archive = p.incoming_root / "artifact-1.tar.gz"
    with tarfile.open(archive, "w:gz") as tf:
        tf.add(src / "worker.py", arcname="worker.py")
        tf.add(src / "RELEASE_MANIFEST.sha256", arcname="RELEASE_MANIFEST.sha256")
    _make_readonly(src)
    aid = _write_approval(p, "STAGE", {"artifact_id": "artifact-1", "release_name": "fixture-release-b",
                                       "artifact_hash": digest, "manifest_hash": digest})
    calls = []; c = hc.HostControl(p, runner=lambda argv, **kw: calls.append(argv))
    out = c.stage("artifact-1", "fixture-release-b", digest, digest, aid)
    assert out["status"] == "STAGED" and out["verification"]["read_only"]
    assert out["receipt"]["mutation_count"] == 2
    assert not calls
    assert c.receipt_read(out["receipt"]["receipt_id"])["status"] == "FOUND"


def test_stage_rejects_wrong_hash_and_archive_traversal(tmp_path):
    p = _policy(tmp_path); p.incoming_root.mkdir(parents=True)
    src = tmp_path / "payload"; src.mkdir(); (src / "worker.py").write_text("payload")
    digest = _manifest(src); archive = p.incoming_root / "artifact-x.tar.gz"
    with tarfile.open(archive, "w:gz") as tf:
        info = tarfile.TarInfo("../outside"); body = b"bad"; info.size = len(body)
        import io
        tf.addfile(info, io.BytesIO(body))
    approval = _write_approval(p, "STAGE", {"artifact_id": "artifact-x", "release_name": "fixture-release-x",
                                             "artifact_hash": digest, "manifest_hash": digest})
    with pytest.raises(ValueError, match="ARTIFACT_ARCHIVE_PATH_REJECTED"):
        hc.HostControl(p).stage("artifact-x", "fixture-release-x", digest, digest, approval)
    with pytest.raises(ValueError, match="ARTIFACT_HASH_CONTRACT_INVALID"):
        hc.HostControl(p).stage("artifact-x", "fixture-release-x", "0" * 64, digest, approval)


def test_snapshot_and_validation_redact_environment_and_preserve_dropins(tmp_path):
    p = _policy(tmp_path); p.base_unit.parent.mkdir(parents=True)
    p.base_unit.write_text("[Service]\nEnvironmentFile=/home/opc/.config/nova-telegram.env\n")
    p.dropin_root.mkdir(); (p.dropin_root / "10-base.conf").write_text("[Service]\nEnvironment=MODE=prod\n")
    c = hc.HostControl(p, runner=_runner_for(p)); snap = c.snapshot()
    check = c.snapshot_validate(snap["snapshot_id"])
    assert check["valid"] and snap["dropin_count"] == 1
    row = json.loads((p.state_root / "snapshots" / (snap["snapshot_id"] + ".json")).read_text())
    assert "API_TOKEN=[REDACTED]" in row["effective"]["Environment"]
    assert row["directory_entries"] == [str(p.dropin_root / "10-base.conf")]


def test_snapshot_rejects_inline_secret_value(tmp_path):
    p = _policy(tmp_path); p.base_unit.parent.mkdir(parents=True)
    p.base_unit.write_text("[Service]\nEnvironment=API_TOKEN=actual-secret\n")
    p.dropin_root.mkdir(); (p.dropin_root / "10-base.conf").write_text("[Service]\n")
    with pytest.raises(ValueError, match="INLINE_SECRET_IN_NOVA_UNIT_CONFIG"):
        hc.HostControl(p, runner=_runner_for(p)).snapshot()


def test_snapshot_restore_preserves_exact_dropin_contents_and_modes(tmp_path):
    p = _policy(tmp_path); p.base_unit.parent.mkdir(parents=True)
    p.base_unit.write_text("[Unit]\nDescription=baseline\n")
    p.dropin_root.mkdir()
    first = p.dropin_root / "10-first.conf"; second = p.dropin_root / "20-second.conf"
    first.write_text("[Service]\nEnvironment=A=1\n"); first.chmod(0o600)
    second.write_text("[Service]\nEnvironment=B=2\n"); second.chmod(0o640)
    files = {str(p.base_unit): hc._read_config(p.base_unit),
             str(first): hc._read_config(first), str(second): hc._read_config(second)}
    snapshot = {"base_unit": str(p.base_unit), "service": p.service,
                "ordered_dropins": [str(first), str(second)],
                "directory_entries": [str(first), str(second)], "files": files}
    first.write_text("[Service]\nEnvironment=CHANGED=1\n"); first.chmod(0o644)
    second.unlink(); (p.dropin_root / "90-new.conf").write_text("[Service]\n")
    class RestoreControl(hc.HostControl):
        def _systemctl_mutation(self, _operation): return ""
        def _systemctl(self, action, *_args): return "active\n" if action == "is-active" else ""
        def poller_status(self): return {"poller_count": 1}
    result = RestoreControl(p)._restore_snapshot(snapshot, restart=True)
    assert result["pass"] is True
    assert sorted(x.name for x in p.dropin_root.iterdir()) == ["10-first.conf", "20-second.conf"]
    assert first.read_text() == "[Service]\nEnvironment=A=1\n" and first.stat().st_mode & 0o777 == 0o600
    assert second.read_text() == "[Service]\nEnvironment=B=2\n" and second.stat().st_mode & 0o777 == 0o640


def test_scoped_poller_reads_only_service_cgroup(tmp_path):
    p = _policy(tmp_path); p.base_unit.parent.mkdir(parents=True); p.base_unit.write_text("[Unit]\n")
    group = p.cgroup_root / "test/novaservice.slice"; group.mkdir(parents=True)
    (group / "cgroup.procs").write_text("501\n502\n")
    p.proc_root.joinpath("501").mkdir(parents=True); p.proc_root.joinpath("501/cmdline").write_bytes(b"python\0/x/nova_telegram_worker.py\0--poll\0")
    p.proc_root.joinpath("502").mkdir(parents=True); p.proc_root.joinpath("502/cmdline").write_bytes(b"helper\0")
    result = hc.HostControl(p, runner=_runner_for(p)).poller_status()
    assert result["main_pid"] == "501" and result["poller_pids"] == ["501"]


def test_activation_and_rollback_require_approval(tmp_path):
    p = _policy(tmp_path); c = hc.HostControl(p, runner=_runner_for(p))
    activation = {"deployment_id": "deploy_" + "b" * 32, "target_release_name": "fixture-release-a",
        "target_release_hash": "1" * 64, "shared_release_hash": "2" * 64,
        "dependency_lock_hash": "3" * 64, "current_snapshot_hash": "4" * 64,
        "target_dropin_hash": "5" * 64, "expected_effective_dropin_count": 1,
        "automatic_rollback_on_failure": True}
    with pytest.raises(PermissionError, match="APPROVAL_REQUIRED"):
        c._activate_approved("appr_" + "0" * 32, activation)
    rollback = {"snapshot_id": "snap_" + "a" * 32, "snapshot_hash": "6" * 64}
    with pytest.raises(PermissionError, match="APPROVAL_REQUIRED"):
        c._rollback_approved("appr_" + "0" * 32, rollback)


def test_failed_activation_uses_only_preapproved_automatic_rollback(tmp_path):
    p = _policy(tmp_path); release = p.release_root / "fixture-release-r69"
    (release / "scripts/nova").mkdir(parents=True)
    (release / "scripts/nova/nova_telegram_worker.py").write_text("fixture")
    class FixtureControl(hc.HostControl):
        def inspect(self, *_args):
            return {"present": True, "mismatches": [], "read_only": True}
        def _validate_approval(self, *_args):
            return ({}, Path("approval-fixture"))
        def _consume_approval(self, *_args):
            return None
        def _snapshot_by_hash(self, _digest):
            return {"snapshot_id": "snap_" + "1" * 32, "snapshot_hash": "d" * 64,
                    "configuration_hash": "same-config"}
        def snapshot_validate(self, _snapshot_id):
            return {"valid": True}
        def snapshot(self):
            return {"snapshot_id": "snap_" + "2" * 32}
        def _load_snapshot(self, _snapshot_id):
            return {"snapshot_id": "snap_" + "2" * 32, "configuration_hash": "same-config"}
        def _shared_dependency(self, _name, _hash):
            return (tmp_path / "shared", "c" * 64)
        def _systemctl(self, *_args):
            return "MainPID=100\n"
        def _disable_current_dropins(self, _deployment_id):
            p.dropin_root.mkdir(parents=True, exist_ok=True)
        def _systemctl_mutation(self, _operation):
            return ""
        def verify(self, *_args):
            return {"pass": False, "main_pid": "101"}
        def _restore_snapshot(self, _snapshot, restart=True):
            return {"pass": True, "poller_count": 1, "mutations": ["snapshot_restore", "restart"]}
        def _receipt(self, operation, payload):
            return {"operation": operation, **payload}
    args = {"deployment_id": "deploy_" + "e" * 32,
        "target_release_name": "fixture-release-r69", "target_release_hash": "a" * 64,
        "shared_release_hash": "b" * 64, "dependency_lock_hash": "c" * 64,
        "current_snapshot_hash": "d" * 64,
        "target_dropin_hash": _sha(hc._dropin_content(release, tmp_path / "shared")),
        "expected_effective_dropin_count": 1, "automatic_rollback_on_failure": True}
    outcome = FixtureControl(p)._activate_approved("appr_" + "f" * 32, args)
    assert outcome["status"] == "FAILED_ROLLED_BACK"
    assert outcome["receipt"]["rollback_performed"] is True


def test_target_dependency_lock_pins_one_verified_shared_release(tmp_path):
    p = _policy(tmp_path); shared_name = "nexus-capability-actions-r68-platform"
    shared = p.release_root / shared_name; (shared / "scripts/nexus_agent_platform").mkdir(parents=True)
    (shared / "scripts/nexus_agent_platform/common.py").write_text("pass\n")
    shared_hash = _manifest(shared); _make_readonly(shared)
    target = p.release_root / "fixture-release-r69"; target.mkdir(parents=True)
    lock = {"source_release": shared_name, "source_release_hash": shared_hash,
            "source_release_manifest_sha256": shared_hash}
    lock_bytes = (json.dumps(lock, sort_keys=True, indent=2) + "\n").encode()
    (target / "NOVA_SHARED_DEPENDENCIES.json").write_bytes(lock_bytes)
    found, lock_hash = hc.HostControl(p)._shared_dependency(target.name, shared_hash)
    assert found == shared and lock_hash == _sha(lock_bytes)
    with pytest.raises(ValueError, match="SHARED_RELEASE_NOT_PINNED"):
        hc.HostControl(p)._shared_dependency(target.name, "0" * 64)


def test_stale_approval_rejected(tmp_path):
    p = _policy(tmp_path); binding = {"artifact_id": "x"}
    aid = _write_approval(p, "STAGE", binding, consumed=True)
    with pytest.raises(PermissionError, match="APPROVAL_BINDING_MISMATCH_OR_STALE"):
        hc.HostControl(p)._consume_approval(aid, "STAGE", binding)


def test_activation_rejects_configuration_changed_after_snapshot(tmp_path):
    p = _policy(tmp_path)
    class StaleControl(hc.HostControl):
        def _validate_approval(self, *_args): return ({}, Path("approval-fixture"))
        def inspect(self, *_args): return {"present": True, "mismatches": [], "read_only": True}
        def _snapshot_by_hash(self, _digest):
            return {"snapshot_id": "snap_" + "1" * 32, "snapshot_hash": "c" * 64,
                    "configuration_hash": "config-before"}
        def snapshot_validate(self, _snapshot_id): return {"valid": True}
        def snapshot(self): return {"snapshot_id": "snap_" + "2" * 32}
        def _load_snapshot(self, _snapshot_id): return {"configuration_hash": "config-after"}
    args = {"deployment_id": "deploy_" + "d" * 32, "target_release_name": "fixture-release-r69",
        "target_release_hash": "a" * 64, "shared_release_hash": "b" * 64,
        "dependency_lock_hash": "c" * 64, "current_snapshot_hash": "d" * 64,
        "target_dropin_hash": "e" * 64, "expected_effective_dropin_count": 1,
        "automatic_rollback_on_failure": True}
    with pytest.raises(ValueError, match="CURRENT_NOVA_SNAPSHOT_STALE"):
        StaleControl(p)._activate_approved("appr_" + "f" * 32, args)


def test_arbitrary_service_path_and_shell_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="SERVICE_POLICY_FIXED"):
        hc.Policy(service="research.service")
    with pytest.raises(ValueError, match="PATH_POLICY_FIXED"):
        hc.Policy(release_root=Path("/tmp"))
    p = _policy(tmp_path); c = hc.HostControl(p)
    with pytest.raises(ValueError, match="CAPABILITY_NOT_ALLOWED"):
        c.invoke("systems.oracle.nova.status", {"command": "systemctl restart hermes"})
    assert hc.PRODUCTION_SERVICE == "nova-telegram-oracle.service"
    assert hc.CERTIFICATION_SERVICE == "nova-release-lifecycle-cert.service"


def test_approval_contract_is_hash_bound_and_auto_rollback_is_explicit():
    args = {"target_release_hash": "a" * 64, "shared_release_hash": "b" * 64,
            "dependency_lock_hash": "c" * 64, "current_snapshot_hash": "d" * 64,
            "target_dropin_hash": "e" * 64, "service_target": hc.PRODUCTION_SERVICE,
            "expected_effective_dropin_count": 1, "automatic_rollback_on_failure": True}
    assert hc._json_hash(args) != hc._json_hash({**args, "target_release_hash": "f" * 64})
    assert "automatic_rollback_on_failure" in hc.SCHEMAS["systems.oracle.nova.activate"][0]


def test_release_name_validation_rejects_traversal_and_absolute_path():
    for value in ("../nova", "/home/opc/.nexus/releases/x", "foo/../bar"):
        with pytest.raises(ValueError):
            hc._safe_name(value, hc.RELEASE_NAME_RE, "bad")


def test_local_server_is_unix_only_and_socket_mode_fixed(tmp_path):
    p = _policy(tmp_path)
    sock = Path("/tmp") / ("hc-" + os.urandom(6).hex() + ".sock")
    server = hc.LocalServer(hc.HostControl(p), sock)
    try:
        assert isinstance(server, hc.socketserver.UnixStreamServer)
        assert os.stat(sock).st_mode & 0o777 == 0o600
    finally:
        server.server_close(); sock.unlink()


def test_local_typed_client_uses_only_the_fixed_unix_socket(tmp_path, monkeypatch):
    p = _policy(tmp_path); sock = Path("/tmp") / ("hc-call-" + os.urandom(6).hex() + ".sock")
    monkeypatch.setattr(hc, "SOCKET_PATH", sock)
    server = hc.LocalServer(hc.HostControl(p), sock)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        result = hc.invoke_local({"capability": "systems.oracle.receipt.read",
                                  "arguments": {"receipt_id": "hcr_" + "0" * 32}})
        assert result["ok"] is True and result["result"]["status"] == "NOT_FOUND"
    finally:
        server.shutdown(); thread.join(timeout=2); server.server_close(); sock.unlink()
