"""Private, bounded Voice input contracts and local whisper.cpp adapter."""

from .local_stt import (
    AUDIO_MAX_BYTES,
    AUDIO_MAX_DURATION_MS,
    TRANSCRIPT_SCHEMA,
    VOICE_INPUT_SCHEMA,
    build_voice_request,
    transcribe_audio_file,
    validate_voice_request,
    voice_status,
)

__all__ = [
    "AUDIO_MAX_BYTES",
    "AUDIO_MAX_DURATION_MS",
    "TRANSCRIPT_SCHEMA",
    "VOICE_INPUT_SCHEMA",
    "build_voice_request",
    "transcribe_audio_file",
    "validate_voice_request",
    "voice_status",
]
