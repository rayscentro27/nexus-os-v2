"""Focused Research State v2 persistence contracts; run only behind recovery gate."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from research import proactive_research_memory as memory
from research import research_state_v2 as state
from research import research_case_engine as cases


def _isolated(monkeypatch, tmp_path: Path):
    root = tmp_path / "cert"
    monkeypatch.setenv("NEXUS_CERTIFICATION_RESEARCH_STATE_ROOT", str(root))
    monkeypatch.setenv("NEXUS_RESEARCH_STATE_ROOT", str(root))
    monkeypatch.delenv("NEXUS_PRODUCTION_RESEARCH_STATE_ROOT", raising=False)
    return root


def _row(case_id="case-test"):
    return {"memory_id": case_id, "case_id": case_id, "memory_kind": "RESEARCH_CASE",
            "objective_id": "objective-test", "project_id": "project-test", "job_id": "job-test",
            "status": "PROMISING", "turn": 2, "open_questions": [{"question_id": "q1", "status": "OPEN"}],
            "source_count": 1, "finding_count": 1, "needle_status": "NOT_RUN",
            "latest_synthesis_ref": "syn-1", "recorded_at": "2026-10-22T00:00:00+00:00"}


def test_current_state_write_succeeds_without_legacy_ledger(monkeypatch, tmp_path):
    _isolated(monkeypatch, tmp_path)
    monkeypatch.setattr(memory.persistence, "append_record", lambda *a, **k: pytest.fail("legacy append"))
    monkeypatch.setattr(memory.state_v2, "_append_event", lambda event, target_hint=None: str(tmp_path / "history.jsonl"))
    result = memory.persist_state(_row())
    assert result["state_v2_receipt"]["status"] == "COMMITTED"
    assert not (tmp_path / "legacy.jsonl").exists()


def test_history_event_writes_daily_partition(monkeypatch, tmp_path):
    root = _isolated(monkeypatch, tmp_path)
    event = state._event_for(_row(), "CASE_UPDATED")
    path = Path(state._append_event(event))
    assert path.is_relative_to(root / "history" / "research")
    assert path.name.startswith("2026-10-22")
    manifest = json.loads(path.with_suffix(path.suffix + ".manifest.json").read_text())
    assert manifest["record_count"] == 1
    assert manifest["size_bytes"] == path.stat().st_size
    assert manifest["chain_sha256"]


def test_exact_case_lookup_does_not_touch_legacy_ledger(monkeypatch):
    monkeypatch.setattr(state, "lookup_case_control", lambda identity: {"case_id": identity})
    monkeypatch.setattr(memory.persistence, "read_records", lambda *a, **k: pytest.fail("legacy scan"))
    assert cases.get_case_control("case-test")["case_id"] == "case-test"


def test_latest_cases_uses_current_state(monkeypatch):
    row = {**_row(), "case_schema_version": "nexus.research-case.v1"}
    monkeypatch.setattr(state, "list_current", lambda **kwargs: [row])
    monkeypatch.setattr(cases.persistence, "read_records", lambda *args, **kwargs: pytest.fail("legacy read"))
    assert cases._latest_cases()[0]["case_id"] == "case-test"


def test_proactive_memory_reads_current_state(monkeypatch):
    sentinel = [{"memory_kind": "PROACTIVE_QUERY", "query_id": "q1"}]
    monkeypatch.setattr(state, "list_current", lambda **kwargs: sentinel)
    monkeypatch.setattr(memory.persistence, "collection_path", lambda *a: pytest.fail("legacy tail"))
    assert memory._read_recent_states() == sentinel


def test_certification_store_and_history_are_isolated(monkeypatch, tmp_path):
    root = _isolated(monkeypatch, tmp_path)
    monkeypatch.setattr(state, "_append_event", lambda event, target_hint=None: str(state._archive_root() / "2026" / "10" / "2026-10-22.jsonl"))
    state.persist_state(_row())
    with sqlite3.connect(root / "current" / "research_state_v2.sqlite3") as db:
        assert db.execute("select count(*) from current_state").fetchone()[0] == 1
    assert state._archive_root() == root / "history" / "research"


def test_seed_activation_is_idempotent_and_preserves_phase5(monkeypatch, tmp_path):
    _isolated(monkeypatch, tmp_path)
    seed_dir = tmp_path / "migration"
    seed_dir.mkdir()
    seed = {"created_at": "2026-10-22T00:00:00+00:00", "cases": [{"case_id": "rcase_f6c19e2c0afe9c44ea",
        "objective_id": "nova_research_16a764a4c75b65d81e46", "project_id": "nova_research_work_16a764a4c75b65d81e46",
        "job_id": "job_d27d3093c0e248a3a1481a5a45730475", "case_status": "PROMISING", "current_turn": 7,
        "open_questions": ["q_b04da13aa3b1464f", "q_b42074818a3af0a5"]}]}
    (seed_dir / "hot_state_seed.json").write_text(json.dumps(seed))
    (seed_dir / "selective_preservation_manifest.json").write_text(json.dumps({"retained_items": [
        {"CASE_ID": "rcase_f6c19e2c0afe9c44ea", "TYPE": "RESEARCH_CASE", "CLASS": "A"}], "EXCLUDED_FROM_STATE_V2_IMPORT": []}))
    monkeypatch.setattr(state, "_append_event", lambda _event, target_hint=None: "history-partition")
    result = state.activate_seed(seed_dir / "hot_state_seed.json")
    assert result["imported"] == 1
    stored = state.lookup_case("rcase_f6c19e2c0afe9c44ea")
    assert stored["objective_id"] == "nova_research_16a764a4c75b65d81e46"
    assert stored["turn"] == 7
    assert state.activate_seed(seed_dir / "hot_state_seed.json")["imported"] == 0


def test_current_state_failure_emits_recovery_event(monkeypatch, tmp_path):
    _isolated(monkeypatch, tmp_path)
    monkeypatch.setattr(state, "_upsert_current", lambda row: (_ for _ in ()).throw(state.CurrentStateUnavailable("offline")))
    events = []
    monkeypatch.setattr(state, "_emit_failure", lambda code, row, detail: events.append(code))
    with pytest.raises(state.CurrentStateUnavailable): state.persist_state(_row())
    assert "CURRENT_STATE_WRITE_FAILED" in events
    assert "RECONCILIATION_REQUIRED" in events


def test_history_failure_leaves_replayable_intent(monkeypatch, tmp_path):
    _isolated(monkeypatch, tmp_path)
    monkeypatch.setattr(state, "_append_event", lambda event, target_hint=None: (_ for _ in ()).throw(state.HistoryPartitionFailure("disk")))
    monkeypatch.setattr(state, "_upsert_current", lambda row: {"status": "PASS", "verified": True})
    monkeypatch.setattr(state, "_emit_failure", lambda *a: None)
    with pytest.raises(state.HistoryPartitionFailure): state.persist_state(_row())
    assert list((tmp_path / "cert" / "state_v2" / "pending").glob("*.json"))


def test_pending_intent_is_detected_and_reconciled(monkeypatch, tmp_path):
    _isolated(monkeypatch, tmp_path)
    row = state._bounded_record({**_row(), "memory_id": "case-test"})
    event = state._event_for(row)
    pending = {"event_id": event["event_id"], "current_state": row, "history_event": event}
    state._atomic_write(state._pending_path(event["event_id"]), json.dumps(pending).encode())
    monkeypatch.setattr(state, "_upsert_current", lambda value: {"status": "PASS", "verified": True})
    monkeypatch.setattr(state, "_append_event", lambda value, target_hint=None: "history-partition")
    monkeypatch.setattr(state, "_emit_failure", lambda *a: None)
    assert state.detect_divergence()["reconciliation_required"] is True
    assert state.reconcile_pending()["processed"] == 1
    assert state.detect_divergence()["consistent"] is True


def test_partition_rotation_uses_numbered_bounded_segments(monkeypatch, tmp_path):
    root = _isolated(monkeypatch, tmp_path)
    first_event = state._event_for(_row())
    second_event = state._event_for({**_row(), "recorded_at": "2026-10-22T00:00:01+00:00"})
    size = len((json.dumps(first_event, separators=(",", ":")) + "\n").encode())
    monkeypatch.setattr(state, "MAX_HISTORY_PARTITION_BYTES", size + 1)
    first = state._append_event(first_event)
    second = state._append_event(second_event)
    assert first.endswith("2026-10-22.jsonl")
    assert second.endswith("2026-10-22.0001.jsonl")
    assert Path(first).is_relative_to(root / "history" / "research")


def _full_partition_family(monkeypatch, tmp_path, *, segment_count, capacity):
    root = _isolated(monkeypatch, tmp_path)
    monkeypatch.setattr(state, "MAX_HISTORY_PARTITION_BYTES", capacity)
    base = root / "history" / "research" / "2026" / "10"
    base.mkdir(parents=True)
    day = "2026-10-22"
    for number in range(segment_count):
        suffix = "" if number == 0 else f".{number:04d}"
        target = base / f"{day}{suffix}.jsonl"
        target.write_bytes(b"x" * capacity)
        target.with_suffix(target.suffix + ".manifest.json").write_text(json.dumps({
            "partition_id": target.stem, "size_bytes": capacity,
            "record_count": 1, "chain_sha256": "fixture", "last_event_id": "fixture"}))
    if segment_count:
        (base / f"{day}.segments.json").write_text(json.dumps({
            "schema_version": "nexus.research-history-segments.v1", "partition_date": day,
            "latest_segment": 0, "latest_partition_id": f"{day}.jsonl",
            "latest_size_bytes": capacity}))
    return root, base, day


def test_segment_selection_uses_current_segment_with_capacity(monkeypatch, tmp_path):
    root = _isolated(monkeypatch, tmp_path)
    event = state._event_for(_row())
    first = Path(state._append_event(event))
    next_event = state._event_for({**_row(), "recorded_at": "2026-10-22T00:00:01+00:00"})
    assert state._partition_for_event(next_event, 100) == first
    assert (first.parent / "2026-10-22.segments.json").exists()
    assert first.is_relative_to(root / "history" / "research")


def test_segment_selection_uses_next_segment_when_current_is_full(monkeypatch, tmp_path):
    event = state._event_for(_row())
    encoded_size = len((json.dumps(event, separators=(",", ":")) + "\n").encode())
    _, base, day = _full_partition_family(monkeypatch, tmp_path, segment_count=1, capacity=encoded_size)
    selected = state._partition_for_event(event, encoded_size)
    assert selected == base / f"{day}.0001.jsonl"


def test_segment_selection_fails_closed_when_segment_manifest_missing(monkeypatch, tmp_path):
    root = _isolated(monkeypatch, tmp_path)
    base = root / "history" / "research" / "2026" / "10"
    base.mkdir(parents=True)
    (base / "2026-10-22.jsonl").write_text("partial")
    with pytest.raises(state.HistoryPartitionFailure, match="SEGMENT_MANIFEST_MISSING"):
        state._partition_for_event(state._event_for(_row()), 100)


def test_segment_selection_fails_closed_on_stale_segment_manifest(monkeypatch, tmp_path):
    root = _isolated(monkeypatch, tmp_path)
    base = root / "history" / "research" / "2026" / "10"
    base.mkdir(parents=True)
    target = base / "2026-10-22.jsonl"
    target.write_text("data")
    target.with_suffix(target.suffix + ".manifest.json").write_text(json.dumps({
        "partition_id": target.stem, "size_bytes": 99}))
    with pytest.raises(state.HistoryPartitionFailure, match="SEGMENT_MANIFEST_STALE"):
        state._partition_for_event(state._event_for(_row()), 100)


def test_segment_selection_fails_on_missing_hinted_candidate(monkeypatch, tmp_path):
    root = _isolated(monkeypatch, tmp_path)
    base = root / "history" / "research" / "2026" / "10"
    base.mkdir(parents=True)
    (base / "2026-10-22.segments.json").write_text(json.dumps({
        "partition_date": "2026-10-22", "latest_segment": 2}))
    with pytest.raises(state.HistoryPartitionFailure, match="SELECTION_EXHAUSTED"):
        state._partition_for_event(state._event_for(_row()), 100)


def test_segment_selection_exhausts_after_configured_probe_bound(monkeypatch, tmp_path):
    event = state._event_for(_row())
    encoded_size = len((json.dumps(event, separators=(",", ":")) + "\n").encode())
    _, _, _ = _full_partition_family(monkeypatch, tmp_path,
        segment_count=state.MAX_HISTORY_SEGMENT_PROBES, capacity=encoded_size)
    with pytest.raises(state.HistoryPartitionFailure, match="probe_limit=4"):
        state._partition_for_event(event, encoded_size)


def test_segment_selection_exhaustion_emits_event_and_preserves_pending(monkeypatch, tmp_path):
    event = state._event_for(state._bounded_record(_row()))
    encoded_size = len((json.dumps(event, separators=(",", ":")) + "\n").encode())
    _full_partition_family(monkeypatch, tmp_path,
        segment_count=state.MAX_HISTORY_SEGMENT_PROBES, capacity=encoded_size)
    emitted = []
    monkeypatch.setattr(state, "_emit_failure", lambda code, row, detail: emitted.append((code, detail)))
    with pytest.raises(state.HistoryPartitionFailure, match="SELECTION_EXHAUSTED"):
        state.persist_state(_row())
    pending = list((tmp_path / "cert" / "state_v2" / "pending").glob("*.json"))
    assert pending
    assert any(code == "HISTORY_PARTITION_SELECTION_EXHAUSTED" for code, _ in emitted)
    assert any(code == "RECONCILIATION_REQUIRED" for code, _ in emitted)


def test_segment_selection_does_not_enumerate_partition_directory(monkeypatch, tmp_path):
    _isolated(monkeypatch, tmp_path)
    monkeypatch.setattr(Path, "iterdir", lambda self: pytest.fail("full partition enumeration"))
    monkeypatch.setattr(Path, "glob", lambda self, pattern: pytest.fail("partition glob scan"))
    state._partition_for_event(state._event_for(_row()), 100)


def test_segment_selection_never_exceeds_probe_limit(monkeypatch, tmp_path):
    event = state._event_for(_row())
    encoded_size = len((json.dumps(event, separators=(",", ":")) + "\n").encode())
    _full_partition_family(monkeypatch, tmp_path,
        segment_count=state.MAX_HISTORY_SEGMENT_PROBES + 2, capacity=encoded_size)
    inspected = []
    original = state._validated_segment_size
    def counted(path):
        inspected.append(path)
        return original(path)
    monkeypatch.setattr(state, "_validated_segment_size", counted)
    with pytest.raises(state.HistoryPartitionFailure, match="SELECTION_EXHAUSTED"):
        state._partition_for_event(event, encoded_size)
    assert len(inspected) == state.MAX_HISTORY_SEGMENT_PROBES


def test_archive_access_requires_explicit_date_and_limit(monkeypatch, tmp_path):
    root = _isolated(monkeypatch, tmp_path)
    path = root / "history/research/2026/10/2026-10-22.jsonl"
    path.parent.mkdir(parents=True)
    event = state._event_for(_row())
    path.write_text(json.dumps(event, separators=(",", ":")) + "\n")
    assert [x["event_id"] for x in state.explicit_archive_events(day="2026-10-22", purpose="test", max_records=1)] == [event["event_id"]]
    with pytest.raises(ValueError): state.explicit_archive_events(day="all", purpose="test")


def test_lineage_lookup_uses_bounded_exact_hydration(monkeypatch):
    monkeypatch.setattr(state, "_certification", lambda: False)
    class Client:
        def configured(self): return True
        def rest(self, method, path):
            if "select=memory_id%2Cpayload" in path or "select=memory_id,payload" in path:
                return 200, [{"memory_id": "case-test", "payload": _row()}]
            if "select=memory_id" in path: return 200, [{"memory_id": "case-test"}]
            raise AssertionError(f"unexpected lineage query: {path}")
    monkeypatch.setattr(state, "supabase", Client())
    assert state.lookup_lineage("project_id", "project-test")[0]["case_id"] == "case-test"


def test_legacy_recovery_requires_explicit_flag(monkeypatch):
    monkeypatch.setattr(memory, "hydrate_memory", lambda _case: None)
    monkeypatch.setattr(cases, "_emit_current_state_lookup_unavailable", lambda case: {"event_id": "evt"})
    monkeypatch.setattr(cases.persistence, "collection_path", lambda *_: pytest.fail("implicit legacy recovery"))
    with pytest.raises(cases.CurrentStateLookupUnavailable): cases.get_case("case-test")


def test_no_full_archive_scan_or_legacy_write_symbols_in_writer():
    source = Path(state.__file__).read_text()
    assert "read_records(\"research_runtime_states\")" not in source
    assert "append_record(\"research_runtime_states\"" not in source
    assert "explicit_archive_events" in source


def test_case_state_bound_reduces_payload_without_losing_lineage():
    row = _row()
    row["sources"] = [{"source_id": str(i), "body": "x" * 3000, "summary": "s" * 2500} for i in range(150)]
    compact = state._bounded_record(row)
    assert compact["case_id"] == "case-test"
    assert compact["objective_id"] == "objective-test"
    assert len(json.dumps(compact).encode()) <= state.MAX_CURRENT_RECORD_BYTES
