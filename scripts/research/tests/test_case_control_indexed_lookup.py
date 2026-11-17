from __future__ import annotations

import pytest

from research import research_case_engine as engine


class _Remote:
    def __init__(self, status, rows):
        self.status = status
        self.rows = rows

    def configured(self):
        return True

    def rest(self, method, path):
        return self.status, self.rows


def test_case_control_uses_exact_indexed_remote_result_without_ledger_fallback(monkeypatch):
    expected = {"memory_id": "case-1", "case_id": "case-1", "status": "PROMISING"}
    monkeypatch.setattr(engine.research_memory, "supabase", _Remote(200, [expected]))
    monkeypatch.setattr(engine.persistence, "read_records",
                        lambda *_args, **_kwargs: pytest.fail("full ledger fallback must not run"))

    assert engine.get_case_control("case-1") == expected


def test_case_control_unavailable_emits_recovery_event_without_scanning(monkeypatch):
    emitted = []
    def capture(event):
        emitted.append(event)
        return event

    monkeypatch.setattr(engine.research_memory, "supabase", None)
    monkeypatch.setattr(engine.persistence, "read_records",
                        lambda *_args, **_kwargs: pytest.fail("full ledger fallback must not run"))
    monkeypatch.setattr(engine, "_emit_current_state_lookup_unavailable", capture)

    with pytest.raises(engine.CurrentStateLookupUnavailable):
        engine.get_case_control("case-unavailable")
    assert len(emitted) == 1
    assert emitted[0]["error_code"] == "CURRENT_STATE_LOOKUP_UNAVAILABLE"
    assert emitted[0]["case_id"] == "case-unavailable"


def test_get_case_remote_hit_does_not_open_local_ledger(monkeypatch):
    expected = {"memory_id": "case-2", "case_id": "case-2", "status": "PROMISING"}
    monkeypatch.setattr(engine.research_memory, "hydrate_memory", lambda _case_id: expected)
    monkeypatch.setattr(engine.persistence, "collection_path",
                        lambda *_args, **_kwargs: pytest.fail("normal lookup must not open local ledger"))

    assert engine.get_case("case-2") == expected


def test_get_case_unavailable_is_explicit_and_does_not_tail_read(monkeypatch):
    emitted = []
    monkeypatch.setattr(engine.research_memory, "hydrate_memory", lambda _case_id: None)
    monkeypatch.setattr(engine, "_emit_current_state_lookup_unavailable",
                        lambda case_id: emitted.append(case_id) or {"event_id": "event-1"})
    monkeypatch.setattr(engine.persistence, "collection_path",
                        lambda *_args, **_kwargs: pytest.fail("normal lookup must not tail-read local ledger"))

    with pytest.raises(engine.CurrentStateLookupUnavailable):
        engine.get_case("case-unavailable")
    assert emitted == ["case-unavailable"]


def test_get_case_local_tail_is_available_only_when_explicitly_authorized(monkeypatch, tmp_path):
    ledger = tmp_path / "research_runtime_states.jsonl"
    row = {"memory_kind": "RESEARCH_CASE", "case_id": "case-recovery", "recorded_at": "2026-10-22T00:00:00Z"}
    ledger.write_text(__import__("json").dumps(row) + "\n")
    monkeypatch.setattr(engine.research_memory, "hydrate_memory", lambda _case_id: None)
    monkeypatch.setattr(engine.persistence, "collection_path", lambda *_args, **_kwargs: ledger)

    assert engine.get_case("case-recovery", allow_bounded_local_recovery=True) == row


def test_certification_research_namespace_is_separate_from_production():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    config = json.loads((root / "config/certification_research_namespace.v1.json").read_text())
    launcher = (root / config["launcher"]).read_text()
    certification_root = config["state_root"]

    assert config["production_writes_allowed"] is False
    assert config["production_archive_writes_allowed"] is False
    assert certification_root.startswith(str(Path.home() / ".nexus/state/certification/research"))
    assert "NEXUS_CERTIFICATION_RESEARCH_STATE_ROOT" in launcher
    assert "NEXUS_RESEARCH_STATE_ROOT" in launcher
