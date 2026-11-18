from __future__ import annotations

import json
from urllib.parse import parse_qs, urlsplit

from research import proactive_research_memory as memory


def test_normal_memory_read_is_compact_filtered_and_bounded(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(memory.persistence, "collection_path", lambda _name: tmp_path / "missing.jsonl")
    monkeypatch.setattr(memory.supabase, "configured", lambda: True)

    def rest(method, path):
        calls.append((method, path))
        return 200, [{"memory_id": "mem-1", "memory_kind": "PROACTIVE_QUERY", "query": "AI workflow",
                      "run_at": "2026-10-08T12:00:00+00:00", "result_ids": ["source-1"],
                      "payload": {"large": "must not be returned"}}]

    monkeypatch.setattr(memory.supabase, "rest", rest)
    rows = memory._read_recent_states(max_records=20_000)
    method, path = calls[0]
    query = parse_qs(urlsplit(path).query)
    assert method == "GET"
    assert query["limit"] == ["500"]
    assert query["memory_kind"] == ["in.(PROACTIVE_QUERY,PROACTIVE_OBJECTIVE,PROACTIVE_RESEARCH_CASE,REPEAT_QUERY_SKIP)"]
    assert "payload" not in query["select"][0].split(",")
    assert "query:payload->>query" in query["select"][0]
    assert rows[0]["query"] == "AI workflow"
    assert "large" not in json.dumps(rows)


def test_detailed_case_read_is_filtered_and_single_memory_hydration_is_explicit(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(memory.persistence, "collection_path", lambda _name: tmp_path / "missing.jsonl")
    monkeypatch.setattr(memory.supabase, "configured", lambda: True)

    def rest(method, path):
        calls.append((method, path))
        if "memory_id=eq." in path:
            return 200, [{"memory_id": "mem-case-1", "payload": {"case_id": "case-1", "evidence": ["detail"]}}]
        return 200, [{"memory_id": "mem-case-1", "memory_kind": "PROACTIVE_RESEARCH_CASE",
                      "recorded_at": "2026-10-08T12:00:00+00:00",
                      "payload": {"case_id": "case-1", "evidence": ["detail"]}}]

    monkeypatch.setattr(memory.supabase, "rest", rest)
    rows = memory._read_recent_states(max_records=1000, include_full_payload=True)
    case_query = parse_qs(urlsplit(calls[0][1]).query)
    assert case_query["limit"] == ["100"]
    assert case_query["memory_kind"] == ["in.(RESEARCH_CASE,PROACTIVE_RESEARCH_CASE)"]
    assert rows[0]["evidence"] == ["detail"]

    detail = memory.hydrate_memory("mem-case-1")
    hydration_query = parse_qs(urlsplit(calls[1][1]).query)
    assert hydration_query["memory_id"] == ["eq.mem-case-1"]
    assert hydration_query["limit"] == ["1"]
    assert hydration_query["select"] == ["memory_id,recorded_at,payload"]
    assert detail == {"case_id": "case-1", "evidence": ["detail"]}
