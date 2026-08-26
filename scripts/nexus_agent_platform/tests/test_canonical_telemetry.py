import json

from nexus_agent_platform.canonical_telemetry import build_telemetry, write_telemetry


def test_telemetry_is_explicit_when_preflight_or_runtime_is_missing(monkeypatch, tmp_path):
    import nexus_agent_platform.canonical_telemetry as telemetry
    monkeypatch.setattr(telemetry, "PREFLIGHT_PATH", tmp_path / "missing.json")
    monkeypatch.setattr(telemetry, "CAMPAIGN_PATH", tmp_path / "missing-campaign.json")
    monkeypatch.setattr(telemetry, "OUTPUT_PATH", tmp_path / "telemetry.json")
    result = build_telemetry()
    assert result["system"]["overall_status"] == "UNKNOWN"
    assert result["proof"]["watchdog"] == "UNKNOWN"
    written = write_telemetry()
    assert json.loads((tmp_path / "telemetry.json").read_text())["read_only"] is True
    assert written["safety"]["arbitrary_shell"] == "PROHIBITED"
