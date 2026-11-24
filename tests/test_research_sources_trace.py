import json
import os

from nexus_agent_platform import research_sources_trace as trace


def test_research_sources_trace_records_shape_and_caller_without_filter_values(tmp_path, monkeypatch):
    target = tmp_path / "trace.jsonl"
    monkeypatch.setattr(trace, "TRACE_PATH", target)
    monkeypatch.setenv("NEXUS_WAKE_ID", "wake_0123456789abcdef")
    monkeypatch.setenv("NEXUS_KERNEL_PHASE", "TEST_PHASE")
    monkeypatch.setenv("NEXUS_RESEARCH_SOURCE_ID", "src_123")

    def application_caller():
        trace.trace_request("GET", "research_sources?select=id,title&url=eq.https%3A%2F%2Fsecret.example%2Fprivate&source_id=eq.src_123&limit=1")

    application_caller()
    event = json.loads(target.read_text().strip())
    assert event["caller_function"] == "application_caller"
    assert event["query"]["selected_fields"] == ["id", "title"]
    assert event["query"]["limit"] == 1
    assert "secret.example" not in target.read_text()
    assert event["wake_id"] == "wake_0123456789abcdef"
    assert event["kernel_phase"] == "TEST_PHASE"
    assert event["query"]["filters"][-1]["opaque_id"] == "src_123"


def test_other_tables_are_not_traced(tmp_path, monkeypatch):
    target = tmp_path / "trace.jsonl"
    monkeypatch.setattr(trace, "TRACE_PATH", target)
    trace.trace_request("GET", "research_questions?select=id&limit=1")
    assert not target.exists()
