import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from acceptance_telemetry import AcceptanceSessionWriter, build_acceptance_record, release_identity


def test_acceptance_record_has_complete_required_schema_and_defaults():
    record = build_acceptance_record(
        update_id=101,
        user_message="Tell me a joke.",
        nova_response="A short joke.",
        session_id="acceptance_test_01",
        identity={"active_release": "/release/nova-v1", "active_release_hash": "abc", "code_root": "/release/nova-v1",
                  "process_pid": 42, "process_start_time": "2026-10-29T00:00:00Z"},
        fields={"intent_class": "CASUAL_CONVERSATION", "operation_class": "CONVERSATION"},
    )
    required = {
        "acceptance_session_id", "update_id", "user_message", "nova_response", "processed_at",
        "intent_class", "resolved_capability", "resolved_engine", "operation_class",
        "used_existing_verified_result", "referent_result_id", "request_id", "correlation_id",
        "engine_call_count", "job_id", "new_objective_created", "new_job_created", "mutation_count",
        "approval_required", "receipt_ids", "provenance_refs", "delivery_state",
        "telegram_message_id", "active_release", "active_release_hash", "code_root", "process_pid",
        "process_start_time", "trace_id",
    }
    assert required.issubset(record)
    assert record["engine_call_count"] == 0
    assert record["new_objective_created"] == "NO"
    assert record["new_job_created"] == "NO"
    assert record["mutation_count"] == 0


def test_session_writer_appends_and_reads_only_exact_session_file():
    with tempfile.TemporaryDirectory() as temp:
        writer = AcceptanceSessionWriter(temp)
        row = build_acceptance_record(
            update_id=101, user_message="Hi", nova_response="Hello", session_id="acceptance_test_02",
            identity={}, fields={},
        )
        writer.append(row)
        writer.append({**row, "update_id": "102"})
        assert [item["update_id"] for item in writer.read("acceptance_test_02")] == ["101", "102"]
        assert writer.read("another_session") == []
        assert not list(Path(temp).glob("**/*"))[-1].name.startswith("another_session")


def test_session_writer_rejects_path_like_session_id():
    with tempfile.TemporaryDirectory() as temp:
        writer = AcceptanceSessionWriter(temp)
        try:
            writer.read("../outside")
        except ValueError as exc:
            assert str(exc) == "INVALID_ACCEPTANCE_SESSION_ID"
        else:
            raise AssertionError("path-like session id was accepted")


def test_release_identity_is_fail_closed_when_manifest_is_missing():
    with tempfile.TemporaryDirectory() as temp:
        result = release_identity(Path(temp), code_root="/code", pid=7, process_start_time="unknown")
        assert result["active_release"] == str(Path(temp).resolve())
        assert result["active_release_hash"] == "UNAVAILABLE"
