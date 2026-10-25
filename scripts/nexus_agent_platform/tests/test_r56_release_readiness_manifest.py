import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone

import pytest

from nexus_agent_platform import stability_supervisor as ss


def _write_release(root: Path, release_id: str, *, base_release_id: str | None = None,
                   payload: bytes = b"runtime") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "runtime.py").write_bytes(payload)
    state_contract = {"STATE_V2_RUNTIME_CERTIFICATION": "PASS",
                      "LEGACY_LEDGER_REQUIRED": "NO"}
    (root / "STATE_V2_RELEASE_CONTRACT.json").write_text(json.dumps(state_contract))
    payloads = {
        "runtime.py": hashlib.sha256(payload).hexdigest(),
        "STATE_V2_RELEASE_CONTRACT.json": hashlib.sha256(
            (root / "STATE_V2_RELEASE_CONTRACT.json").read_bytes()).hexdigest(),
    }
    metadata = {"release_id": release_id, "runtime_file_count": len(payloads),
                "certification": {"result": "PASS"}}
    metadata_path = root / "BUILD_METADATA.json"
    metadata_path.write_text(json.dumps(metadata))
    manifest = {"release_id": release_id, "payload_sha256": payloads,
                "runtime_file_count": len(payloads),
                "build_metadata_sha256": hashlib.sha256(metadata_path.read_bytes()).hexdigest(),
                "certification": {"result": "PASS"}}
    if base_release_id:
        manifest["base_release_id"] = base_release_id
    number = release_id.rsplit("-r", 1)[-1]
    manifest_path = root / f"R{number}_RELEASE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest))
    manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    (root / "RELEASE_MANIFEST.sha256").write_text(
        f"{manifest_hash}  {manifest_path.name}\n")
    return manifest_path


def _set_active(monkeypatch, root: Path):
    monkeypatch.setenv("NEXUS_ACTIVE_RESEARCH_RELEASE", str(root))


def _staged_r56_root() -> Path:
    value = os.environ.get("R56_TEST_ROOT")
    if not value:
        pytest.skip("requires assembled R56 certification runtime")
    return Path(value).resolve()


@pytest.mark.parametrize("release_id", [
    "nexus-capability-actions-20261023-r52",
    "nexus-capability-actions-20261024-r53",
    "nexus-capability-actions-20261024-r55",
    "nexus-capability-actions-20261025-r56",
    "nexus-capability-actions-20991231-r999",
])
def test_generic_root_manifest_resolution_for_r52_r53_r55_r56_and_future(
        tmp_path, monkeypatch, release_id):
    root = tmp_path / release_id
    _write_release(root, release_id)
    _set_active(monkeypatch, root)
    assert ss._active_state_v2_release() == (release_id, True)


def test_r53_declared_base_manifest_is_not_ambiguous(tmp_path, monkeypatch):
    root = tmp_path / "nexus-capability-actions-20261024-r53"
    _write_release(root, "nexus-capability-actions-20261024-r53",
                   base_release_id="nexus-capability-actions-20261023-r52")
    base_id = "nexus-capability-actions-20261023-r52"
    base_path = root / "R52_RELEASE_MANIFEST.json"
    base_path.write_text(json.dumps({"release_id": base_id, "payload_sha256": {},
                                     "certification": {"result": "PASS"}}))
    _set_active(monkeypatch, root)
    assert ss._active_state_v2_release() == ("nexus-capability-actions-20261024-r53", True)


def test_zero_manifests_fails_closed(tmp_path, monkeypatch):
    root = tmp_path / "nexus-capability-actions-20261025-r56"
    root.mkdir()
    (root / "RELEASE_MANIFEST.sha256").write_text("")
    _set_active(monkeypatch, root)
    assert ss._active_state_v2_release() == (None, False)


def test_multiple_current_manifests_fail_closed(tmp_path, monkeypatch):
    root = tmp_path / "nexus-capability-actions-20261025-r56"
    first = _write_release(root, root.name)
    (root / "R056_RELEASE_MANIFEST.json").write_text(first.read_text())
    _set_active(monkeypatch, root)
    assert ss._active_state_v2_release() == (None, False)


def test_release_directory_identity_mismatch_fails_closed(tmp_path, monkeypatch):
    root = tmp_path / "nexus-capability-actions-20261025-r56"
    _write_release(root, "nexus-capability-actions-20261024-r55")
    _set_active(monkeypatch, root)
    assert ss._active_state_v2_release() == (None, False)


def test_malformed_manifest_fails_closed(tmp_path, monkeypatch):
    root = tmp_path / "nexus-capability-actions-20261025-r56"
    root.mkdir()
    (root / "R56_RELEASE_MANIFEST.json").write_text("{")
    (root / "RELEASE_MANIFEST.sha256").write_text("unused")
    _set_active(monkeypatch, root)
    assert ss._active_state_v2_release() == (None, False)


def test_payload_hash_mismatch_fails_closed(tmp_path, monkeypatch):
    root = tmp_path / "nexus-capability-actions-20261025-r56"
    _write_release(root, root.name, payload=b"different")
    (root / "runtime.py").write_bytes(b"tampered")
    _set_active(monkeypatch, root)
    assert ss._active_state_v2_release() == (None, False)


def test_manifest_build_metadata_identity_mismatch_fails_closed(tmp_path, monkeypatch):
    root = tmp_path / "nexus-capability-actions-20261025-r56"
    _write_release(root, root.name)
    metadata_path = root / "BUILD_METADATA.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["release_id"] = "nexus-capability-actions-20261024-r55"
    metadata_path.write_text(json.dumps(metadata))
    _set_active(monkeypatch, root)
    assert ss._active_state_v2_release() == (None, False)


def test_build_metadata_hash_mismatch_fails_closed(tmp_path, monkeypatch):
    root = tmp_path / "nexus-capability-actions-20261025-r56"
    _write_release(root, root.name)
    (root / "BUILD_METADATA.json").write_text("{}")
    _set_active(monkeypatch, root)
    assert ss._active_state_v2_release() == (None, False)


def test_matching_manifest_identity_yields_ready_simulation(tmp_path, monkeypatch):
    root = tmp_path / "nexus-capability-actions-20261025-r56"
    _write_release(root, root.name)
    _set_active(monkeypatch, root)
    identity = ss._active_state_v2_release()
    record = {"schema": ss.STATE_V2_READINESS_SCHEMA,
              "active_release_id": root.name,
              "verified_at": datetime.now(timezone.utc).isoformat(),
              "checks": {name: True for name in ss.STATE_V2_REQUIRED_CHECKS}}
    assert identity == (root.name, True)
    assert ss.evaluate_state_v2_readiness(record, active_release=identity)["status"] == "READY"


def test_nested_manifest_is_not_discovered_and_no_worktree_fallback(monkeypatch, tmp_path):
    monkeypatch.delenv("NEXUS_ACTIVE_RESEARCH_RELEASE", raising=False)
    monkeypatch.setattr(ss, "__file__", str(tmp_path / "checkout/scripts/stability_supervisor.py"))
    nested = tmp_path / "checkout" / "nested"
    _write_release(nested / "nexus-capability-actions-20261025-r56",
                   "nexus-capability-actions-20261025-r56")
    assert ss._active_state_v2_release() == (None, False)


def test_invalid_explicit_release_does_not_fall_back_to_older_module_root(monkeypatch, tmp_path):
    old_root = tmp_path / "nexus-capability-actions-20261024-r53"
    _write_release(old_root, old_root.name)
    monkeypatch.setenv("NEXUS_ACTIVE_RESEARCH_RELEASE", str(tmp_path / "missing-r56"))
    monkeypatch.setattr(ss, "__file__", str(old_root / "scripts/stability_supervisor.py"))
    assert ss._active_state_v2_release() == (None, False)


def test_r56_launcher_owns_its_root_and_has_no_older_release_literal():
    root = _staged_r56_root()
    launcher = root / "scripts/ops/nexus_mcp_bridge.sh"
    body = launcher.read_text()
    assert 'ROOT="$(cd "$SCRIPT_DIR/../.." && pwd -P)"' in body
    assert 'export PYTHONPATH="$ROOT:$ROOT/scripts"' in body
    assert "nexus-capability-actions-20261024-r53" not in body
    assert "nexus-capability-actions-20261024-r55" not in body


def test_r56_worker_import_roots_are_the_current_release(monkeypatch):
    import importlib
    import sys

    root = _staged_r56_root()
    root_text = str(root.resolve())
    monkeypatch.syspath_prepend(str(root / "scripts"))
    monkeypatch.syspath_prepend(str(root))
    for name in ("services.nexus_mcp.http_server", "nexus_agent_platform.job_worker_once",
                 "nexus_agent_platform.stability_supervisor"):
        module = importlib.import_module(name)
        origin = str(Path(module.__file__).resolve())
        assert origin.startswith(root_text + "/")
        assert "nexus-capability-actions-20261024-r53" not in origin
        assert "nexus-capability-actions-20261024-r55" not in origin


def test_packaged_r56_root_is_discovered_without_environment_override(monkeypatch):
    monkeypatch.delenv("NEXUS_ACTIVE_RESEARCH_RELEASE", raising=False)
    root = _staged_r56_root()
    assert ss._active_state_v2_release() == (root.name, True)
