import json

import nexus_agent_platform.research.last30days_adapter as adapter
from nexus_agent_platform.research.last30days_adapter import health, run_demand_radar


def test_last30days_health_is_pinned_and_cookie_safe():
    result = health()
    assert result["version"] == "3.24.0"
    assert result["pinned_commit"] == "25a5cea5bfa5723991894385041ebb3b87049753"
    assert result["browser_cookies_enabled"] is False
    assert result["publication_enabled"] is False


def test_last30days_mock_export_normalizes_and_persists_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path / "governed"))
    result = run_demand_radar({
        "request_id": "adapter-test",
        "query": "business funding for new LLC",
        "requested_sources": ["reddit", "youtube"],
        "work_class": "DEMAND_DISCOVERY",
        "mock": True,
        "max_runtime_seconds": 10,
        "max_results": 5,
    }, timeout_seconds=10)
    assert result["status"] == "PASS"
    assert result["schema_version"] == "1.3"
    assert result["result_count"] >= 1
    assert result["browser_cookies_enabled"] is False
    assert result["publication_enabled"] is False
    source_file = tmp_path / "governed" / "research_v2_sources.jsonl"
    assert source_file.exists()
    assert json.loads(source_file.read_text().splitlines()[0])["upstream_run_id"] == result["run_id"]


def test_source_specific_runner_preserves_healthy_partial_results(monkeypatch):
    def fake_run(request, *, timeout_seconds=None):
        source = request["requested_sources"][0]
        if source == "youtube":
            return {"status": "TIMEOUT", "run_id": "youtube-run", "sources_attempted": [source], "stderr": "metadata timeout"}
        return {
            "status": "PASS", "run_id": f"{source}-run", "sources_attempted": [source],
            "sources_successful": [source], "source_status": {source: "OK"},
            "signals": [{"signal_id": f"{source}-signal", "source_url": f"https://example.test/{source}"}],
            "clusters": [], "result_count": 1, "new_evidence_count": 1, "existing_source_links": 0,
        }

    monkeypatch.setattr(adapter, "run_demand_radar", fake_run)
    result = adapter.run_demand_radar_sources({
        "request_id": "partial-test", "query": "funding", "requested_sources": ["hackernews", "youtube"],
    }, source_timeouts={"hackernews": 1, "youtube": 1})
    assert result["status"] == "PASS"
    assert result["result_count"] == 1
    assert result["source_status"] == {"hackernews": "OK"}
    assert result["errors"][0]["source"] == "youtube"
