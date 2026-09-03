from datetime import datetime, timedelta, timezone

from nexus_agent_platform.knowledge_freshness import classify_freshness, refresh_once
from nexus_agent_platform.governed import persistence


def test_missing_timestamp_waits_for_source():
    assert classify_freshness({"content_id": "x", "content_type": "web_page"})["status"] == "WAITING_SOURCE"


def test_stale_refresh_persists_new_lineage(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path))
    record = {"content_id": "old", "canonical_url": "https://example.test/page", "content_type": "web_page",
              "title": "old", "last_seen_at": "2020-01-01T00:00:00+00:00", "source_family": "example.test"}
    result = refresh_once(record, lambda url: {"ok": True, "url": url, "title": "new", "excerpt": "current evidence",
                                                "text_hash": "hash", "retrieved_at": datetime.now(timezone.utc).isoformat()},
                          as_of=datetime.now(timezone.utc))
    assert result["status"] == "COMPLETED"
    assert result["receipt"]["freshness_after"]["status"] == "FRESH"
    assert persistence.read_records("knowledge_refreshes")[0]["content_stored"] is True
