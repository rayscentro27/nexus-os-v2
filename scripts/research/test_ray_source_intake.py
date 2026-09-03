from ray_source_intake import add_source, list_sources, record_backfill, set_source_state, update_source


def test_ray_source_intake_is_idempotent_and_multilane(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path))
    first = add_source("https://example.com/channel", source_type="YOUTUBE_CHANNEL", lanes=["TRADING", "FUNDING"])
    duplicate = add_source("https://example.com/channel/", source_type="YOUTUBE_CHANNEL", lanes=["TRADING"])
    assert first["added_by"] == "RAY_CURATED"
    assert duplicate["idempotent"] is True
    assert len(list_sources(lane="FUNDING")) == 1


def test_ray_source_state_backfill_and_monitoring(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path))
    source = add_source("https://example.com/funding", source_type="FUNDING_SOURCE", lanes=["FUNDING"])
    updated = record_backfill(source["source_id"], ["item-1", "item-2"], last_fingerprint="fp-1")
    assert updated["initial_backfill"]["status"] == "COMPLETE"
    assert updated["incremental_monitoring"]["last_seen_fingerprint"] == "fp-1"
    paused = set_source_state(source["source_id"], "PAUSED")
    assert paused["enabled"] is False
    changed = update_source(source["source_id"], priority="P1_ACTIVE_OBJECTIVE", lanes=["FUNDING", "FINANCE"])
    assert changed["lanes"] == ["FINANCE", "FUNDING"]
