import json
from pathlib import Path
from unittest.mock import patch

import alpha_heartbeat as heartbeat


def test_seed_registry_contains_all_ray_sources(tmp_path):
    with patch.object(heartbeat, "REGISTRY", tmp_path / "registry.json"):
        rows = heartbeat.seed_registry()
    assert len(rows) == 22
    assert sum(row["source_type"] == "YOUTUBE_CHANNEL" for row in rows) == 20
    assert all(row["added_by"] == "RAY_CURATED" for row in rows)
    assert all(row["baseline_limit"] == 10 for row in rows if row["source_type"] == "YOUTUBE_CHANNEL")


def test_youtube_result_is_bounded_to_latest_ten():
    result = {"ok": True, "url": "channel", "retrieved_at": "now", "source_type": "YOUTUBE_CHANNEL",
              "entries": [{"id": str(i)} for i in range(20)]}
    assert len(result["entries"][:10]) == 10


def test_seed_registry_repairs_newer_safe_identifier_shape(tmp_path):
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps([
        {"source_id": "legacy", "url": "https://example.com/legacy", "source_type": "WEB_PAGE"},
        {"source_id": "intake", "url_or_safe_identifier": "https://example.com/intake", "source_type": "WEB_PAGE"},
    ]))
    with patch.object(heartbeat, "REGISTRY", registry), patch.object(heartbeat, "REPAIR_RECEIPT", tmp_path / "repair.json"):
        rows = heartbeat.seed_registry()
    assert {row["url"] for row in rows if row["source_id"] in {"legacy", "intake"}} == {
        "https://example.com/legacy", "https://example.com/intake"
    }
    receipt = json.loads((tmp_path / "repair.json").read_text())
    assert receipt["rows_normalized"] == 1
    assert receipt["continuation"] == "ALPHA_RETRY_ALLOWED"


def test_heartbeat_does_not_call_queue_for_work():
    with patch.object(heartbeat, "REGISTRY", Path("/tmp/alpha-heartbeat-registry.json")), \
         patch.object(heartbeat, "seed_registry", return_value=[{"source_id": "g", "source_type": "GITHUB_REPO", "url": "https://github.com/example/g", "monitoring_enabled": True, "research_lane": "AI_NEXUS"}]), \
         patch.object(heartbeat, "fetch_github", return_value={"ok": True, "url": "https://github.com/example/g", "source_type": "GITHUB_REPO", "retrieved_at": "now", "excerpt": "real source"}), \
         patch.object(heartbeat, "persist_finding", return_value={"new": True, "url": "https://example/g", "claim_id": "c"}), \
         patch.object(heartbeat, "evaluate_pending", return_value={"evaluations_created": [], "evaluated_count": 0}), \
         patch.object(heartbeat, "append_record"), patch.object(heartbeat, "ACTIVITY", Path("/tmp/alpha-heartbeat-test.json")):
        result = heartbeat.run(max_channels=1)
    assert result["ok"] is True
    assert result["activity"]["sources_checked"] == 1
    Path("/tmp/alpha-heartbeat-test.json").unlink(missing_ok=True)
    Path("/tmp/alpha-heartbeat-registry.json").unlink(missing_ok=True)
