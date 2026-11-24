"""Stateless Gradio Space wrapper for the Nexus MEDIA_ASR worker contract."""
from __future__ import annotations

import hashlib
import os
import secrets
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import gradio as gr
import spaces


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _auth(request: gr.Request | None) -> None:
    expected = os.environ.get("NEXUS_WORKER_TOKEN", "")
    headers = getattr(request, "headers", {}) if request else {}
    supplied = headers.get("x-nexus-worker-token") or headers.get("X-Nexus-Worker-Token")
    if expected and (not supplied or not secrets.compare_digest(supplied, expected)):
        raise PermissionError("worker authentication failed")


def _ffmpeg() -> str:
    binary = shutil.which("ffmpeg")
    if binary:
        return binary
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


@spaces.GPU(duration=60)
def transcribe(audio_path: str | None, job_id: str, video_id: str,
               queue_sequence: int | None = None, audio_reference: str | None = None,
               requested_model: str = "tiny.en", request: gr.Request | None = None) -> dict:
    """Transcribe one acquired audio file and return a shared-contract receipt."""
    _auth(request)
    if not audio_path:
        return {"status": "FAILED_RETRYABLE", "error": "audio is required", "job_id": job_id, "video_id": video_id}
    from faster_whisper import WhisperModel

    started_at = _now()
    started = time.monotonic()
    temp_dir = Path(tempfile.mkdtemp(prefix="nexus-hf-asr-"))
    normalized = temp_dir / f"{video_id}.wav"
    try:
        normalized_result = subprocess.run(
            [_ffmpeg(), "-y", "-i", str(audio_path), "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(normalized)],
            capture_output=True, text=True, timeout=180, check=False,
        )
        if normalized_result.returncode != 0:
            raise RuntimeError(f"ffmpeg normalization failed: {normalized_result.stderr[-500:]}")
        model_name = requested_model or os.environ.get("ASR_MODEL", "tiny.en")
        model_started = time.monotonic()
        gpu_available = os.environ.get("HF_ASR_USE_GPU", "0") == "1"
        try:
            import torch
            gpu_available = gpu_available and bool(torch.cuda.is_available())
        except Exception:
            pass
        selected_device = "cuda" if gpu_available else "cpu"
        selected_compute = "float16" if gpu_available else "int8"
        try:
            model = WhisperModel(model_name, device=selected_device, compute_type=selected_compute,
                                 cpu_threads=4, num_workers=1)
        except Exception as gpu_error:
            if selected_device != "cuda":
                raise
            # ZeroGPU can expose CUDA through torch while omitting a compatible
            # cuBLAS runtime. CPU remains a valid secondary worker path.
            gpu_available = False
            selected_device = "cpu"
            selected_compute = "int8"
            model = WhisperModel(model_name, device=selected_device, compute_type=selected_compute,
                                 cpu_threads=4, num_workers=1)
        model_load_seconds = time.monotonic() - model_started
        try:
            segments, info = model.transcribe(str(normalized), beam_size=1, vad_filter=True)
        except Exception as gpu_error:
            if not gpu_available:
                raise
            gpu_available = False
            selected_device = "cpu"
            selected_compute = "int8"
            model = WhisperModel(model_name, device=selected_device, compute_type=selected_compute,
                                 cpu_threads=4, num_workers=1)
            segments, info = model.transcribe(str(normalized), beam_size=1, vad_filter=True)
        transcript = " ".join(str(segment.text or "").strip() for segment in segments).strip()
        if not transcript:
            raise RuntimeError("empty transcript")
        payload = {
            "job_id": job_id, "queue_sequence": queue_sequence, "video_id": video_id,
            "engine": "faster-whisper", "model": model_name,
            "compute_type": selected_compute, "gpu_fallback_error": str(gpu_error)[:300] if not gpu_available and 'gpu_error' in locals() else None,
            "worker_type": "MEDIA_ASR", "worker_host": "huggingface-space",
            "started_at": started_at, "completed_at": _now(),
            "runtime_seconds": round(time.monotonic() - started, 3),
            "model_load_seconds": round(model_load_seconds, 3),
            "audio_duration_seconds": float(info.duration), "transcript": transcript,
            "word_count": len(transcript.split()),
            "transcript_hash": hashlib.sha256(transcript.encode()).hexdigest(),
            "status": "COMPLETED", "error": None, "audio_reference": audio_reference,
        }
        return payload
    except Exception as exc:  # noqa: BLE001
        return {"job_id": job_id, "video_id": video_id, "engine": "faster-whisper",
                "worker_host": "huggingface-space", "status": "FAILED_RETRYABLE", "error": str(exc)[:500]}
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def health() -> dict:
    return {"status": "ok", "worker_type": "MEDIA_ASR", "engine": "faster-whisper",
            "model": os.environ.get("ASR_MODEL", "tiny.en")}


with gr.Blocks(title="Nexus ASR Worker") as demo:
    gr.Markdown("# Nexus MEDIA_ASR worker")
    gr.Markdown("Private stateless worker. Audio is acquired outside the Space and removed after processing.")
    audio = gr.Audio(type="filepath", label="Acquired audio")
    job_id = gr.Textbox(label="job_id")
    video_id = gr.Textbox(label="video_id")
    queue_sequence = gr.Number(label="queue_sequence", precision=0)
    audio_reference = gr.Textbox(label="audio_reference")
    requested_model = gr.Textbox(value=os.environ.get("ASR_MODEL", "tiny.en"), label="model")
    run = gr.Button("Transcribe")
    output = gr.JSON(label="MEDIA_ASR receipt")
    run.click(transcribe, [audio, job_id, video_id, queue_sequence, audio_reference, requested_model], output)


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", "7860")), show_error=True)
