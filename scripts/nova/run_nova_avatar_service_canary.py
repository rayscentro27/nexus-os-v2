#!/usr/bin/env python3
"""One bounded Modal-backed Nova service/session canary (three turns max)."""
from __future__ import annotations

import base64
from contextlib import nullcontext
import hashlib
import json
import os
import socket
import struct
import sys
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ["MODAL_PROFILE"] = "goclearonline"
os.environ["NOVA_TEST_TTS_PROVIDER"] = "macos_say"
os.environ["NOVA_AVATAR_RENDER_ENABLED"] = "1"

import modal  # noqa: E402
from deploy.modal.nova_musetalk_canary import app, render_cached  # noqa: E402
from scripts.nexus_agent_platform import nova_avatar_service as service  # noqa: E402


def request(base: str, path: str, payload: dict[str, Any] | None = None) -> tuple[int, dict[str, Any] | bytes]:
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(base + path, data=body, method="POST" if body is not None else "GET",
                                 headers={"Content-Type": "application/json"} if body is not None else {})
    with urllib.request.urlopen(req, timeout=900) as res:
        raw = res.read()
        content_type = res.headers.get("Content-Type", "")
        return res.status, (json.loads(raw) if content_type.startswith("application/json") else raw)


class WSProbe:
    def __init__(self, port: int, session_id: str):
        self.socket = socket.create_connection(("127.0.0.1", port), timeout=10)
        self.socket.settimeout(2)
        key = base64.b64encode(os.urandom(16)).decode()
        self.socket.sendall((f"GET /stream?session_id={session_id} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
                             "Upgrade: websocket\r\nConnection: Upgrade\r\n"
                             f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        header = b""
        while b"\r\n\r\n" not in header:
            header += self.socket.recv(1024)
            if len(header) > 8192:
                raise RuntimeError("websocket_handshake_header_limit")
        if b"101 Switching Protocols" not in header:
            raise RuntimeError("websocket_upgrade_failed")
        self.events: list[dict[str, Any]] = []
        self.running = True
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()

    def _read(self) -> None:
        while self.running:
            try:
                head = self._read_n(2)
                opcode, length = head[0] & 0x0F, head[1] & 0x7F
                if length == 126:
                    length = struct.unpack("!H", self._read_n(2))[0]
                elif length == 127:
                    length = struct.unpack("!Q", self._read_n(8))[0]
                if length > 200_000:
                    return
                payload = self._read_n(length)
                if opcode == 8:
                    return
                if opcode == 1:
                    self.events.append(json.loads(payload))
            except (OSError, TimeoutError, ValueError, json.JSONDecodeError):
                continue

    def _read_n(self, n: int) -> bytes:
        data = b""
        while len(data) < n:
            chunk = self.socket.recv(n - len(data))
            if not chunk:
                raise OSError("websocket_closed")
            data += chunk
        return data

    def close(self) -> None:
        self.running = False
        try:
            mask = os.urandom(4)
            self.socket.sendall(bytes([0x88, 0x80]) + mask)
        except OSError:
            pass
        self.socket.close()
        self.thread.join(timeout=2)


from scripts.nexus_agent_platform.provider_enforcement import governed_modal_canary

@governed_modal_canary
def main() -> dict[str, Any]:
    OUT = ROOT / "artifacts/nova/avatar-canary"
    OUT.mkdir(parents=True, exist_ok=True)
    label = os.environ.get("NOVA_CANARY_LABEL", "").strip()
    if label and not all(c.isalnum() or c in "-_" for c in label):
        raise ValueError("invalid_nova_canary_label")
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    server = service.create_server("127.0.0.1", port)
    deployed = os.environ.get("NOVA_USE_DEPLOYED_MODAL") == "1"
    service._MODAL_RENDER_FUNCTION = (
        modal.Function.from_name("nexus-creative-gpu-worker", "nova_live_avatar")
        if deployed else render_cached
    )
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.2}, daemon=True)
    turns = (["Hello Ray. I am Nova. The live avatar pipeline is now connected."] if deployed else [
        "Hello Ray. I am Nova. The live avatar pipeline is now connected.",
        "My approved identity cache is being reused for this session.",
        "I can keep speaking when the avatar service is unavailable.",
    ])
    record: dict[str, Any] = {"started_at": datetime.now(timezone.utc).isoformat(),
                              "provider": "Modal", "modal_app": "nexus-creative-gpu-worker",
                              "modal_function": "nova_live_avatar", "deployment_mode": "PERSISTENT_DEPLOYMENT" if deployed else "BOUNDED_APP_RUN",
                              "gpu_type": "T4",
                              "tts_provider": "macOS_say_TEST_ONLY", "turns": []}
    thread.start()
    base = f"http://127.0.0.1:{port}"
    probe: WSProbe | None = None
    try:
        run_context = nullcontext() if deployed else app.run()
        with modal.enable_output(), run_context:
            status, health = request(base, "/health")
            if status != 200 or health.get("reference", {}).get("valid") is not True:
                raise RuntimeError("avatar_service_health_or_reference_failed")
            _, session = request(base, "/session", {})
            session_id = str(session["session_id"])
            probe = WSProbe(port, session_id)
            for i, text in enumerate(turns, start=1):
                started = time.monotonic()
                code, result = request(base, "/speak", {"session_id": session_id, "text": text})
                elapsed = round(time.monotonic() - started, 3)
                if code != 200 or result.get("status") != "AVATAR_RENDERED":
                    record["turns"].append({"turn": i, "status": result.get("status"), "response": result,
                                            "elapsed_seconds": elapsed})
                    record["status"] = "PARTIAL_RENDER_FAILED"
                    break
                video_url = base + result["media"]["media_url"]
                audio_url = base + result["render_evidence"]["audio"]["media_url"]
                _, video_bytes = request(base, result["media"]["media_url"])
                _, audio_bytes = request(base, result["render_evidence"]["audio"]["media_url"])
                video_hash = hashlib.sha256(video_bytes).hexdigest()
                audio_hash = hashlib.sha256(audio_bytes).hexdigest()
                if video_hash != result["media"]["sha256"]:
                    raise RuntimeError("service_video_media_hash_mismatch")
                if audio_hash != result["render_evidence"]["audio"]["sha256"]:
                    raise RuntimeError("service_audio_media_hash_mismatch")
                artifact = (OUT / (f"{label}.mp4" if label else "nova-live-deployed-smoke.mp4") if deployed else
                            OUT / ("nova-live-session.mp4" if i == 1 else f"nova-live-session-turn-{i}.mp4"))
                artifact.write_bytes(video_bytes)
                record["turns"].append({"turn": i, "status": result["status"], "text": text,
                                        "elapsed_seconds": elapsed, "reference_sha256": result["render_evidence"]["reference_sha256"],
                                        "identity_cache_reused": result["render_evidence"]["identity_cache_reused"],
                                        "audio_duration_seconds": result["render_evidence"]["audio"]["duration_seconds"],
                                        "video_duration_seconds": result["render_evidence"]["video"]["duration_seconds"],
                                        "audio_url": audio_url, "audio_sha256": audio_hash,
                                        "video_url": video_url, "video_path": str(artifact),
                                        "video_sha256": video_hash, "video_bytes": len(video_bytes),
                                        "gpu_type": result["render_evidence"]["gpu_type"],
                                        "modal_runtime_seconds": result["render_evidence"]["runtime_seconds"]})
            time.sleep(1)
            _, stopped = request(base, "/stop", {"session_id": session_id})
            record["stop"] = stopped
            record["websocket_events"] = list(probe.events)
            record["media_ready_events"] = [e for e in probe.events if e.get("type") == "media_ready"]
            record["health"] = health
            record["session_id"] = session_id
            record["completed_at"] = datetime.now(timezone.utc).isoformat()
            if record.get("status") != "PARTIAL_RENDER_FAILED":
                expected_turns = 1 if deployed else 3
                record["status"] = "PASS_REAL_MODAL_SERVICE_CANARY" if len(record["turns"]) == expected_turns and stopped.get("state") == "IDLE" else "PARTIAL"
    finally:
        if probe:
            probe.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    result_path = OUT / (f"{label}.json" if label else
                         ("nova-live-deployed-canary.json" if deployed else "nova-live-service-canary.json"))
    result_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": record.get("status"), "turn_count": len(record["turns"]),
                      "first_video": record["turns"][0].get("video_path") if record["turns"] else None,
                      "media_ready_events": len(record.get("media_ready_events", [])),
                      "stop": record.get("stop"), "evidence": str(result_path)}, indent=2))
    return record


if __name__ == "__main__":
    main()
