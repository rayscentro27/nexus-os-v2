"""Localhost-only, fixed voice.transcribe bridge for the admin pilot."""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .local_stt import build_voice_request, transcribe_audio_file


class VoiceHandler(BaseHTTPRequestHandler):
    server_version = "NexusVoiceLocal/1"

    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path != "/v1/voice/transcribe": self._send(404, {"error": "not-found"}); return
        configured = os.environ.get("NEXUS_VOICE_LOCAL_TOKEN")
        if configured and self.headers.get("X-Nexus-Voice-Token") != configured: self._send(401, {"error": "authentication-required"}); return
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 10 * 1024 * 1024: self._send(413, {"error": "audio-size-bounded"}); return
        session = self.headers.get("X-Nexus-Voice-Session", "local-session")
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

    def log_message(self, *_args) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8789)
    args = parser.parse_args()
    ThreadingHTTPServer((args.host, args.port), VoiceHandler).serve_forever()
    return 0


if __name__ == "__main__": raise SystemExit(main())
