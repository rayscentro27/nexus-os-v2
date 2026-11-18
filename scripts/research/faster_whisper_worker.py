#!/usr/bin/env python3
"""Small subprocess boundary for the Python 3.12 faster-whisper backend."""
from __future__ import annotations

import json
import re
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 6:
        print("usage: faster_whisper_worker.py AUDIO TRANSCRIPT PROGRESS RESULT MODEL", file=sys.stderr)
        return 2
    audio_path, transcript_path, progress_path, result_path = map(Path, sys.argv[1:5])
    model_name = sys.argv[5]
    from faster_whisper import WhisperModel

    started = time.monotonic()
    usage_started = resource.getrusage(resource.RUSAGE_SELF)
    model = WhisperModel(model_name, device="cpu", compute_type="int8", cpu_threads=4, num_workers=1)
    segments, info = model.transcribe(str(audio_path), beam_size=1, vad_filter=True)
    pieces: list[str] = []
    captured: list[dict[str, object]] = []
    for segment in segments:
        text = re.sub(r"\s+", " ", str(segment.text or "")).strip()
        if not text:
            continue
        pieces.append(text)
        captured.append({"timestamp": f"{float(segment.start):.2f}-{float(segment.end):.2f}", "text": text})
        transcript_path.write_text(" ".join(pieces) + "\n", encoding="utf-8")
        progress_path.write_text(json.dumps({
            "asr_started_at": started,
            "audio_duration_seconds": float(info.duration),
            "model": model_name,
            "current_chunk": 1,
            "total_chunks": 1,
            "words_written": len(" ".join(pieces).split()),
            "last_progress_at": datetime.now(timezone.utc).isoformat(),
            "runtime_seconds": time.monotonic() - started,
        }), encoding="utf-8")
    transcript = " ".join(pieces).strip()
    runtime = time.monotonic() - started
    usage_finished = resource.getrusage(resource.RUSAGE_SELF)
    cpu_user_seconds = usage_finished.ru_utime - usage_started.ru_utime
    cpu_system_seconds = usage_finished.ru_stime - usage_started.ru_stime
    cpu_percent_estimate = ((cpu_user_seconds + cpu_system_seconds) / runtime / 4.0 * 100.0) if runtime else 0.0
    result_path.write_text(json.dumps({
        "transcript": transcript,
        "segments": captured,
        "audio_duration_seconds": float(info.duration),
        "runtime_seconds": runtime,
        "model": model_name,
        "words_written": len(transcript.split()),
        "cpu_user_seconds": cpu_user_seconds,
        "cpu_system_seconds": cpu_system_seconds,
        "cpu_percent_estimate": cpu_percent_estimate,
        "ram_peak_bytes": usage_finished.ru_maxrss,
    }), encoding="utf-8")
    return 0 if transcript else 1


if __name__ == "__main__":
    raise SystemExit(main())
