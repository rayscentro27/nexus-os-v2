"""Bounded TTS-to-WAV adapter for Nova's avatar canary.

The macOS `say` provider is explicitly test-only. Production voice selection
remains in Nova's current client speech path unless a production provider is
configured separately.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts/nova/avatar-canary"
MAX_TEXT_CHARS = 600


def synthesize_test_wav(
    text: str, *, output_path: Path | None = None,
    voice_name: str | None = None, speaking_rate: int | None = None,
) -> dict[str, Any]:
    text = " ".join(str(text).split())
    if not text or len(text) > MAX_TEXT_CHARS:
        raise ValueError("nova_test_tts_text_empty_or_too_long")
    if os.environ.get("NOVA_TEST_TTS_PROVIDER", "") != "macos_say":
        raise RuntimeError("test_tts_provider_not_explicitly_enabled")
    # Test-only overrides support voice auditions and lip-motion tuning. They
    # never write or modify Nova's canonical production voice configuration.
    voice_name = voice_name or os.environ.get("NOVA_TEST_TTS_VOICE")
    raw_rate = speaking_rate if speaking_rate is not None else os.environ.get("NOVA_TEST_TTS_RATE")
    if voice_name and voice_name not in {"Samantha", "Victoria", "Alex", "Fred"}:
        raise ValueError("unsupported_test_voice")
    rate = int(raw_rate) if raw_rate is not None else None
    if rate is not None and not 120 <= rate <= 190:
        raise ValueError("test_speaking_rate_out_of_bounds")
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    target = output_path or ARTIFACTS / f"nova-test-{uuid.uuid4().hex[:12]}.wav"
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="nova-tts-") as folder:
        aiff = Path(folder) / "speech.aiff"
        say_command = ["/usr/bin/say"]
        if voice_name:
            say_command.extend(["-v", voice_name])
        if rate is not None:
            say_command.extend(["-r", str(rate)])
        say_command.extend(["-o", str(aiff), text])
        subprocess.run(say_command, check=True,
                       capture_output=True, timeout=30)
        subprocess.run(["/usr/local/bin/ffmpeg", "-nostdin", "-v", "error", "-y",
                        "-i", str(aiff), "-ac", "1", "-ar", "16000",
                        "-c:a", "pcm_s16le", str(target)], check=True,
                       capture_output=True, timeout=30)
    probe = subprocess.run(["/usr/local/bin/ffprobe", "-v", "error", "-show_entries",
                            "format=duration:stream=codec_name,sample_rate,channels",
                            "-of", "json", str(target)], check=True,
                           capture_output=True, text=True, timeout=10)
    info = json.loads(probe.stdout)
    duration = float(info.get("format", {}).get("duration", 0))
    streams = info.get("streams", [])
    if not duration or not streams or streams[0].get("codec_name") != "pcm_s16le":
        target.unlink(missing_ok=True)
        raise RuntimeError("test_tts_wav_validation_failed")
    return {"provider": "macOS_say_TEST_ONLY", "voice_name": voice_name or "system_default",
            "speaking_rate_wpm": rate,
            "mime_type": "audio/wav",
            "path": str(target), "duration_seconds": duration,
            "sample_rate": int(streams[0].get("sample_rate", 0)),
            "channels": int(streams[0].get("channels", 0)),
            "size_bytes": target.stat().st_size}
