import json

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
