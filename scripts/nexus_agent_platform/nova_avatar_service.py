"""Loopback-only Nova avatar session control and WebSocket state stream.

The optional renderer is intentionally fail-closed. Without a configured TTS
audio adapter and GPU renderer, /speak returns the text for the existing
browser-native voice-only path and never claims to have produced avatar media.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import socket
import struct
import threading
import re
import tempfile
import uuid
import time
from dataclasses import asdict
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[2]
IMAGE = ROOT / "assets/nova/avatar/nova_reference.png"
METADATA = ROOT / "assets/nova/avatar/nova_reference.json"
MAX_BODY = 8 * 1024 * 1024
MAX_MEDIA_BYTES = 6 * 1024 * 1024
MAX_SESSIONS = 2
MAX_CONNECTIONS = 4
STATES = {"IDLE", "LISTENING", "THINKING", "WORKING", "SPEAKING", "ERROR"}
_LOCK = threading.RLock()
_SESSIONS: dict[str, dict[str, Any]] = {}
_STREAMS: dict[str, set[socket.socket]] = {}
_MEDIA: dict[str, dict[str, Any]] = {}
_MODAL_RENDER_FUNCTION: Any = None
_NOVA_REMOTE_CONTROL_PLANE: Any = None
_NOVA_MODAL_HOST_ID = "modal-nova-live-avatar-host"
_NOVA_MODAL_WORKER_ID = "modal-nova-live-avatar"
_NOVA_CAPABILITY = "nova_live_avatar"
_MEDIA_ROOT = ROOT / ".runtime/nova/avatar-media"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def current_reference() -> dict[str, Any]:
    try:
        metadata = json.loads(METADATA.read_text())
        digest = hashlib.sha256(IMAGE.read_bytes()).hexdigest()
        valid = metadata.get("approval_status") == "approved" and metadata.get("sha256") == digest
        return {"valid": valid, "sha256": digest, "path": str(IMAGE)}
    except (OSError, ValueError, TypeError):
        return {"valid": False, "sha256": None, "path": str(IMAGE)}


def _frame(opcode: int, payload: bytes) -> bytes:
    size = len(payload)
    head = bytes([0x80 | opcode])
    if size < 126:
        head += bytes([size])
    elif size < 65536:
        head += bytes([126]) + struct.pack("!H", size)
    else:
        head += bytes([127]) + struct.pack("!Q", size)
    return head + payload


def _send_event(session_id: str, event: dict[str, Any]) -> None:
    payload = _frame(1, json.dumps(event, separators=(",", ":")).encode())
    with _LOCK:
        clients = list(_STREAMS.get(session_id, set()))
    for client in clients:
        try:
            client.sendall(payload)
        except OSError:
            with _LOCK:
                _STREAMS.get(session_id, set()).discard(client)


def _persist_media(session_id: str, raw: bytes, mime_type: str) -> dict[str, Any]:
    if mime_type not in {"video/mp4", "audio/wav"} or not raw or len(raw) > MAX_MEDIA_BYTES:
        raise ValueError("bounded_media_payload_required")
    digest = hashlib.sha256(raw).hexdigest()
    media_id = secrets.token_hex(16)
    _MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    suffix = ".mp4" if mime_type == "video/mp4" else ".wav"
    media_path = _MEDIA_ROOT / f"{media_id}{suffix}"
    media_path.write_bytes(raw)
    media = {"media_id": media_id, "session_id": session_id, "path": str(media_path),
             "mime_type": mime_type, "sha256": digest, "size_bytes": len(raw), "created_at": _now()}
    with _LOCK:
        _MEDIA[media_id] = media
    return {**media, "media_url": f"/media?id={media_id}"}


def _control_plane() -> Any:
    """Register Nova's governed Modal route in the existing Nexus worker plane."""
    global _NOVA_REMOTE_CONTROL_PLANE
    if _NOVA_REMOTE_CONTROL_PLANE is not None:
        return _NOVA_REMOTE_CONTROL_PLANE
    from scripts.nexus_agent_platform.remote_control_plane import (
        Capability, CapabilityHealth, Host, RemoteWorkerControlPlane, Worker,
    )
    registry_path = ROOT / "data/runtime/nexus_worker_registry.json"
    try:
        registry = json.loads(registry_path.read_text())
        worker_record = next(row for row in registry.get("workers", [])
                             if row.get("worker_id") == _NOVA_MODAL_WORKER_ID)
    except (OSError, ValueError, StopIteration) as exc:
        raise RuntimeError("nova_modal_worker_registry_record_unavailable") from exc
    if (_NOVA_CAPABILITY not in worker_record.get("capabilities", [])
            or worker_record.get("availability") != "available"
            or worker_record.get("health") != "PASS_REAL_BOUNDED"):
        raise RuntimeError("nova_modal_worker_registry_record_not_ready")
    route = worker_record["control_plane"]
    plane = RemoteWorkerControlPlane()
    plane.register_capability(Capability(
        _NOVA_CAPABILITY, "Cached-identity Nova MuseTalk render on bounded Modal T4",
        "Real Modal service canary; approved image/cache hashes and output receipts",
        resource_requirements={"provider": "Modal", "gpu": "T4", "max_containers": 1,
                               "max_output_bytes": MAX_MEDIA_BYTES},
    ))
    plane.register_host(Host(
        route["host_id"], route["host_type"], route["status"], route["reachable"],
        route["execution_method"], tuple(route["capabilities"]), route["concurrency"],
        route["cost_class"], route["auth_status"], route["security_class"],
    ))
    plane.register_worker(Worker(
        worker_record["worker_id"], route["host_id"], worker_record["provider"], worker_record["execution_type"],
        status="READY", certified_capabilities=worker_record["certified_capabilities"],
        department_allowlist=tuple(worker_record["department_allowlist"]), health_state="ONLINE",
        concurrency_limit=worker_record["max_concurrency"], cost_class=worker_record["cost_class"],
        security_class=worker_record["security_scope"],
    ))
    plane.set_capability_health(CapabilityHealth(
        route["host_id"], _NOVA_CAPABILITY, "Modal serverless T4", service="DEPLOYED",
        model="MuseTalk " + "0a89dec45a0192b824e3cf4daf96c239440c5ed8",
        inference="PASS_REAL_BOUNDED", status="HEALTHY",
    ))
    _NOVA_REMOTE_CONTROL_PLANE = plane
    return plane


def _persist_control_plane_receipt(job: Any, result: Any) -> str:
    path = ROOT / "reports/runtime/nova_avatar_remote_worker_control_plane_latest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    result_data = asdict(result)
    payload = result_data.get("result") or {}
    payload.pop("video_bytes", None)
    snapshot = _control_plane().snapshot()
    for receipt in snapshot.get("receipts", []):
        (receipt.get("result") or {}).pop("video_bytes", None)
    report = {"schema_version": "nexus.remote-worker-control-plane-receipt.v1",
              "capability": _NOVA_CAPABILITY, "provider": "Modal", "deployment": "nexus-creative-gpu-worker/nova_live_avatar",
              "job": asdict(job), "worker": _NOVA_MODAL_WORKER_ID,
              "host": _NOVA_MODAL_HOST_ID, "result": result_data,
              "control_plane": snapshot, "recorded_at": _now()}
    path.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return str(path)


def _render_test_turn(session_id: str, text: str) -> dict[str, Any]:
    """Canary-only path: explicit test TTS, approved cache, governed Modal function."""
    if os.environ.get("NOVA_AVATAR_RENDER_ENABLED") != "1":
        raise RuntimeError("avatar_renderer_not_enabled")
    ref = current_reference()
    if not ref["valid"]:
        raise RuntimeError("approved_reference_invalid")
    cache_path = ROOT / "artifacts/nova/avatar-canary/nova-identity-cache.pt"
    if not cache_path.is_file():
        raise RuntimeError("approved_identity_cache_missing")
    from scripts.nexus_agent_platform.nova_tts_adapter import synthesize_test_wav
    request_id = uuid.uuid4().hex
    audio_info = synthesize_test_wav(text, output_path=_MEDIA_ROOT / f"{request_id}.wav")
    audio_bytes = Path(audio_info["path"]).read_bytes()
    # Validate the known cache provenance from the prior GPU execution receipt.
    receipt_path = ROOT / "artifacts/nova/avatar-canary/modal-render-result.json"
    try:
        receipt = json.loads(receipt_path.read_text())
    except (OSError, ValueError) as exc:
        raise RuntimeError("identity_cache_receipt_unavailable") from exc
    if receipt.get("identity_cache_key") != ref["sha256"]:
        raise RuntimeError("identity_cache_reference_hash_mismatch")
    if receipt.get("identity_cache_path") != str(cache_path):
        raise RuntimeError("identity_cache_path_mismatch")
    if receipt.get("identity_cache_sha256") != hashlib.sha256(cache_path.read_bytes()).hexdigest():
        raise RuntimeError("identity_cache_digest_mismatch")
    function = _MODAL_RENDER_FUNCTION
    if function is None:
        import modal
        os.environ.setdefault("MODAL_PROFILE", "goclearonline")
        function = modal.Function.from_name("nexus-creative-gpu-worker", "nova_live_avatar")
    from scripts.nexus_agent_platform.remote_control_plane import RemoteJob
    plane = _control_plane()
    job = RemoteJob(
        job_id=f"nova-avatar-{request_id}", work_id=request_id, objective_id=_NOVA_CAPABILITY,
        department="NOVA_AVATAR", required_capability=_NOVA_CAPABILITY,
        input_refs=[f"reference_sha256:{ref['sha256']}",
                    f"identity_cache_sha256:{receipt['identity_cache_sha256']}",
                    f"audio_sha256:{hashlib.sha256(audio_bytes).hexdigest()}"],
        limits={"timeout_seconds": 900, "max_output_bytes": MAX_MEDIA_BYTES,
                "gpu_type": "T4", "max_containers": 1}, timeout=900,
        cost_budget="METERED_GPU",
        security_policy={"approved_reference_only": True, "no_live_trading": True,
                         "no_publication": True, "no_external_side_effects": True},
        correlation_ids={"request_id": request_id, "session_id": session_id},
    )
    started = time.monotonic()
    def invoke(_job: Any, _worker: Any, _host: Any) -> dict[str, Any]:
        return function.remote(IMAGE.read_bytes(), audio_bytes, cache_path.read_bytes(), ref["sha256"], request_id)
    from scripts.nexus_agent_platform.provider_enforcement import execute
    estimate = {"requests": 1, "operations": 1, "gpu_seconds": float(os.environ.get("NEXUS_MODAL_GPU_SECONDS_ESTIMATE", "900")), "billable": True}
    try: estimate["cost"] = float(os.environ["NEXUS_MODAL_ESTIMATED_COST_PER_JOB"])
    except (KeyError, ValueError): pass
    control_result = execute("MODAL", "nova_avatar_render", "GPU_GENERATION", estimate,
        lambda: plane.submit(job, claimed_by="nova_avatar_service", fn=invoke),
        job_id=job.job_id, job_type="NOVA_AVATAR_RENDER", correlation_id=request_id,
        actual_usage=lambda _result: {"requests": 1, "operations": 1, "gpu_seconds": estimate["gpu_seconds"], **({"cost": estimate["cost"]} if "cost" in estimate else {})})
    valid_receipt, receipt_status = plane.validate_receipt(control_result)
    if not valid_receipt or control_result.status != "SUCCEEDED":
        _persist_control_plane_receipt(job, control_result)
        raise RuntimeError("remote_worker_control_plane_render_failed:" + receipt_status)
    result = control_result.result
    _persist_control_plane_receipt(job, control_result)
    if result.get("status") != "SUCCESS" or result.get("reference_sha256") != ref["sha256"]:
        raise RuntimeError("modal_avatar_render_failed")
    # Apply the Ray-approved Candidate B color-only pass to the raw MuseTalk
    # output. No geometry replacement, rest-pose injection, or temporal blend.
    from scripts.nova.nova_lip_color_pipeline import apply_candidate_b
    with tempfile.TemporaryDirectory(prefix="nova-lip-color-b-") as work_dir:
        raw_path = Path(work_dir) / "musetalk-raw.mp4"
        corrected_path = Path(work_dir) / "lip-color-b.mp4"
        raw_path.write_bytes(result["video_bytes"])
        lip_color_receipt = apply_candidate_b(raw_path, corrected_path)
        video_bytes = corrected_path.read_bytes()
    video_media = _persist_media(session_id, video_bytes, "video/mp4")
    audio_media = _persist_media(session_id, audio_bytes, "audio/wav")
    return {"request_id": request_id, "provider": "Modal", "gpu_type": result.get("gpu_type"),
            "musetalk_commit": result.get("musetalk_commit"), "reference_sha256": ref["sha256"],
            "identity_cache_reused": result.get("identity_cache_reused") is True,
            "lip_color_pipeline": lip_color_receipt,
            "audio": {**audio_info, "media_url": audio_media["media_url"], "sha256": audio_media["sha256"]},
            "video": {**video_media, "duration_seconds": lip_color_receipt["video_duration_output"]},
            "runtime_seconds": result.get("runtime_seconds"),
            "control_plane_receipt": "reports/runtime/nova_avatar_remote_worker_control_plane_latest.json",
            "service_elapsed_seconds": round(time.monotonic() - started, 3),
            "modal_started_at": result.get("started_at"), "modal_completed_at": result.get("completed_at")}


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address: Any, handler: Any):
        self._request_slots = threading.BoundedSemaphore(MAX_CONNECTIONS)
        super().__init__(server_address, handler)

    def process_request(self, request: socket.socket, client_address: Any) -> None:
        if not self._request_slots.acquire(blocking=False):
            try:
                request.sendall(b"HTTP/1.1 503 Service Unavailable\r\nConnection: close\r\nContent-Length: 0\r\n\r\n")
            finally:
                self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self._request_slots.release()
            raise

    def process_request_thread(self, request: socket.socket, client_address: Any) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._request_slots.release()


class Handler(BaseHTTPRequestHandler):
    server_version = "NexusNovaAvatar/1.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, *_: Any) -> None:
        # Never write speech text, audio, session tokens, or request bodies.
        return

    def _reply(self, status: int, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _body(self) -> dict[str, Any]:
        size = int(self.headers.get("Content-Length", "0"))
        if size < 0 or size > MAX_BODY:
            raise ValueError("request_body_limit")
        raw = self.rfile.read(size)
        data = json.loads(raw or b"{}")
        if not isinstance(data, dict):
            raise ValueError("object_body_required")
        return data

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        if parsed.path == "/nova-avatar-lab":
            harness = ROOT / "public/nova-avatar-lab.html"
            try:
                raw = harness.read_bytes()
            except OSError:
                self._reply(404, {"error": "temporary_avatar_harness_not_found"})
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)
            return
        if parsed.path == "/health":
            ref = current_reference()
            with _LOCK:
                active = sum(1 for x in _SESSIONS.values() if x["state"] != "IDLE")
            test_tts = os.environ.get("NOVA_TEST_TTS_PROVIDER") == "macos_say"
            service_status = "READY_TEST_TTS" if ref["valid"] and test_tts else ("DEGRADED_TTS_UNAVAILABLE" if ref["valid"] else "DEGRADED_REFERENCE_INVALID")
            self._reply(200, {"status": service_status,
                              "service": "nova_avatar_session_control", "states": sorted(STATES),
                              "reference": ref, "tts_provider": "macOS_say_TEST_ONLY" if test_tts else "NOT_CONFIGURED_BROWSER_SPEECH_SYNTHESIS_ONLY",
                              "renderer": "Modal:nova_live_avatar" if os.environ.get("NOVA_AVATAR_RENDER_ENABLED") == "1" else "NOT_CONNECTED_MODAL_ARTIFACT_HANDOFF_ONLY", "active_sessions": active,
                              "media_stream": {"mode": "WEBSOCKET_STATE_CONTROL_PLUS_ARTIFACT_URL", "ready": True},
                              "fallback": "VOICE_ONLY"})
            return
        if parsed.path == "/media":
            media_id = parse_qs(parsed.query).get("id", [""])[0]
            if not re.fullmatch(r"[a-f0-9]{32}", media_id):
                self._reply(404, {"error": "media_not_found"})
                return
            with _LOCK:
                media = _MEDIA.get(media_id)
            if not media:
                self._reply(404, {"error": "media_not_found"})
                return
            try:
                raw = Path(media["path"]).read_bytes()
            except OSError:
                self._reply(404, {"error": "media_not_found"})
                return
            self.send_response(200)
            self.send_header("Content-Type", media["mime_type"])
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-SHA256", media["sha256"])
            self.end_headers()
            self.wfile.write(raw)
            return
        if parsed.path != "/stream":
            self._reply(404, {"error": "not_found"})
            return
        origin = self.headers.get("Origin")
        if origin:
            origin_url = urlsplit(origin)
            if origin_url.scheme != "http" or origin_url.hostname not in {"127.0.0.1", "localhost", "::1"}:
                self._reply(403, {"error": "origin_not_allowed"})
                return
        session_id = parse_qs(parsed.query).get("session_id", [""])[0]
        with _LOCK:
            session = _SESSIONS.get(session_id)
            stream_exists = bool(_STREAMS.get(session_id))
        if not session:
            self._reply(404, {"error": "session_not_found"})
            return
        if stream_exists:
            self._reply(429, {"error": "stream_already_attached"})
            return
        if self.headers.get("Upgrade", "").lower() != "websocket":
            self._reply(426, {"error": "websocket_upgrade_required"})
            return
        key = self.headers.get("Sec-WebSocket-Key", "")
        if not key:
            self._reply(400, {"error": "websocket_key_required"})
            return
        import hashlib as _hashlib
        import base64 as _base64
        accept = _base64.b64encode(_hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()).decode()
        self.send_response(101, "Switching Protocols")
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept)
        self.end_headers()
        client = self.connection
        with _LOCK:
            _STREAMS.setdefault(session_id, set()).add(client)
        try:
            self.wfile.write(_frame(1, json.dumps({"type": "session_state", "session_id": session_id,
                                                   "state": session["state"], "at": _now()}).encode()))
            self.wfile.flush()
            while True:
                first = self.rfile.read(2)
                if len(first) < 2:
                    break
                opcode = first[0] & 0x0F
                length = first[1] & 0x7F
                masked = bool(first[1] & 0x80)
                if length == 126:
                    length = struct.unpack("!H", self.rfile.read(2))[0]
                elif length == 127:
                    length = struct.unpack("!Q", self.rfile.read(8))[0]
                if length > 4096:
                    break
                mask = self.rfile.read(4) if masked else b""
                payload = self.rfile.read(length)
                if opcode == 8:
                    try: self.wfile.write(_frame(8, b"")); self.wfile.flush()
                    except OSError: pass
                    break
                if opcode == 9:
                    self.wfile.write(_frame(10, payload)); self.wfile.flush()
        except (OSError, ConnectionError):
            pass
        finally:
            with _LOCK:
                _STREAMS.get(session_id, set()).discard(client)
        return

    def do_POST(self) -> None:
        try:
            body = self._body()
        except (ValueError, json.JSONDecodeError):
            self._reply(400, {"error": "invalid_or_oversized_json"})
            return
        if self.path == "/session":
            ref = current_reference()
            if not ref["valid"]:
                self._reply(503, {"error": "approved_reference_invalid"})
                return
            session_id = "nova_" + secrets.token_urlsafe(18)
            session = {"session_id": session_id, "state": "IDLE", "created_at": _now(),
                       "updated_at": _now(), "reference_sha256": ref["sha256"], "turn_count": 0}
            with _LOCK:
                if len(_SESSIONS) >= MAX_SESSIONS:
                    self._reply(429, {"error": "session_limit", "limit": MAX_SESSIONS})
                    return
                _SESSIONS[session_id] = session
                _STREAMS[session_id] = set()
            self._reply(201, session)
            return
        if self.path not in {"/speak", "/stop", "/state", "/media"}:
            self._reply(404, {"error": "not_found"})
            return
        session_id = str(body.get("session_id") or "")
        with _LOCK:
            session = _SESSIONS.get(session_id)
            if not session:
                self._reply(404, {"error": "session_not_found"})
                return
            if self.path == "/stop":
                session.update(state="IDLE", updated_at=_now())
                stale_media = [key for key, item in _MEDIA.items() if item.get("session_id") == session_id]
                for key in stale_media:
                    item = _MEDIA.pop(key)
                    try:
                        Path(item["path"]).unlink(missing_ok=True)
                    except OSError:
                        pass
                event = {"type": "session_state", "session_id": session_id, "state": "IDLE", "reason": "STOPPED", "at": _now()}
                self._reply(200, {"status": "STOPPED", "state": "IDLE", "session_id": session_id})
                _send_event(session_id, event)
                return
            if self.path == "/state":
                state = str(body.get("state") or "")
                if state not in STATES:
                    self._reply(400, {"error": "unsupported_state", "allowed": sorted(STATES)})
                    return
                session.update(state=state, updated_at=_now())
                event = {"type": "session_state", "session_id": session_id, "state": state, "at": _now()}
                self._reply(200, {"status": "STATE_UPDATED", "session_id": session_id, "state": state})
                _send_event(session_id, event)
                return
            if self.path == "/media":
                if not current_reference()["valid"]:
                    self._reply(503, {"error": "approved_reference_invalid"})
                    return
                encoded = str(body.get("media_base64") or "")
                mime_type = str(body.get("mime_type") or "video/mp4")
                if mime_type not in {"video/mp4", "audio/wav"} or not encoded or len(encoded) > ((MAX_MEDIA_BYTES + 2) // 3) * 4:
                    self._reply(400, {"error": "bounded_video_mp4_required"})
                    return
                try:
                    media_bytes = base64.b64decode(encoded, validate=True)
                except (ValueError, TypeError):
                    self._reply(400, {"error": "invalid_media_encoding"})
                    return
                if not media_bytes or len(media_bytes) > MAX_MEDIA_BYTES:
                    self._reply(413, {"error": "media_size_limit", "max_bytes": MAX_MEDIA_BYTES})
                    return
                digest = hashlib.sha256(media_bytes).hexdigest()
                expected = str(body.get("sha256") or "")
                if not re.fullmatch(r"[a-f0-9]{64}", expected) or digest != expected:
                    self._reply(400, {"error": "media_hash_mismatch"})
                    return
                stored = _persist_media(session_id, media_bytes, mime_type)
                media_id = stored["media_id"]
                media_path = Path(stored["path"])
                media = stored
                session.update(state="SPEAKING", updated_at=_now())
                event = {"type": "media_ready", "session_id": session_id,
                         "state": "SPEAKING", "media_id": media_id,
                         "media_url": f"/media?id={media_id}", "mime_type": mime_type,
                         "sha256": digest, "size_bytes": len(media_bytes), "at": _now()}
                self._reply(201, {"status": "MEDIA_READY", **event})
                _send_event(session_id, event)
                return
            text = str(body.get("text") or "").strip()
            if not text or len(text) > 4000:
                self._reply(400, {"error": "text_required_or_too_long"})
                return
            session["state"] = "THINKING"
            session["updated_at"] = _now()
            session["turn_count"] += 1
            event = {"type": "session_state", "session_id": session_id, "state": "THINKING", "at": _now()}
        _send_event(session_id, event)
        _send_event(session_id, {"type": "session_state", "session_id": session_id, "state": "WORKING", "at": _now()})
        try:
            rendered = _render_test_turn(session_id, text)
            with _LOCK:
                session.update(state="SPEAKING", updated_at=_now())
            event = {"type": "media_ready", "session_id": session_id, "state": "SPEAKING",
                     "media_id": rendered["video"]["media_id"], "media_url": rendered["video"]["media_url"],
                     "mime_type": "video/mp4", "sha256": rendered["video"]["sha256"],
                     "audio_url": rendered["audio"]["media_url"], "audio_duration_seconds": rendered["audio"]["duration_seconds"],
                     "gpu_type": rendered["gpu_type"], "identity_cache_reused": rendered["identity_cache_reused"], "at": _now()}
            response = {"status": "AVATAR_RENDERED", "session_id": session_id, "state": "SPEAKING",
                        "text": text, "tts_provider": "macOS_say_TEST_ONLY", "audio_buffer_available": True,
                        "avatar_rendered": True, "media": event, "render_evidence": rendered}
            self._reply(200, response)
            _send_event(session_id, event)
        except Exception as exc:
            with _LOCK:
                session.update(state="WORKING", updated_at=_now())
            # Safe degradation: the test TTS bytes remain available as voice-only
            # media if GPU/model rendering is unavailable.
            try:
                from scripts.nexus_agent_platform.nova_tts_adapter import synthesize_test_wav
                audio_info = synthesize_test_wav(text, output_path=_MEDIA_ROOT / f"fallback-{uuid.uuid4().hex}.wav")
                audio = _persist_media(session_id, Path(audio_info["path"]).read_bytes(), "audio/wav")
                response = {"status": "VOICE_ONLY_FALLBACK_READY", "session_id": session_id,
                            "state": "WORKING", "text": text, "tts_provider": "macOS_say_TEST_ONLY",
                            "audio_buffer_available": True, "avatar_rendered": False,
                            "audio_url": audio["media_url"], "fallback_reason": type(exc).__name__,
                            "renderer_error": re.sub(r"(?i)(token|secret|key|authorization)[=: ]+[^ ,;]+", r"\1=[REDACTED]", str(exc))[:1200]}
            except Exception:
                response = {"status": "VOICE_ONLY_FALLBACK_READY", "session_id": session_id,
                            "state": "WORKING", "text": text, "tts_path": "browser_native_speechSynthesis",
                            "audio_buffer_available": False, "avatar_rendered": False,
                            "fallback_reason": type(exc).__name__,
                            "renderer_error": re.sub(r"(?i)(token|secret|key|authorization)[=: ]+[^ ,;]+", r"\1=[REDACTED]", str(exc))[:400]}
            self._reply(200, response)


def create_server(host: str = "127.0.0.1", port: int = 8876) -> _Server:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Nova avatar control service must remain loopback-only")
    return _Server((host, port), Handler)


def main() -> None:
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8876)
    args = parser.parse_args()
    server = create_server(args.host, args.port)
    renderer = "Modal:nova_live_avatar" if os.environ.get("NOVA_AVATAR_RENDER_ENABLED") == "1" else "NOT_CONFIGURED"
    tts = "macOS_say_TEST_ONLY" if os.environ.get("NOVA_TEST_TTS_PROVIDER") == "macos_say" else "NOT_CONFIGURED"
    print(json.dumps({"event": "nova_avatar_service_started", "host": args.host,
                      "port": args.port, "media_renderer": renderer, "tts_provider": tts,
                      "fallback": "VOICE_ONLY"}))
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
