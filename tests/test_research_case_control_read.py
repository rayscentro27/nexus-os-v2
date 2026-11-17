from urllib.parse import parse_qs, urlsplit

from research import research_case_engine as cases


def test_systems_case_control_uses_exact_id_and_compact_projection(monkeypatch):
    calls = []
    monkeypatch.setattr(cases.research_memory.supabase, "configured", lambda: True)

    def rest(method, path):
        calls.append((method, path))
        return 200, [{"memory_id": "rcase-1", "memory_kind": "RESEARCH_CASE", "case_id": "rcase-1",
                      "status": "DEPARTMENT_DEVELOPMENT", "department_requests": [{"department": "SYSTEMS", "status": "OPEN"}]}]

    monkeypatch.setattr(cases.research_memory.supabase, "rest", rest)
    monkeypatch.setattr(cases, "_latest_cases", lambda: (_ for _ in ()).throw(
        AssertionError("Systems control read must not hydrate the complete case history")))
    row = cases.get_case_control("rcase-1")
    query = parse_qs(urlsplit(calls[0][1]).query)
    assert calls[0][0] == "GET"
    assert query["memory_id"] == ["eq.rcase-1"]
    assert query["limit"] == ["1"]
    assert "payload" not in query["select"][0].split(",")
    assert "department_requests:payload->department_requests" in query["select"][0]
    assert row["department_requests"][0]["department"] == "SYSTEMS"
