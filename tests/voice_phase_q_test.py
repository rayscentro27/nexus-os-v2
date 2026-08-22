import sys
import wave
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from nexus_agent_platform.voice.local_stt import (  # noqa: E402
    AUDIO_MAX_BYTES,
    AUDIO_MAX_DURATION_MS,
    TRANSCRIPT_SCHEMA,
    _wav_duration_ms,
    build_voice_request,
    transcribe_audio_file,
    validate_voice_request,
    voice_status,
)
import nexus_agent_platform.voice.local_stt as local_stt  # noqa: E402
from nexus_agent_platform.voice.local_server import VoiceLimiter  # noqa: E402


def test_voice_request_is_bounded_and_consent_scoped():
    request = build_voice_request(session_id="session-1", source="LOCAL_TEST")
    assert request["schema_version"] == "nexus.voice-input.v1"
    assert request["audio_retained"] is False
    assert validate_voice_request(request, audio_size=1024) == (True, "ok")


def test_voice_request_rejects_unbounded_or_unconsented_input():
    request = build_voice_request(session_id="session-1", source="LOCAL_TEST")
    assert validate_voice_request({**request, "duration_ms": 30001}, audio_size=1024)[0] is False
    assert validate_voice_request({**request, "consent_state": "UNKNOWN"}, audio_size=1024)[0] is False
    assert validate_voice_request(request, audio_size=AUDIO_MAX_BYTES + 1)[0] is False


def test_voice_transcript_contract_is_fixed():
    assert TRANSCRIPT_SCHEMA == "nexus.voice-transcript.v1"


def test_voice_runtime_status_is_optional_and_non_core():
    status = voice_status()
    assert status["stt_provider"] == "whisper.cpp"
    assert status["raw_audio_retained"] is False
    assert status["core_health_dependency"] is False


def test_voice_limiter_allows_one_active_request_and_bounds_session_rate():
    limiter = VoiceLimiter(requests_per_minute=2)
    assert limiter.allow("session-1") is True
    assert limiter.acquire() is True
    assert limiter.acquire() is False
    limiter.release()
    assert limiter.allow("session-1") is True
    assert limiter.allow("session-1") is False


def _write_wav(path: Path, duration_ms: int) -> None:
    frames = round(16_000 * duration_ms / 1000)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16_000)
        handle.writeframes(b"\0\0" * frames)


def _runtime(tmp_path: Path) -> tuple[Path, Path]:
    binary = tmp_path / "whisper-cli"
    model = tmp_path / "model.bin"
    binary.write_bytes(b"synthetic-whisper")
    model.write_bytes(b"synthetic-model")
    return binary, model


def test_wav_duration_reader_reports_normalized_frames(tmp_path):
    path = tmp_path / "normalized.wav"
    _write_wav(path, 1250)
    assert _wav_duration_ms(path) == 1250


def test_browser_style_webm_uses_normalized_wav_duration_and_whisper_input(tmp_path, monkeypatch):
    source = tmp_path / "browser-recording.webm"
    source.write_bytes(b"synthetic-browser-webm-without-container-duration")
    binary, model = _runtime(tmp_path)
    captured = {}

    def normalize(input_path, target):
        captured["source"] = input_path
        captured["wav"] = target
        _write_wav(target, 1250)

    def whisper(command, **kwargs):
        captured["command"] = command
        return SimpleNamespace(returncode=0, stdout="safe fixture text", stderr="")

    monkeypatch.setattr(local_stt, "_normalize_to_wav", normalize)
    monkeypatch.setattr(local_stt.subprocess, "run", whisper)
    result = transcribe_audio_file(source, build_voice_request(session_id="webm-test", source="LOCAL_TEST"), binary=binary, model=model)

    assert result["text"] == "safe fixture text"
    assert result["duration_ms"] == 1250
    assert captured["source"] == source
    assert Path(captured["command"][captured["command"].index("-f") + 1]).suffix == ".wav"
    assert not captured["wav"].exists()


def test_normalized_duration_at_limit_is_accepted(tmp_path, monkeypatch):
    source = tmp_path / "recording.webm"
    source.write_bytes(b"webm")
    binary, model = _runtime(tmp_path)
    monkeypatch.setattr(local_stt, "_normalize_to_wav", lambda _source, target: _write_wav(target, AUDIO_MAX_DURATION_MS))
    monkeypatch.setattr(local_stt.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout="at limit", stderr=""))
    result = transcribe_audio_file(source, build_voice_request(session_id="limit-test", source="LOCAL_TEST"), binary=binary, model=model)
    assert result["duration_ms"] == AUDIO_MAX_DURATION_MS


def test_normalized_duration_over_limit_is_rejected_before_whisper(tmp_path, monkeypatch):
    source = tmp_path / "long.webm"
    source.write_bytes(b"webm")
    binary, model = _runtime(tmp_path)
    whisper_called = False

    def whisper(*_args, **_kwargs):
        nonlocal whisper_called
        whisper_called = True
        return SimpleNamespace(returncode=0, stdout="should not run", stderr="")

    monkeypatch.setattr(local_stt, "_normalize_to_wav", lambda _source, target: _write_wav(target, AUDIO_MAX_DURATION_MS + 1))
    monkeypatch.setattr(local_stt.subprocess, "run", whisper)
    with pytest.raises(ValueError, match="audio-duration-bounded"):
        transcribe_audio_file(source, build_voice_request(session_id="long-test", source="LOCAL_TEST"), binary=binary, model=model)
    assert whisper_called is False


def test_empty_and_oversized_audio_are_rejected_before_normalization(tmp_path, monkeypatch):
    empty = tmp_path / "empty.webm"
    empty.write_bytes(b"")
    oversized = tmp_path / "oversized.webm"
    oversized.write_bytes(b"x" * (AUDIO_MAX_BYTES + 1))
    called = False

    def normalize(*_args):
        nonlocal called
        called = True

    monkeypatch.setattr(local_stt, "_normalize_to_wav", normalize)
    request = build_voice_request(session_id="size-test", source="LOCAL_TEST")
    with pytest.raises(ValueError, match="audio-size-bounded"):
        transcribe_audio_file(empty, request)
    with pytest.raises(ValueError, match="audio-size-bounded"):
        transcribe_audio_file(oversized, request)
    assert called is False


def test_malformed_audio_and_unknown_normalized_duration_fail_closed(tmp_path, monkeypatch):
    source = tmp_path / "malformed.webm"
    source.write_bytes(b"not-a-real-webm")
    binary, model = _runtime(tmp_path)
    monkeypatch.setattr(local_stt, "_normalize_to_wav", lambda _source, _target: (_ for _ in ()).throw(RuntimeError("decoder failed")))
    with pytest.raises(RuntimeError, match="decoder failed"):
        transcribe_audio_file(source, build_voice_request(session_id="malformed-test", source="LOCAL_TEST"), binary=binary, model=model)

    def unknown_duration(_source, target):
        target.write_bytes(b"not-a-wav")

    monkeypatch.setattr(local_stt, "_normalize_to_wav", unknown_duration)
    with pytest.raises(ValueError, match="audio-duration-unavailable"):
        transcribe_audio_file(source, build_voice_request(session_id="unknown-duration-test", source="LOCAL_TEST"), binary=binary, model=model)
