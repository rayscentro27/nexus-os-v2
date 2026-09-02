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


def test_heartbeat_does_not_call_queue_for_work():
    with patch.object(heartbeat, "REGISTRY", Path("/tmp/alpha-heartbeat-registry.json")), \
         patch.object(heartbeat, "seed_registry", return_value=[{"source_id": "g", "source_type": "GITHUB_REPO", "url": "https://github.com/example/g", "monitoring_enabled": True, "research_lane": "AI_NEXUS"}]), \
         patch.object(heartbeat, "fetch_github", return_value={"ok": True, "url": "https://github.com/example/g", "source_type": "GITHUB_REPO", "retrieved_at": "now", "excerpt": "real source"}), \
         patch.object(heartbeat, "persist_finding", return_value={"new": True, "url": "https://example/g", "claim_id": "c"}), \
         patch.object(heartbeat, "append_record"), patch.object(heartbeat, "ACTIVITY", Path("/tmp/alpha-heartbeat-test.json")):
        result = heartbeat.run(max_channels=1)
    assert result["ok"] is True
    assert result["activity"]["sources_checked"] == 1
    Path("/tmp/alpha-heartbeat-test.json").unlink(missing_ok=True)
    Path("/tmp/alpha-heartbeat-registry.json").unlink(missing_ok=True)
