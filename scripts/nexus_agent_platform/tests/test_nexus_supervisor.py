from pathlib import Path

from scripts.operations import nexus_supervisor


def test_snapshot_is_productivity_aware(tmp_path, monkeypatch):
    monkeypatch.setattr(nexus_supervisor, "ROOT", tmp_path)
    monkeypatch.setattr(nexus_supervisor, "STATE", tmp_path / "state.json")
    monkeypatch.setattr(nexus_supervisor, "HEARTBEAT", tmp_path / "heartbeat.json")
    monkeypatch.setattr(nexus_supervisor, "_launchd", lambda: {})
    monkeypatch.setattr(nexus_supervisor, "_processes", lambda: "")
    result = nexus_supervisor.snapshot()
    assert result["productivity_aware"] is True
    assert result["supervisor_status"] == "RUNNING"
    assert Path(tmp_path / "state.json").exists()
