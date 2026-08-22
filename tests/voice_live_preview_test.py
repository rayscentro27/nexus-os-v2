import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from nexus_agent_platform.voice.local_server import PreviewLimiter  # noqa: E402
from nexus_agent_platform.voice.local_stt import build_voice_request, validate_voice_request  # noqa: E402


def test_preview_source_is_explicitly_bounded_and_consent_scoped():
    request = build_voice_request(session_id="preview-test", source="ADMIN_PORTAL_PREVIEW", audio_format="audio/webm")
    assert validate_voice_request(request, audio_size=1024) == (True, "ok")
    assert validate_voice_request({**request, "external_action_performed": True}, audio_size=1024)[0] is False


def test_preview_limiter_is_separate_and_allows_one_active_session():
    limiter = PreviewLimiter(requests_per_minute=2)
    assert limiter.allow("session") is True
    assert limiter.acquire() is True
    assert limiter.acquire() is False
    limiter.release()
    assert limiter.allow("session") is True
    assert limiter.allow("session") is False
