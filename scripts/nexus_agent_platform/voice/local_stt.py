"""Fixed local whisper.cpp adapter with no raw-audio retention."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import time
import uuid
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

VOICE_INPUT_SCHEMA = "nexus.voice-input.v1"
TRANSCRIPT_SCHEMA = "nexus.voice-transcript.v1"
AUDIO_MAX_DURATION_MS = 30_000
AUDIO_DECODE_LIMIT_SECONDS = 31
AUDIO_PREFERRED_DURATION_MS = 15_000
AUDIO_MAX_BYTES = 10 * 1024 * 1024
DEFAULT_MODEL = Path("tools/voice/models/ggml-base.en.bin")
DEFAULT_BINARY = Path("tools/voice/runtime/whisper.cpp/build/bin/whisper-cli")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve(value: str | Path | None, default: Path) -> Path:
    path = Path(value or default)
    return path if path.is_absolute() else _root() / path


def build_voice_request(*, session_id: str, user_id: str = "ray", source: str = "LOCAL_TEST", audio_format: str = "audio/wav", sample_rate: int = 16_000, duration_ms: int = 0, consent_state: str = "ADMIN_CONSENT") -> Dict[str, Any]:
    return {"schema_version": VOICE_INPUT_SCHEMA, "voice_request_id": f"voice_{uuid.uuid4().hex}", "session_id": session_id, "user_id": user_id, "source": source, "audio_format": audio_format, "sample_rate": sample_rate, "duration_ms": duration_ms, "consent_state": consent_state, "created_at": utc_now(), "audio_retained": False, "external_action_performed": False}


def validate_voice_request(request: Dict[str, Any], *, audio_size: int = 0) -> tuple[bool, str]:
    required = ("voice_request_id", "session_id", "source", "audio_format", "consent_state")
    if not isinstance(request, dict) or request.get("schema_version") != VOICE_INPUT_SCHEMA: return False, "unsupported-schema"
    if any(not request.get(key) for key in required): return False, "missing-voice-field"
    if request.get("source") not in {"ADMIN_PORTAL", "LOCAL_TEST", "TELEGRAM_FUTURE"}: return False, "unsupported-source"
    if request.get("consent_state") != "ADMIN_CONSENT": return False, "consent-required"
    if audio_size <= 0 or audio_size > AUDIO_MAX_BYTES: return False, "audio-size-bounded"
    if int(request.get("duration_ms") or 0) > AUDIO_MAX_DURATION_MS: return False, "audio-duration-bounded"
    if request.get("external_action_performed") is not False: return False, "external-action-field"
    return True, "ok"


def _wav_duration_ms(path: Path) -> Optional[int]:
    try:
        with wave.open(str(path), "rb") as handle:
            return round(handle.getnframes() / max(1, handle.getframerate()) * 1000)
    except (wave.Error, OSError):
        return None


def _duration_ms(path: Path) -> Optional[int]:
    wav = _wav_duration_ms(path)
    if wav is not None: return wav
    try:
        output = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], capture_output=True, text=True, timeout=5, check=False)
        return round(float(output.stdout.strip()) * 1000) if output.returncode == 0 else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def _normalize_to_wav(source: Path, target: Path) -> None:
    if source.suffix.lower() == ".wav":
        target.write_bytes(source.read_bytes())
        return
    completed = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(source), "-t", str(AUDIO_DECODE_LIMIT_SECONDS), "-ac", "1", "-ar", "16000", "-f", "wav", str(target)], capture_output=True, text=True, timeout=15, check=False)
    if completed.returncode != 0: raise RuntimeError("audio-format-normalization-failed")


def _extract_transcript(stdout: str) -> str:
    lines = []
    for line in stdout.splitlines():
        text = line.strip()
        if not text or text.startswith(("whisper_", "main:", "system_info:", "ggml_", "whisper_print_")): continue
        if text.startswith("[") and "]" in text[:20]:
            text = text.split("]", 1)[1].strip()
        if text and not text.startswith(("load", "encode", "decode", "output")): lines.append(text)
    return " ".join(lines).strip()


def transcribe_audio_file(audio_path: str | Path, request: Dict[str, Any], *, binary: str | Path | None = None, model: str | Path | None = None) -> Dict[str, Any]:
    source = Path(audio_path)
    if not source.exists(): raise ValueError("audio-not-found")
    size = source.stat().st_size
    # Client/container duration metadata is supplemental only. Validate the
    # request shape and byte bound first, then use normalized WAV frames below
    # as the authoritative duration for the transcript contract.
    request_for_validation = {**request, "duration_ms": 0}
    valid, reason = validate_voice_request(request_for_validation, audio_size=size)
    if not valid: raise ValueError(reason)
    binary_path, model_path = _resolve(binary, DEFAULT_BINARY), _resolve(model, DEFAULT_MODEL)
    if not binary_path.exists() or not model_path.exists(): raise RuntimeError("whisper-runtime-not-configured")
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="nexus-voice-") as temp_dir:
        wav_path = Path(temp_dir) / "input.wav"
        _normalize_to_wav(source, wav_path)
        duration = _wav_duration_ms(wav_path)
        if duration is None: raise ValueError("audio-duration-unavailable")
        if duration <= 0: raise ValueError("audio-duration-unavailable")
        if duration > AUDIO_MAX_DURATION_MS: raise ValueError("audio-duration-bounded")
        command = [str(binary_path), "-m", str(model_path), "-f", str(wav_path), "-l", "en", "-nt", "-np", "-t", "2"]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
        if completed.returncode != 0: raise RuntimeError("whisper-transcription-failed")
        transcript = _extract_transcript(completed.stdout)
    if not transcript: raise ValueError("empty-transcript")
    return {"schema_version": TRANSCRIPT_SCHEMA, "transcript_id": f"transcript_{uuid.uuid4().hex}", "voice_request_id": request["voice_request_id"], "session_id": request["session_id"], "text": transcript, "language": "en", "confidence": None, "duration_ms": duration, "stt_provider": "whisper.cpp", "model": model_path.name, "model_version": "base.en", "model_hash": hashlib.sha256(model_path.read_bytes()).hexdigest(), "processing_duration_ms": round((time.monotonic() - started) * 1000), "audio_retained": False, "created_at": utc_now(), "external_action_performed": False}


def voice_status() -> Dict[str, Any]:
    binary = _resolve(os.environ.get("NEXUS_VOICE_BINARY"), DEFAULT_BINARY)
    model = _resolve(os.environ.get("NEXUS_VOICE_MODEL"), DEFAULT_MODEL)
    configured = binary.exists() and model.exists()
    return {"status": "HEALTHY" if configured else "NOT_CONFIGURED", "stt_provider": "whisper.cpp", "model": model.name, "local_offline": True, "raw_audio_retained": False, "admin_transport": "CONNECTED" if os.environ.get("NEXUS_VOICE_ENDPOINT") else "LOCAL_ONLY", "last_transcription": None, "last_error": None, "core_health_dependency": False}
