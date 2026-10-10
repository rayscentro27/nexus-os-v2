"""Small, provider-neutral TTS buffer contract and safe Nova delivery fallback.

This module deliberately does not synthesize speech or render video. A real
approved TTS adapter can hand its completed audio buffer to an avatar renderer;
the same buffer remains deliverable as voice-only output if rendering fails.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class TTSAudioBuffer:
    session_id: str
    request_id: str
    mime_type: str
    audio: bytes
    duration_ms: int | None = None

    @classmethod
    def from_provider(cls, *, session_id: str, request_id: str,
                      mime_type: str, audio: bytes,
                      duration_ms: int | None = None) -> "TTSAudioBuffer":
        if not session_id or not request_id:
            raise ValueError("session_and_request_ids_required")
        if not mime_type.startswith("audio/"):
            raise ValueError("audio_mime_type_required")
        if not isinstance(audio, bytes) or not audio:
            raise ValueError("nonempty_audio_buffer_required")
        if duration_ms is not None and duration_ms <= 0:
            raise ValueError("duration_ms_must_be_positive")
        return cls(session_id, request_id, mime_type, audio, duration_ms)

    def renderer_payload(self) -> dict[str, Any]:
        return {"session_id": self.session_id, "request_id": self.request_id,
                "mime_type": self.mime_type, "audio": self.audio,
                "duration_ms": self.duration_ms}


def choose_delivery(*, tts_ready: bool, avatar_healthy: bool) -> Mapping[str, str]:
    """Keep voice delivery independent from optional avatar health."""
    if not tts_ready:
        return {"mode": "TEXT_ONLY", "reason": "TTS_UNAVAILABLE"}
    if avatar_healthy:
        return {"mode": "AVATAR_AND_AUDIO", "reason": "AVATAR_HEALTHY"}
    return {"mode": "VOICE_ONLY", "reason": "AVATAR_UNAVAILABLE_OR_FAILED"}
