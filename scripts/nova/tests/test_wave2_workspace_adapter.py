"""Disposable contract fixtures for bounded internal NOTE/FILE workspace actions."""
from __future__ import annotations

import hashlib
from pathlib import Path
import pytest

from services.nexus_mcp import server


def test_note_create_and_read_use_exact_path_and_independent_postcondition(tmp_path, monkeypatch):
    artifact_root = tmp_path / "repo"
    receipt_root = tmp_path / "receipts"
    monkeypatch.setattr(server, "_WORKSPACE_ARTIFACT_ROOT", artifact_root)
    monkeypatch.setattr(server, "_WORKSPACE_READ_ROOTS", (artifact_root.resolve(),))
    monkeypatch.setattr(server, "RECEIPT_DIR", receipt_root)
    monkeypatch.setattr(server, "authorize_read", lambda _name: None)

    relative_path = "reports/nova_internal/nova_note_fixture.md"
    content = "Phase 4 live test,"
    created = server._write_workspace_artifact(relative_path, content)
    assert created["status"] == "created"
    assert created["created"] is True
    assert created["path"] == relative_path
    assert created["sha256"] == hashlib.sha256(content.encode()).hexdigest()
    assert "receipt" not in created  # exercise postcondition fallback without a receipt

    readback = server._read_workspace_file(relative_path)
    assert readback["status"] == "ok"
    assert readback["path"] == relative_path
    assert readback["content"] == content
    assert readback["sha256"] == created["sha256"]
    assert readback["receipt"]
    assert (artifact_root / relative_path).is_file()
    assert len(list(receipt_root.glob("*.json"))) == 1


def test_workspace_artifact_create_is_idempotent_by_exact_path(tmp_path, monkeypatch):
    artifact_root = tmp_path / "repo"
    monkeypatch.setattr(server, "_WORKSPACE_ARTIFACT_ROOT", artifact_root)
    relative_path = "reports/nova_internal/nova_note_fixture.md"
    first = server._write_workspace_artifact(relative_path, "one")
    second = server._write_workspace_artifact(relative_path, "one")
    assert first["created"] is True
    assert second["status"] == "conflict"
    assert second["created"] is False
    assert (artifact_root / relative_path).read_text() == "one"


def test_workspace_update_requires_same_entity_and_current_hash(tmp_path, monkeypatch):
    artifact_root = tmp_path / "repo"
    receipt_root = tmp_path / "receipts"
    monkeypatch.setattr(server, "_WORKSPACE_ARTIFACT_ROOT", artifact_root)
    monkeypatch.setattr(server, "_WORKSPACE_READ_ROOTS", (artifact_root.resolve(),))
    monkeypatch.setattr(server, "RECEIPT_DIR", receipt_root)
    monkeypatch.setattr(server, "authorize_read", lambda _name: None)

    relative_path = "reports/nova_internal/nova_note_fixture.md"
    original = "Phase 4 live test,"
    updated = "Phase 4 live test passed,"
    created = server._write_workspace_artifact(relative_path, original)
    result = server._update_workspace_artifact(relative_path, updated, created["sha256"],
                                                note_id=relative_path)
    assert result["status"] == "updated"
    assert result["updated"] is True
    assert result["created"] is False
    assert result["path"] == relative_path
    assert result["previous_sha256"] == created["sha256"]
    readback = server._read_workspace_file(relative_path)
    assert readback["status"] == "ok"
    assert readback["path"] == relative_path
    assert readback["content"] == updated
    assert readback["sha256"] == result["sha256"]
    assert len(list(artifact_root.rglob("nova_note_fixture.md"))) == 1


def test_workspace_update_rejects_stale_hash_or_replacement_entity(tmp_path, monkeypatch):
    artifact_root = tmp_path / "repo"
    monkeypatch.setattr(server, "_WORKSPACE_ARTIFACT_ROOT", artifact_root)
    relative_path = "reports/nova_internal/nova_note_fixture.md"
    created = server._write_workspace_artifact(relative_path, "original")

    stale = server._update_workspace_artifact(relative_path, "wrong", "0" * 64, note_id=relative_path)
    mismatch = server._update_workspace_artifact(relative_path, "wrong", created["sha256"],
                                                 note_id="reports/nova_internal/other.md")
    assert stale["status"] == "conflict"
    assert stale["updated"] is False
    assert mismatch["status"] == "rejected"
    assert mismatch["error"] == "workspace_entity_path_mismatch"
    assert (artifact_root / relative_path).read_text() == "original"


def test_workspace_update_rejects_symlinked_target(tmp_path, monkeypatch):
    artifact_root = tmp_path / "repo"
    artifact_root.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("protected", encoding="utf-8")
    target = artifact_root / "reports/nova_internal/linked.md"
    target.parent.mkdir(parents=True)
    target.symlink_to(outside)
    monkeypatch.setattr(server, "_WORKSPACE_ARTIFACT_ROOT", artifact_root)
    result = server._update_workspace_artifact("reports/nova_internal/linked.md", "changed",
                                                "0" * 64,
                                                note_id="reports/nova_internal/linked.md")
    assert result["status"] == "rejected"
    assert "workspace_artifact_path_outside_approved_scope" in result["error"] or result["error"] == "workspace_symlink_update_denied"
    assert outside.read_text(encoding="utf-8") == "protected"


def test_missing_write_receipt_recovers_from_same_path_readback(tmp_path, monkeypatch):
    artifact_root = tmp_path / "repo"
    receipt_root = tmp_path / "receipts"
    monkeypatch.setattr(server, "_WORKSPACE_ARTIFACT_ROOT", artifact_root)
    monkeypatch.setattr(server, "_WORKSPACE_READ_ROOTS", (artifact_root.resolve(),))
    monkeypatch.setattr(server, "RECEIPT_DIR", receipt_root)
    monkeypatch.setattr(server, "authorize_read", lambda _name: None)
    relative_path = "reports/nova_internal/nova_note_recovery.md"
    created = server._write_workspace_artifact(relative_path, "verified despite missing receipt")
    assert created.get("receipt") is None
    readback = server._read_workspace_file(relative_path)
    assert readback["status"] == "ok"
    assert readback["content"] == "verified despite missing receipt"
    assert readback["sha256"] == created["sha256"]
    retry = server._write_workspace_artifact(relative_path, "verified despite missing receipt")
    assert retry["status"] == "conflict"
    assert len(list(artifact_root.rglob("nova_note_recovery.md"))) == 1


def test_invalid_path_and_unavailable_exact_mutations_fail_closed(tmp_path, monkeypatch):
    artifact_root = tmp_path / "repo"
    monkeypatch.setattr(server, "_WORKSPACE_ARTIFACT_ROOT", artifact_root)
    try:
        server._write_workspace_artifact("reports/nova_internal/../../outside.txt", "no")
    except (ValueError, PermissionError):
        pass
    else:
        raise AssertionError("path traversal must be rejected")
    assert not artifact_root.exists()

    try:
        server._write_workspace_artifact("data/runtime/nova_artifacts/outside_runtime.txt", "no")
    except PermissionError as exc:
        assert "workspace_write_root_not_allowlisted" in str(exc)
    else:
        raise AssertionError("read-only data/runtime must not be a write location")
    assert not (artifact_root / "data/runtime/nova_artifacts/outside_runtime.txt").exists()

    from nova.operator_shadow import decide_wave2_action
    invalid_target = decide_wave2_action("Update that same note")
    assert invalid_target["ERROR_CODE"] == "EXACT_ENTITY_REQUIRED"
    assert invalid_target["CREATE_NEW_ENTITY"] is False
    assert invalid_target["SIDE_EFFECTS"] == 0


def test_transient_create_failure_retries_same_path_without_duplicate(tmp_path, monkeypatch):
    artifact_root = tmp_path / "repo"
    monkeypatch.setattr(server, "_WORKSPACE_ARTIFACT_ROOT", artifact_root)
    relative_path = "reports/nova_internal/nova_note_retry.md"
    original_write = server._write_workspace_artifact
    attempts = {"count": 0}

    def flaky_write(path, content):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise TimeoutError("simulated transient timeout before commit")
        return original_write(path, content)

    monkeypatch.setattr(server, "_write_workspace_artifact", flaky_write)
    try:
        server._write_workspace_artifact(relative_path, "same request")
    except TimeoutError:
        pass
    else:
        raise AssertionError("first attempt should time out")
    success = server._write_workspace_artifact(relative_path, "same request")
    assert success["created"] is True
    assert attempts["count"] == 2
    assert len(list(artifact_root.rglob("nova_note_retry.md"))) == 1


@pytest.mark.parametrize("entity_type,entity_id", [
    ("NOTE", "reports/nova_internal/nova_note_lifecycle.md"),
    ("FILE", "reports/nova_internal/nova_file_lifecycle.txt"),
])
def test_complete_bounded_crud_lifecycle_preserves_one_exact_entity(tmp_path, monkeypatch, entity_type, entity_id):
    root = tmp_path / "repo"
    receipts = tmp_path / "receipts"
    monkeypatch.setattr(server, "_WORKSPACE_ARTIFACT_ROOT", root)
    monkeypatch.setattr(server, "_WORKSPACE_READ_ROOTS", (root.resolve(),))
    monkeypatch.setattr(server, "RECEIPT_DIR", receipts)
    monkeypatch.setattr(server, "authorize_read", lambda _name: None)
    key = "note_id" if entity_type == "NOTE" else "file_id"
    created = server._write_workspace_artifact(entity_id, "first")
    assert created["status"] == "created"
    assert server._write_workspace_artifact(entity_id, "replacement")["status"] == "conflict"
    assert server._read_workspace_file(entity_id)["content"] == "first"
    updated = server._update_workspace_artifact(entity_id, "second", created["sha256"], **{key: entity_id})
    assert updated["status"] == "updated" and updated["created"] is False
    assert server._read_workspace_file(entity_id)["content"] == "second"
    stale = server._delete_workspace_artifact(entity_id, created["sha256"], **{key: entity_id})
    assert stale["status"] == "conflict" and stale["deleted"] is False
    deleted = server._delete_workspace_artifact(entity_id, updated["sha256"], **{key: entity_id})
    assert deleted["status"] == "deleted" and deleted["deleted"] is True
    assert server._read_workspace_file(entity_id)["status"] == "not_found"
    assert server._delete_workspace_artifact(entity_id, updated["sha256"], **{key: entity_id})["status"] == "not_found"
    assert list(root.rglob(Path(entity_id).name)) == []


def test_delete_fails_closed_for_missing_stale_directory_traversal_and_malformed_lineage(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    monkeypatch.setattr(server, "_WORKSPACE_ARTIFACT_ROOT", root)
    path = "reports/nova_internal/delete_guard.md"
    missing = server._delete_workspace_artifact(path, "0" * 64, note_id=path)
    assert missing["status"] == "not_found"
    created = server._write_workspace_artifact(path, "kept")
    assert server._delete_workspace_artifact(path, "0" * 64, note_id=path)["status"] == "conflict"
    assert server._delete_workspace_artifact(path, created["sha256"], file_id="other")["status"] == "rejected"
    assert server._delete_workspace_artifact("reports/nova_internal/../../outside", created["sha256"], note_id="reports/nova_internal/../../outside")["status"] == "rejected"
    directory = "reports/nova_internal/directory"
    (root / directory).mkdir(parents=True)
    assert server._delete_workspace_artifact(directory, "0" * 64, note_id=directory)["status"] == "rejected"
    assert (root / path).read_text(encoding="utf-8") == "kept"
