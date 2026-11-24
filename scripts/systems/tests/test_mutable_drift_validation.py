from __future__ import annotations

import hashlib
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/systems"))

from change_target_resolver import _path_identity, post_change_check


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _plan(protected: Path, mutable: Path) -> dict:
    return {
        "scope_mode": "SCOPED_TARGETS",
        "authorized_files": [],
        "baseline_sha256": {},
        "allowed_dependency_files": [],
        "allowed_dependency_sha256": {},
        "prohibited_file_hashes": {str(protected): _file_hash(protected)},
        "mutable_runtime_state": {str(mutable): {
            "identity": _path_identity(str(mutable)),
            "integrity": "PASS",
            "classification": "EXPECTED_MUTABLE_RUNTIME_STATE",
        }},
        "prohibited_path_patterns": [str(protected), str(mutable)],
        "workspace_status_before_paths": [],
        "workspace_status_available": False,
    }


def test_prohibited_configuration_content_change_remains_hard_failure(tmp_path, monkeypatch):
    config = tmp_path / "production.json"
    db = tmp_path / "runtime.sqlite3"
    config.write_text("before")
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE state(value TEXT)")
        con.execute("INSERT INTO state VALUES('before')")
    plan = _plan(config, db)
    config.write_text("unauthorized")
    monkeypatch.setattr("change_target_resolver._git_status", lambda: None)
    result = post_change_check(plan)
    assert result["post_change_drift_check"] == "FAIL"
    assert result["drift_classification"] == "PROHIBITED_TARGET_DRIFT"


def test_mutable_sqlite_content_update_is_expected_but_integrity_checked(tmp_path, monkeypatch):
    config = tmp_path / "production.json"
    db = tmp_path / "runtime.sqlite3"
    config.write_text("stable")
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE state(value TEXT)")
        con.execute("INSERT INTO state VALUES('before')")
    plan = _plan(config, db)
    with sqlite3.connect(db) as con:
        con.execute("INSERT INTO state VALUES('normal runtime update')")
    monkeypatch.setattr("change_target_resolver._git_status", lambda: None)
    result = post_change_check(plan)
    assert result["post_change_drift_check"] == "PASS"
    assert result["mutable_runtime_state"][str(db)]["content_hash_checked"] is False


def test_mutable_sqlite_deletion_or_replacement_fails(tmp_path, monkeypatch):
    config = tmp_path / "production.json"
    db = tmp_path / "runtime.sqlite3"
    replacement = tmp_path / "replacement.sqlite3"
    config.write_text("stable")
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE state(value TEXT)")
    with sqlite3.connect(replacement) as con:
        con.execute("CREATE TABLE replacement(value TEXT)")
    plan = _plan(config, db)
    original_identity = plan["mutable_runtime_state"][str(db)]["identity"]
    db.unlink()
    replacement.replace(db)
    # Keep the old inode alive to make the replacement check deterministic.
    assert original_identity["inode"] != db.stat().st_ino
    monkeypatch.setattr("change_target_resolver._git_status", lambda: None)
    result = post_change_check(plan)
    assert result["post_change_drift_check"] == "FAIL"
    assert any("MUTABLE_STATE_REPLACED_OR_REDIRECTED" in item for item in result["mutable_runtime_state_failures"])


def test_mutable_sqlite_deletion_fails(tmp_path, monkeypatch):
    config = tmp_path / "production.json"
    db = tmp_path / "runtime.sqlite3"
    config.write_text("stable")
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE state(value TEXT)")
    plan = _plan(config, db)
    db.unlink()
    monkeypatch.setattr("change_target_resolver._git_status", lambda: None)
    result = post_change_check(plan)
    assert result["post_change_drift_check"] == "FAIL"
    assert any("MUTABLE_STATE_MISSING" in item for item in result["mutable_runtime_state_failures"])
