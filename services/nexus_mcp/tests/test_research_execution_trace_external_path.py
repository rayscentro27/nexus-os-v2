import json

from services.nexus_mcp import server


def test_research_execution_trace_accepts_external_state_path(tmp_path, monkeypatch):
    ledger = tmp_path / "runtime" / "research_execution_jobs.jsonl"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(json.dumps({
        "execution_id": "job_trace_external_12345678",
        "status": "COMPLETED",
        "worker_id": "worker-test",
        "error": "",
    }) + "\n", encoding="utf-8")
    monkeypatch.setattr(server, "nexus_research_state_path", lambda *parts: ledger)

    result = server._get_research_execution_trace("job_trace_external_12345678")

    assert result["status"] == "ok"
    assert result["event_count"] == 1
    assert result["events"][0]["status"] == "COMPLETED"
    assert result["source"] == "external_research_state:runtime/research_execution_jobs.jsonl"
