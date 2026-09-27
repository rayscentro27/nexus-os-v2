import json
from pathlib import Path

from nexus_agent_platform.systems_notebook_worker import (
    build_worker_job,
    discover_approved_assets,
    load_recipe,
    provider_readiness,
    verify_video_artifact,
)


def test_diagnostic_recipe_is_versioned_and_rebuildable():
    recipe = load_recipe("gpu-environment-diagnostic-v1")
    assert recipe["version"] == "1.0.0"
    assert recipe["reproducibility_status"] == "READY"
    assert "ffmpeg" in recipe["system_packages"]


def test_asset_discovery_hashes_only_approved_or_audio_files(tmp_path):
    approved = tmp_path / "nova_master.jpg"
    approved.write_bytes(b"approved")
    unrelated = tmp_path / "unrelated.jpg"
    unrelated.write_bytes(b"do not use")
    audio = tmp_path / "nova_audio.wav"
    audio.write_bytes(b"audio")
    found = discover_approved_assets(tmp_path)
    names = {item["name"] for item in found["assets"]}
    assert names == {"nova_master.jpg", "nova_audio.wav"}
    assert found["substitution_performed"] is False
    assert found["assets"][0]["sha256"]


def test_job_contract_preserves_recipe_and_no_production_touch(tmp_path):
    assets = discover_approved_assets(tmp_path)
    job = build_worker_job("gpu-environment-diagnostic-v1", assets, provider_preferences=["kaggle"])
    assert job.parameters["recipe"]["recipe_id"] == "gpu-environment-diagnostic-v1"
    assert job.parameters["production_touch"] is False
    assert job.provider_preferences == ["kaggle"]


def test_kaggle_auth_gate_is_truthful():
    readiness = provider_readiness()
    assert readiness["kaggle_status"] in {"READY", "KAGGLE_AUTH_REQUIRED"}
    assert readiness["remote_control_plane"] is True


def test_video_verification_does_not_equate_file_existence_with_approval(tmp_path):
    video = tmp_path / "nova_test.mp4"
    video.write_bytes(b"not a video")
    result = verify_video_artifact(video)
    assert result["exists"] is True
    assert result["verified"] is False
