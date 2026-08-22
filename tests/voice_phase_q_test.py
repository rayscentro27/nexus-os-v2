import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from nexus_agent_platform.voice.local_stt import (  # noqa: E402
    AUDIO_MAX_BYTES,
    TRANSCRIPT_SCHEMA,
    build_voice_request,
    validate_voice_request,
    voice_status,
)
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
