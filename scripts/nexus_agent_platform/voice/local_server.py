"""Localhost-only, fixed voice.transcribe bridge for the admin pilot."""
from __future__ import annotations

import argparse
from collections import defaultdict, deque
import json
import os
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .local_stt import build_voice_request, transcribe_audio_file


class VoiceLimiter:
    """Small in-process bound for the optional local voice service."""

    def __init__(self, requests_per_minute: int = 6) -> None:
        self.requests_per_minute = requests_per_minute
        self._active = 0
        self._history: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, session: str) -> bool:
        now = time.monotonic()
        with self._lock:
            history = self._history[session]
            while history and now - history[0] >= 60:
                history.popleft()
            if len(history) >= self.requests_per_minute:
                return False
            history.append(now)
            return True

    def acquire(self) -> bool:
        with self._lock:
            if self._active >= 1:
                return False
            self._active += 1
            return True

    def release(self) -> None:
        with self._lock:
            self._active = max(0, self._active - 1)


class VoiceHandler(BaseHTTPRequestHandler):
    server_version = "NexusVoiceLocal/1"

    def _allowed_origins(self) -> set[str]:
        return {item.strip() for item in os.environ.get("NEXUS_VOICE_ALLOWED_ORIGINS", "").split(",") if item.strip()}

    def _cors(self) -> None:
        origin = self.headers.get("Origin")
        if origin and origin in self._allowed_origins():
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Credentials", "true")
            self.send_header("Vary", "Origin")

    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        origin = self.headers.get("Origin")
        if origin not in self._allowed_origins():
            self._send(403, {"error": "origin-not-allowed"})
            return
        self.send_response(204)
        self._cors()
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Nexus-Voice-Session")
        self.send_header("Access-Control-Max-Age", "300")
        self.end_headers()

    def do_POST(self) -> None:
        if self.path != "/v1/voice/transcribe": self._send(404, {"error": "not-found"}); return
        origin = self.headers.get("Origin")
        if origin and origin not in self._allowed_origins(): self._send(403, {"error": "origin-not-allowed"}); return
        configured = os.environ.get("NEXUS_VOICE_LOCAL_TOKEN")
        if configured and self.headers.get("X-Nexus-Voice-Token") != configured: self._send(401, {"error": "authentication-required"}); return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send(400, {"error": "invalid-content-length"}); return
        if length <= 0 or length > 10 * 1024 * 1024: self._send(413, {"error": "audio-size-bounded"}); return
        session = self.headers.get("X-Nexus-Voice-Session", "local-session")
        if not self.server.voice_limiter.allow(session): self._send(429, {"error": "voice-rate-limited"}); return
        if not self.server.voice_limiter.acquire(): self._send(429, {"error": "voice-busy"}); return
        suffix = ".wav" if "wav" in self.headers.get("Content-Type", "") else ".webm"
        try:
            with tempfile.TemporaryDirectory(prefix="nexus-voice-upload-") as temp_dir:
                path = Path(temp_dir) / f"input{suffix}"
                path.write_bytes(self.rfile.read(length))
                request = build_voice_request(session_id=session, source="ADMIN_PORTAL", audio_format=self.headers.get("Content-Type", "audio/webm"))
                result = transcribe_audio_file(path, request)
            self._send(200, result)
        except ValueError as exc: self._send(400, {"error": str(exc)})
        except Exception: self._send(503, {"error": "voice-transcription-unavailable"})
        finally:
            self.server.voice_limiter.release()

    def log_message(self, *_args) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8789)
    args = parser.parse_args()
    if args.host != "127.0.0.1":
        raise SystemExit("voice server must remain bound to 127.0.0.1")
    server = ThreadingHTTPServer((args.host, args.port), VoiceHandler)
    server.voice_limiter = VoiceLimiter()
    server.serve_forever()
    return 0


if __name__ == "__main__": raise SystemExit(main())
