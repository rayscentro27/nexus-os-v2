"""Provider-neutral notebook recipes and artifact gates for Systems.

This module is deliberately an adapter over the existing temporary-worker
framework.  It does not create a scheduler or a second execution plane.  It
builds a reproducible job envelope, discovers only explicitly approved local
assets, and verifies returned media without claiming that an MP4 is good.
"""
from __future__ import annotations

import json
import mimetypes
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nexus_agent_platform.governed import persistence
from nexus_agent_platform.temporary_worker_framework import (
    KaggleAdapter,
    ResourceRequirements,
    WorkerJob,
    provider_registry,
    sha256_file,
)

ROOT = Path(__file__).resolve().parents[2]
RECIPE_PATH = ROOT / "configs" / "systems_worker_recipes.json"
SYSTEMS_OBJECTIVE_ID = "systems-permanent-cloud-notebook-worker"
EXPECTED_ASSET_NAMES = {"nova_master.jpg", "nova_master.jpeg", "nova_master.png", "nova_source.mp4"}
AUDIO_SUFFIXES = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
EXPECTED_AUDIO_NAMES = {"nova_audio.wav", "nova_audio.mp3", "nova_source.wav", "nova_source.mp3", "nova_voice.wav", "nova_voice.mp3", "nova_test.wav", "nova_test.mp3"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_recipe(recipe_id: str) -> dict[str, Any]:
    payload = json.loads(RECIPE_PATH.read_text(encoding="utf-8"))
    for recipe in payload.get("recipes", []):
        if recipe.get("recipe_id") == recipe_id:
            return {**recipe, "operating_mode": payload.get("operating_mode"), "schema_version": payload.get("schema_version")}
    raise KeyError(f"unknown_systems_recipe:{recipe_id}")


def discover_approved_assets(source_dir: Path | None = None) -> dict[str, Any]:
    """Hash likely Nova assets; never silently select arbitrary media."""
    directory = (source_dir or Path.home() / "Downloads").expanduser().resolve()
    candidates: list[dict[str, Any]] = []
    if directory.exists():
        for path in sorted(directory.iterdir()):
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            if path.name.lower() not in EXPECTED_ASSET_NAMES and path.name.lower() not in EXPECTED_AUDIO_NAMES:
                continue
            candidates.append({
                "name": path.name,
                "path": str(path),
                "kind": "audio" if suffix in AUDIO_SUFFIXES else ("video" if suffix == ".mp4" else "image"),
                "mime_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
                "approved_name_match": path.name.lower() in EXPECTED_ASSET_NAMES or path.name.lower() in EXPECTED_AUDIO_NAMES,
            })
    return {
        "source_dir": str(directory),
        "assets": candidates,
        "approved_assets_present": any(item["approved_name_match"] for item in candidates),
        "audio_present": any(item["kind"] == "audio" for item in candidates),
        "substitution_performed": False,
        "discovered_at": _now(),
    }


def build_worker_job(recipe_id: str, assets: dict[str, Any], *, provider_preferences: list[str] | None = None) -> WorkerJob:
    recipe = load_recipe(recipe_id)
    job_id = f"systems-notebook-{recipe_id}-{uuid.uuid4().hex[:12]}"
    requirements = ResourceRequirements(
        cpu="4",
        ram="16GiB",
        gpu_required=recipe.get("required_accelerator") == "NVIDIA_GPU",
        gpu_class="nvidia-t4" if recipe.get("required_accelerator") == "NVIDIA_GPU" else None,
        vram="16GiB" if recipe.get("required_accelerator") == "NVIDIA_GPU" else None,
        storage="20GiB",
        network_required=True,
    )
    return WorkerJob(
        worker_job_id=job_id,
        worker_type=f"SYSTEMS_NOTEBOOK_{recipe_id.upper().replace('-', '_')}",
        requested_by="SYSTEMS_AI_WORKER",
        input_artifacts=[item["path"] for item in assets.get("assets", [])],
        parameters={"recipe": recipe, "assets": assets, "production_touch": False, "output_contract": recipe.get("outputs", [])},
        resource_requirements=requirements,
        environment_requirements={"recipe_id": recipe_id, "recipe_version": recipe.get("version"), "base_runtime": recipe.get("base_runtime"), "python_packages": recipe.get("python_packages", []), "system_packages": recipe.get("system_packages", [])},
        runtime={"max_runtime": 900, "startup_timeout": 120, "execution_timeout": 720, "cleanup_timeout": 60},
        output_destination="reports/systems/worker_artifacts",
        provider_preferences=provider_preferences or ["kaggle", "modal", "oracle"],
        batch_metadata={"worker_class": "SYSTEMS_REPRODUCIBLE_NOTEBOOK", "environment_signature": f"{recipe_id}:{recipe.get('version')}", "dependency_signature": json.dumps(recipe.get("python_packages", []), sort_keys=True), "model_signature": str(recipe.get("model_revision")), "gpu_class": requirements.gpu_class or "none"},
    )


def provider_readiness() -> dict[str, Any]:
    registry = provider_registry()
    kaggle = registry["kaggle"]
    return {"providers": registry, "kaggle_status": "READY" if kaggle.get("available") else "KAGGLE_AUTH_REQUIRED", "remote_control_plane": registry["modal"].get("authorization_state") == "DEPLOYED_EXISTING_REMOTE_WORKER"}


def persist_objective() -> dict[str, Any]:
    record = {"objective_id": SYSTEMS_OBJECTIVE_ID, "department": "SYSTEMS", "status": "ACTIVE_RESEARCH", "mission": "Continuously improve, validate, and maintain Nexus execution environments and worker recipes required by departments.", "next_action": "Inspect approved assets and run the clean-runtime diagnostic before selecting a GPU avatar recipe.", "human_gate": "KAGGLE_AUTH_REQUIRED", "updated_at": _now()}
    existing = persistence.read_records("systems_services")
    if next((row for row in existing if row.get("objective_id") == SYSTEMS_OBJECTIVE_ID), None) is None:
        persistence.append_record("systems_services", record)
    return record


def persist_recipe_receipt(recipe_id: str, *, assets: dict[str, Any], readiness: dict[str, Any]) -> dict[str, Any]:
    recipe = load_recipe(recipe_id)
    record = {"recipe_id": recipe_id, "recipe_version": recipe["version"], "recipe": recipe, "assets": assets, "provider_readiness": readiness, "created_at": _now(), "status": "REGISTERED"}
    persistence.append_record("systems_worker_recipes", record)
    return record


def verify_video_artifact(path: Path, *, expected_audio: bool = True) -> dict[str, Any]:
    result: dict[str, Any] = {"path": str(path), "exists": path.exists(), "nonzero": path.exists() and path.stat().st_size > 0, "sha256": None, "ffprobe": "UNAVAILABLE", "video_stream": False, "audio_stream": False, "duration_seconds": None, "width": None, "height": None, "fps": None, "verified": False}
    if not result["nonzero"]:
        return result
    result["sha256"] = sha256_file(path)
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return result
    command = [ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    if completed.returncode:
        result["ffprobe"] = "FAILED"
        return result
    result["ffprobe"] = "PASS"
    payload = json.loads(completed.stdout or "{}")
    streams = payload.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    result["video_stream"] = video is not None
    result["audio_stream"] = audio is not None
    if video:
        result["width"], result["height"] = video.get("width"), video.get("height")
        result["fps"] = video.get("r_frame_rate")
    result["duration_seconds"] = (payload.get("format") or {}).get("duration")
    result["verified"] = bool(result["video_stream"] and (result["audio_stream"] or not expected_audio))
    return result


def stage_job_receipt(job: WorkerJob, *, status: str, reason: str | None = None) -> dict[str, Any]:
    record = {"worker_job_id": job.worker_job_id, "worker_type": job.worker_type, "status": status, "recipe_id": job.parameters.get("recipe", {}).get("recipe_id"), "assets": job.parameters.get("assets"), "production_touch": False, "reason": reason, "created_at": _now()}
    persistence.append_record("systems_worker_jobs", record)
    return record


def build_clean_runtime_package(job: WorkerJob, workdir: Path) -> Path:
    """Materialize a provider package from the versioned recipe.

    The diagnostic recipe is intentionally executable without model weights.
    Model recipes produce a blocked package until their revision/license gate is
    resolved; this prevents a cloud run from silently using mutable ``main`` or
    hidden notebook state.
    """
    recipe = job.parameters.get("recipe") or {}
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "job_manifest.json").write_text(json.dumps({"job": job.__dict__, "recipe": recipe}, default=lambda value: value.__dict__, indent=2, sort_keys=True), encoding="utf-8")
    (workdir / "kernel-metadata.json").write_text(json.dumps({
        "id": f"nexus-{job.worker_job_id[-24:]}",
        "title": f"Nexus {recipe.get('recipe_id', 'systems-worker')}",
        "code_file": "worker.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": True,
        "enable_gpu": bool(job.resource_requirements.gpu_required),
        "enable_internet": True,
    }, indent=2, sort_keys=True), encoding="utf-8")
    for asset in (job.parameters.get("assets") or {}).get("assets", []):
        source = Path(asset["path"])
        if source.exists() and source.is_file():
            shutil.copy2(source, workdir / source.name)
    worker = _diagnostic_worker_source() if recipe.get("recipe_id") == "gpu-environment-diagnostic-v1" else _blocked_model_worker_source(recipe)
    (workdir / "worker.py").write_text(worker, encoding="utf-8")
    return workdir


def _diagnostic_worker_source() -> str:
    return '''import json, os, platform, shutil, subprocess, sys, time

def command_result(command):
    try:
        p = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
        return {"returncode": p.returncode, "stdout": p.stdout[-2000:], "stderr": p.stderr[-2000:]}
    except Exception as exc:
        return {"error": str(exc)}

started = time.time()
report = {
    "python": sys.version,
    "platform": platform.platform(),
    "torch": command_result([sys.executable, "-c", "import torch; print(torch.__version__); print(torch.cuda.is_available())"]),
    "ffmpeg": command_result(["ffmpeg", "-version"]),
    "disk": shutil.disk_usage("/")._asdict(),
    "network": command_result([sys.executable, "-c", "import urllib.request; print(urllib.request.urlopen('https://pypi.org', timeout=10).status)"]),
    "model_import_boundary": "NO_MODEL_IMPORTED_BY_DIAGNOSTIC",
    "started_at": started,
    "finished_at": time.time(),
}
json.dump(report, open("diagnostic_report.json", "w"), indent=2, sort_keys=True)
json.dump({"status": "SUCCEEDED", "recipe": "gpu-environment-diagnostic-v1", "report": "diagnostic_report.json", "production_touch": False}, open("run_manifest.json", "w"), indent=2, sort_keys=True)
'''


def _blocked_model_worker_source(recipe: dict[str, Any]) -> str:
    payload = json.dumps({"recipe_id": recipe.get("recipe_id"), "status": recipe.get("reproducibility_status"), "model_source": recipe.get("model_source")}, sort_keys=True)
    return f'''import json
raise RuntimeError("MODEL_RECIPE_NOT_RUN_PENDING_PINNED_DEPENDENCY_AND_LICENSE_REVIEW: {payload}")
'''
