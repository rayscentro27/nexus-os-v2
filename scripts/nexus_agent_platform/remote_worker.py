"""Provider-neutral, capability-allowlisted Nexus CPU worker foundation.

The worker is compute only. It accepts a short-lived authenticated job, runs a
fixed capability adapter, and returns a structured result. It has no shell,
scheduler, approval, work-order, messaging, financial, or governance API.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import http.server
import json
import os
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Protocol

from scripts.nexus_agent_platform.evidence_ingestion import (
    DEFAULT_RUNTIME,
    DEFAULT_TENANT_CONTEXT,
    ingest_url,
    utc_now,
    write_json,
)

JOB_SCHEMA = "nexus.remote-job.v1"
RESULT_SCHEMA = "nexus.remote-result.v1"
MAX_REQUEST_BYTES = 128 * 1024
MAX_CLOCK_SKEW_SECONDS = 300
ALLOWED_CAPABILITIES = {
    "evidence_ingestion": {"crawl4ai", "markitdown"},
}
DENIED_CAPABILITIES = {
    "generic_shell", "arbitrary_python", "browser_agent", "computer_use",
    "social_publish", "email_send", "stripe", "trading_execution",
    "meeting_bot", "creative_gpu", "avatar", "voice", "unrestricted_http",
}


class RemoteWorkerProvider(Protocol):
    def submit(self, job: dict) -> dict: ...
    def get_status(self, job_id: str) -> dict: ...
    def cancel(self, job_id: str) -> dict: ...
    def health(self) -> dict: ...


def canonical_json(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def sign_request(payload: dict, secret: str, timestamp: str) -> str:
    message = timestamp.encode("ascii") + b"." + canonical_json(payload)
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def verify_request(payload: dict, secret: str, timestamp: str, signature: str, *, now: Optional[float] = None) -> bool:
    try:
        stamp = float(timestamp)
    except (TypeError, ValueError):
        return False
    current = time.time() if now is None else now
    if abs(current - stamp) > MAX_CLOCK_SKEW_SECONDS:
        return False
    expected = sign_request(payload, secret, timestamp)
    return hmac.compare_digest(expected, str(signature or ""))


def validate_job(job: dict) -> tuple[bool, str]:
    if not isinstance(job, dict) or job.get("schema_version") != JOB_SCHEMA:
        return False, "unsupported-schema"
    if not isinstance(job.get("job_id"), str) or not job["job_id"]:
        return False, "missing-job-id"
    capability = job.get("capability")
    adapter = job.get("adapter")
    if capability in DENIED_CAPABILITIES or capability not in ALLOWED_CAPABILITIES:
        return False, "capability-not-allowed"
    if adapter not in ALLOWED_CAPABILITIES[capability]:
        return False, "adapter-not-allowed"
    if not isinstance(job.get("tenant_context"), dict):
        return False, "missing-tenant-context"
    if not isinstance(job.get("source"), dict):
        return False, "missing-source"
    return True, "ok"


def build_remote_job(*, capability: str, adapter: str, source: dict, job_id: Optional[str] = None,
                     tenant_context: Optional[dict] = None, policy: Optional[dict] = None,
                     limits: Optional[dict] = None, correlation: Optional[dict] = None) -> dict:
    """Build the provider-neutral v1 request envelope."""
    return {
        "schema_version": JOB_SCHEMA,
        "job_id": job_id or f"job-{uuid.uuid4().hex[:16]}",
        "capability": capability,
        "adapter": adapter,
        "tenant_context": tenant_context or DEFAULT_TENANT_CONTEXT,
        "source": source,
        "policy": policy or {"public_only": adapter == "crawl4ai", "no_external_processing": True},
        "limits": limits or {"max_pages": 1, "max_depth": 0, "timeout_seconds": 30},
        "requested_at": utc_now(),
        "correlation": correlation or {},
    }


def validate_result(result: dict) -> tuple[bool, str]:
    required = ("schema_version", "job_id", "capability", "worker_id", "provider", "status", "started_at", "completed_at")
    if not isinstance(result, dict) or result.get("schema_version") != RESULT_SCHEMA:
        return False, "unsupported-schema"
    if any(not result.get(field) for field in required):
        return False, "missing-result-field"
    return True, "ok"


def validate_result_tenant(job: dict, result: dict) -> tuple[bool, str]:
    if job.get("tenant_context") != result.get("tenant_context"):
        return False, "tenant-context-mismatch"
    return True, "ok"


def _safe_job_result(job: dict, *, status: str, worker_id: str, provider: str, started: str,
                     completed: str, payload: Optional[dict] = None, error: Optional[dict] = None) -> dict:
    evidence = payload or {}
    artifact_refs = [evidence["artifact_ref"]] if evidence.get("artifact_ref") else []
    return {
        "schema_version": RESULT_SCHEMA,
        "job_id": job.get("job_id", "invalid"),
        "capability": job.get("capability", "unknown"),
        "worker_id": worker_id,
        "provider": provider,
        "status": status,
        "started_at": started,
        "completed_at": completed,
        "duration_ms": 0,
        "artifact_refs": artifact_refs,
        "receipt_ref": evidence.get("receipt_ref"),
        "usage": {"cost": "COST_UNKNOWN", "artifact_bytes": None},
        "tenant_context": job.get("tenant_context"),
        "evidence_result": evidence,
        "error": error,
    }


class CapabilityRegistry:
    """Fixed registry; unknown capabilities are denied."""

    @staticmethod
    def allows(capability: str, adapter: str) -> bool:
        return adapter in ALLOWED_CAPABILITIES.get(capability, set())


class WorkerRuntime:
    def __init__(self, *, worker_id: str, provider: str, root: Path = DEFAULT_RUNTIME,
                 shared_secret: Optional[str] = None, heartbeat_path: Optional[Path] = None):
        self.worker_id = worker_id
        self.provider = provider
        self.root = root
        self.shared_secret = shared_secret
        self.heartbeat_path = heartbeat_path or Path("reports/runtime/nexus_remote_cpu_worker_heartbeat_latest.json")
        self._slot = threading.BoundedSemaphore(1)
        self._seen_jobs: set[str] = set()
        self._lock = threading.Lock()
        self.completed_jobs = 0
        self.failed_jobs = 0
        self.last_job: Optional[dict] = None
        self._write_health("HEALTHY")

    def _write_health(self, status: str) -> dict:
        value = {
            "capability": "remote_cpu_worker", "worker_id": self.worker_id, "provider": self.provider,
            "status": status, "capabilities": {"evidence_ingestion": ["crawl4ai", "markitdown"]},
            "last_seen": utc_now(), "active_jobs": 0, "completed_jobs": self.completed_jobs,
            "failed_jobs": self.failed_jobs, "optional": True, "core_health_dependency": False,
            "arbitrary_shell": "UNAVAILABLE", "stripe": "UNAVAILABLE", "funded_trading": "UNAVAILABLE",
        }
        write_json(self.heartbeat_path, value)
        return value

    def health(self) -> dict:
        return self._write_health("HEALTHY")

    def execute(self, job: dict) -> dict:
        valid, reason = validate_job(job)
        if not valid or not CapabilityRegistry.allows(job.get("capability", ""), job.get("adapter", "")):
            now = utc_now()
            self.failed_jobs += 1
            return _safe_job_result(job if isinstance(job, dict) and job.get("job_id") else {"job_id": "invalid"}, status="SAFETY_BLOCKED", worker_id=self.worker_id, provider=self.provider, started=now, completed=utc_now(), error={"classification": reason})
        with self._lock:
            if job["job_id"] in self._seen_jobs:
                now = utc_now()
                return _safe_job_result(job, status="DUPLICATE", worker_id=self.worker_id, provider=self.provider, started=now, completed=utc_now(), error={"classification": "duplicate-job-id"})
            self._seen_jobs.add(job["job_id"])
        if not self._slot.acquire(blocking=False):
            now = utc_now()
            self.failed_jobs += 1
            return _safe_job_result(job, status="WORKER_BUSY", worker_id=self.worker_id, provider=self.provider, started=now, completed=utc_now(), error={"classification": "concurrency-limit"})
        started = utc_now(); clock = time.monotonic()
        try:
            if job["adapter"] != "crawl4ai":
                # MarkItDown remains local-file scoped in Phase H; remote paths
                # are intentionally rejected rather than becoming file authority.
                raise ValueError("remote-markitdown-source-not-enabled")
            source = job["source"]
            if set(source) - {"source_type", "original_reference"}:
                raise ValueError("unsupported-source-fields")
            if source.get("source_type") != "public_url":
                raise ValueError("crawl4ai-requires-public-url")
            payload = ingest_url(source["original_reference"], job_id=job["job_id"], root=self.root,
                                 tenant_context=job.get("tenant_context") or DEFAULT_TENANT_CONTEXT,
                                 timeout_seconds=min(int((job.get("limits") or {}).get("timeout_seconds", 30)), 30))
            result = _safe_job_result(job, status=payload.get("status", "SOURCE_UNAVAILABLE"), worker_id=self.worker_id,
                                      provider=self.provider, started=started, completed=utc_now(), payload=payload,
                                      error=payload.get("error"))
            tenant_valid, tenant_reason = validate_result_tenant(job, result)
            if not tenant_valid:
                result["status"] = "SAFETY_BLOCKED"
                result["error"] = {"classification": tenant_reason}
            result["duration_ms"] = int((time.monotonic() - clock) * 1000)
            self.last_job = {"job_id": job["job_id"], "status": result["status"], "completed_at": result["completed_at"]}
            if result["status"] in {"SUCCESS", "DUPLICATE", "NO_CHANGE"}:
                self.completed_jobs += 1
            else:
                self.failed_jobs += 1
            return result
        except Exception as exc:
            self.failed_jobs += 1
            result = _safe_job_result(job, status="SAFETY_BLOCKED" if "not-enabled" in str(exc) else "SOURCE_UNAVAILABLE",
                                      worker_id=self.worker_id, provider=self.provider, started=started, completed=utc_now(),
                                      error={"classification": "WORKER_EXECUTION_FAILED", "message": str(exc)[:300]})
            result["duration_ms"] = int((time.monotonic() - clock) * 1000)
            return result
        finally:
            self._slot.release()
            self._write_health("HEALTHY")


class InProcessRemoteWorkerProvider:
    def __init__(self, runtime: WorkerRuntime):
        self.runtime = runtime

    def submit(self, job: dict) -> dict:
        return self.runtime.execute(job)

    def get_status(self, job_id: str) -> dict:
        return {"job_id": job_id, "last_job": self.runtime.last_job}

    def cancel(self, job_id: str) -> dict:
        return {"job_id": job_id, "status": "NOT_AVAILABLE", "reason": "synchronous bounded worker"}

    def health(self) -> dict:
        return self.runtime.health()


class HttpRemoteWorkerProvider:
    def __init__(self, base_url: str, shared_secret: str, timeout: int = 35):
        self.base_url = base_url.rstrip("/")
        self.shared_secret = shared_secret
        self.timeout = timeout

    def _request(self, method: str, path: str, payload: Optional[dict] = None) -> dict:
        body = canonical_json(payload) if payload is not None else None
        timestamp = str(int(time.time()))
        headers = {"Accept": "application/json", "User-Agent": "NexusRemoteWorkerClient/1.0"}
        if body is not None:
            headers.update({"Content-Type": "application/json", "X-Nexus-Timestamp": timestamp,
                            "X-Nexus-Signature": sign_request(payload, self.shared_secret, timestamp)})
        request = urllib.request.Request(self.base_url + path, data=body, method=method, headers=headers)
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read(MAX_REQUEST_BYTES).decode("utf-8"))

    def submit(self, job: dict) -> dict:
        return self._request("POST", "/v1/jobs", job)

    def get_status(self, job_id: str) -> dict:
        return self._request("GET", "/v1/jobs/" + job_id)

    def cancel(self, job_id: str) -> dict:
        return self._request("POST", "/v1/jobs/" + job_id + "/cancel", {"job_id": job_id})

    def health(self) -> dict:
        return self._request("GET", "/health")


class _WorkerHandler(http.server.BaseHTTPRequestHandler):
    runtime: WorkerRuntime

    def log_message(self, _format: str, *args: Any) -> None:
        return

    def _send(self, status: int, value: dict) -> None:
        body = canonical_json(value)
        self.send_response(status); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health": self._send(200, self.runtime.health()); return
        if self.path.startswith("/v1/jobs/"):
            self._send(200, self.runtime.last_job or {"status": "NOT_FOUND"}); return
        self._send(404, {"error": "not-found"})

    def do_POST(self) -> None:
        if self.path != "/v1/jobs": self._send(404, {"error": "not-found"}); return
        if not self.runtime.shared_secret: self._send(503, {"error": "worker-auth-not-configured"}); return
        length = int(self.headers.get("Content-Length", "-1"))
        if length < 0 or length > MAX_REQUEST_BYTES: self._send(413, {"error": "request-too-large"}); return
        try: job = json.loads(self.rfile.read(length).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError): self._send(400, {"error": "invalid-json"}); return
        timestamp = self.headers.get("X-Nexus-Timestamp", "")
        signature = self.headers.get("X-Nexus-Signature", "")
        if not verify_request(job, self.runtime.shared_secret, timestamp, signature): self._send(401, {"error": "invalid-authentication"}); return
        valid, reason = validate_job(job)
        if not valid: self._send(403, {"error": reason}); return
        self._send(200, self.runtime.execute(job))


def serve(*, runtime: WorkerRuntime, bind: str, port: int) -> None:
    handler = type("NexusWorkerHandler", (_WorkerHandler,), {"runtime": runtime})
    server = http.server.ThreadingHTTPServer((bind, port), handler)
    try: server.serve_forever(poll_interval=0.2)
    finally: server.server_close()


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run the bounded Nexus remote CPU worker")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--worker-id", default=f"worker-{uuid.uuid4().hex[:12]}")
    parser.add_argument("--provider", default="local-container")
    parser.add_argument("--root", type=Path, default=DEFAULT_RUNTIME)
    args = parser.parse_args(argv)
    if not args.serve:
        parser.error("only fixed --serve mode is available")
    secret = os.environ.get("NEXUS_REMOTE_WORKER_SHARED_SECRET")
    if not secret: parser.error("NEXUS_REMOTE_WORKER_SHARED_SECRET is required")
    serve(runtime=WorkerRuntime(worker_id=args.worker_id, provider=args.provider, root=args.root, shared_secret=secret), bind=args.bind, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
