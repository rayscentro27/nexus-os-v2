"""Minimal Kaggle GPU ASR canary for a Mac-acquired audio file.

This is a worker payload, not an orchestrator.  Nexus submits the job and
persists the returned transcript through the existing canonical ingestion
path.  No credentials are required in the Kaggle notebook.
"""
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path


def command_version(command):
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=15).stdout.strip()
    except Exception as exc:
        return f"UNAVAILABLE:{type(exc).__name__}"


def main():
    started = time.time()
    audio = Path(os.environ.get("NEXUS_AUDIO_PATH", "/kaggle/input/nexus-asr-audio/audio.wav"))
    if not audio.exists() and Path("/kaggle/input").exists():
        candidates = sorted(Path("/kaggle/input").glob("**/*.wav"))
        if candidates:
            audio = candidates[0]
    receipt = {
        "worker_type": "MEDIA_ASR",
        "worker_host": "kaggle",
        "job_id": os.environ.get("NEXUS_JOB_ID", "kaggle-asr-canary"),
        "video_id": os.environ.get("NEXUS_VIDEO_ID"),
        "queue_sequence": os.environ.get("NEXUS_QUEUE_SEQUENCE"),
        "python": sys.version,
        "platform": platform.platform(),
        "audio_path": str(audio),
        "audio_bytes": audio.stat().st_size if audio.exists() else 0,
        "ffmpeg": command_version(["ffmpeg", "-version"]).splitlines()[0] if audio.exists() else "NOT_CHECKED",
    }
    try:
        import torch
        receipt["cuda_available"] = bool(torch.cuda.is_available())
        receipt["gpu_model"] = torch.cuda.get_device_name(0) if receipt["cuda_available"] else None
        receipt["gpu_memory_bytes"] = int(torch.cuda.get_device_properties(0).total_memory) if receipt["cuda_available"] else 0
    except Exception as exc:
        receipt["cuda_available"] = False
        receipt["gpu_error"] = f"{type(exc).__name__}: {exc}"
    try:
        try:
            import ctranslate2
            from faster_whisper import WhisperModel
            receipt["dependency_setup_seconds"] = 0
        except ModuleNotFoundError:
            setup_started = time.time()
            install = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
                 "faster-whisper==1.2.1", "av>=16,<19"],
                capture_output=True, text=True, timeout=300,
            )
            receipt["dependency_setup_seconds"] = round(time.time() - setup_started, 3)
            receipt["dependency_install_returncode"] = install.returncode
            if install.returncode != 0:
                raise RuntimeError(install.stderr[-1000:])
            import importlib
            importlib.invalidate_caches()
            import ctranslate2
            from faster_whisper import WhisperModel
        receipt["ctranslate2_version"] = getattr(ctranslate2, "__version__", "unknown")
        try:
            import av
            receipt["pyav_version"] = getattr(av, "__version__", "unknown")
        except Exception:
            receipt["pyav_version"] = "UNAVAILABLE"
        receipt["faster_whisper_import"] = True
        model_name = os.environ.get("NEXUS_ASR_MODEL", "small.en")
        compute_type = os.environ.get("NEXUS_ASR_COMPUTE_TYPE", "float16" if receipt.get("cuda_available") else "int8")
        device = "cuda" if receipt.get("cuda_available") else "cpu"
        model_started = time.time()
        model = WhisperModel(model_name, device=device, compute_type=compute_type)
        receipt["model"] = model_name
        receipt["compute_type"] = compute_type
        receipt["model_load_seconds"] = round(time.time() - model_started, 3)
        if not audio.exists():
            raise FileNotFoundError(str(audio))
        asr_started = time.time()
        segments, info = model.transcribe(str(audio), beam_size=1, vad_filter=True)
        parts = []
        for segment in segments:
            text = segment.text.strip()
            if text:
                parts.append(text)
        transcript = " ".join(parts).strip()
        receipt.update({
            "audio_duration_seconds": float(getattr(info, "duration", 0.0) or 0.0),
            "runtime_seconds": round(time.time() - asr_started, 3),
            "transcript": transcript,
            "word_count": len(transcript.split()),
            "transcript_hash": hashlib.sha256(transcript.encode()).hexdigest(),
            "status": "COMPLETED" if transcript else "FAILED_RETRYABLE",
            "error": None if transcript else "empty transcript",
        })
    except Exception as exc:
        receipt.update({"status": "FAILED_RETRYABLE", "error": f"{type(exc).__name__}: {exc}", "runtime_seconds": 0})
    receipt["completed_at_epoch"] = time.time()
    receipt["total_runtime_seconds"] = round(time.time() - started, 3)
    out = Path("/kaggle/working/nexus_asr_receipt.json")
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    # The generic KaggleAdapter retrieves these stable contract artifacts.
    Path("result.json").write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
    Path("artifact.txt").write_text(
        json.dumps({"status": receipt.get("status"), "word_count": receipt.get("word_count", 0),
                    "transcript_hash": receipt.get("transcript_hash")}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({k: v for k, v in receipt.items() if k != "transcript"}, sort_keys=True))


if __name__ == "__main__":
    main()
