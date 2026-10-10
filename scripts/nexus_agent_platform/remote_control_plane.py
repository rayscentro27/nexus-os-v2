"""Canonical Nexus Remote Worker Control Plane V1.

This module is deliberately provider- and department-neutral.  Existing
providers (Modal, Oracle, Mac, Kaggle, and the bounded worker runtime) can be
registered here without giving any department a second worker framework.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Iterable


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


@dataclass(frozen=True)
class Host:
    host_id: str
    host_type: str
    status: str
    reachable: bool
    execution_method: str
    capabilities: tuple[str, ...] = ()
    concurrency: int = 1
    cost_class: str = "LOCAL_FREE"
    auth_status: str = "NOT_REQUIRED"
    security_class: str = "NEXUS_PRIVATE"
    last_health_check: str | None = None


@dataclass
class Worker:
    worker_id: str
    host_id: str
    provider: str
    execution_type: str
    status: str = "REGISTERED"
    certified_capabilities: dict[str, str] = field(default_factory=dict)
    department_allowlist: tuple[str, ...] = ()
    health_state: str = "UNKNOWN"
    last_health_check: str | None = None
    concurrency_limit: int = 1
    active_jobs: int = 0
    cost_class: str = "LOCAL_FREE"
    security_class: str = "NEXUS_PRIVATE"
    network_requirements: tuple[str, ...] = ()
    credential_requirements: tuple[str, ...] = ()


@dataclass(frozen=True)
class Capability:
    capability_id: str
    description: str
    certification_source: str
    allowed_statuses: tuple[str, ...] = ("PASS_REAL", "PASS_REAL_BOUNDED")
    resource_requirements: dict[str, Any] = field(default_factory=dict)


@dataclass
class CapabilityHealth:
    host_id: str
    capability: str
    route: str
    tunnel: str = "NOT_REQUIRED"
    service: str = "UNKNOWN"
    model: str = "NOT_REQUIRED"
    inference: str = "NOT_RUN"
    status: str = "RUNTIME_REQUIRED"
    checked_at: str = field(default_factory=now)
    last_error: str | None = None


@dataclass
class Lease:
    lease_id: str
    job_id: str
    work_id: str
    worker_id: str
    host_id: str
    claimed_by: str
    status: str = "ACTIVE"
    claimed_at: str = field(default_factory=now)
    expires_at: str | None = None


@dataclass
class RemoteJob:
    job_id: str
    work_id: str
    objective_id: str
    department: str
    required_capability: str
    input_refs: list[str] = field(default_factory=list)
    limits: dict[str, Any] = field(default_factory=lambda: {"timeout_seconds": 60, "max_output_bytes": 1_000_000})
    timeout: int = 60
    cost_budget: str = "LOCAL_FREE"
    security_policy: dict[str, Any] = field(default_factory=dict)
    correlation_ids: dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=now)
    selected_worker: str | None = None
    selected_host: str | None = None


@dataclass
class RemoteResult:
    job_id: str
    worker_id: str
    host_id: str
    capability: str
    status: str
    started_at: str
    completed_at: str
    duration: float
    result: dict[str, Any] = field(default_factory=dict)
    artifact_refs: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    cost_receipt: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None
    retry_classification: str = "NONE"
    content_hash: str | None = None
    receipt_hash: str | None = None


class ControlPlaneError(RuntimeError):
    pass


class RemoteWorkerControlPlane:
    """Small deterministic control-plane core suitable for real adapters and canaries."""

    def __init__(self) -> None:
        self.hosts: dict[str, Host] = {}
        self.workers: dict[str, Worker] = {}
        self.capabilities: dict[str, Capability] = {}
        self.leases: dict[str, Lease] = {}
        self.receipts: dict[str, RemoteResult] = {}
        self.capability_health: dict[tuple[str, str], CapabilityHealth] = {}
        self._claimed_work: set[str] = set()
        self._lock = threading.Lock()

    def register_host(self, host: Host) -> None:
        self.hosts[host.host_id] = host

    def register_capability(self, capability: Capability) -> None:
        if capability.capability_id in self.capabilities:
            raise ControlPlaneError(f"duplicate capability id: {capability.capability_id}")
        self.capabilities[capability.capability_id] = capability

    def register_worker(self, worker: Worker) -> None:
        if worker.host_id not in self.hosts:
            raise ControlPlaneError(f"worker host not registered: {worker.host_id}")
        self.workers[worker.worker_id] = worker

    def select(self, job: RemoteJob) -> tuple[Worker, Host]:
        capability = self.capabilities.get(job.required_capability)
        if capability is None:
            raise ControlPlaneError("CAPABILITY_NOT_REGISTERED")
        candidates: list[tuple[tuple[Any, ...], Worker, Host]] = []
        for worker in self.workers.values():
            host = self.hosts[worker.host_id]
            certification = worker.certified_capabilities.get(job.required_capability)
            if certification not in capability.allowed_statuses:
                continue
            if worker.status not in {"REGISTERED", "READY", "ONLINE"} or worker.health_state not in {"ONLINE", "DEGRADED"}:
                continue
            if worker.department_allowlist and job.department not in worker.department_allowlist:
                continue
            if host.status not in {"ONLINE", "DEGRADED"} or not host.reachable:
                continue
            if worker.active_jobs >= min(worker.concurrency_limit, host.concurrency):
                continue
            if job.cost_budget == "LOCAL_FREE" and host.cost_class != "LOCAL_FREE":
                continue
            # Lower load, lower cost rank, then stable identifiers.
            cost_rank = {"LOCAL_FREE": 0, "REMOTE_FREE": 1, "METERED_LOW": 2, "METERED_GPU": 3, "PAID_API": 4}.get(host.cost_class, 9)
            candidates.append(((worker.active_jobs, cost_rank, worker.worker_id), worker, host))
        if not candidates:
            raise ControlPlaneError("NO_CERTIFIED_AVAILABLE_WORKER")
        _, worker, host = min(candidates, key=lambda row: row[0])
        job.selected_worker, job.selected_host = worker.worker_id, host.host_id
        return worker, host

    def claim(self, job: RemoteJob, *, claimed_by: str, lease_seconds: int = 300) -> Lease:
        with self._lock:
            if job.work_id in self._claimed_work:
                raise ControlPlaneError("DUPLICATE_WORK_CLAIM")
            if not job.selected_worker or not job.selected_host:
                raise ControlPlaneError("WORKER_SELECTION_REQUIRED")
            worker = self.workers[job.selected_worker]
            host = self.hosts[job.selected_host]
            if worker.active_jobs >= min(worker.concurrency_limit, host.concurrency):
                raise ControlPlaneError("CONCURRENCY_LIMIT")
            self._claimed_work.add(job.work_id)
            worker.active_jobs += 1
            lease = Lease(f"lease-{uuid.uuid4().hex[:16]}", job.job_id, job.work_id, worker.worker_id, host.host_id, claimed_by,
                          expires_at=datetime.fromtimestamp(time.time() + lease_seconds, timezone.utc).isoformat())
            self.leases[lease.lease_id] = lease
            return lease

    def execute(self, job: RemoteJob, lease: Lease, fn: Callable[[RemoteJob, Worker, Host], dict[str, Any]]) -> RemoteResult:
        started_at = now(); started = time.monotonic()
        worker, host = self.workers[lease.worker_id], self.hosts[lease.host_id]
        try:
            payload = fn(job, worker, host)
            status = "SUCCEEDED"
            error = None
            retry = "NONE"
        except TimeoutError as exc:
            payload, status, error, retry = {}, "TIMED_OUT", {"classification": "TIMEOUT", "message": str(exc)}, "RETRY_DIFFERENT_WORKER_OR_HOST"
        except Exception as exc:  # adapters must return failures as bounded receipts
            payload, status, error, retry = {}, "FAILED", {"classification": classify_failure(exc), "message": str(exc)[:300]}, "CLASSIFY_BEFORE_RETRY"
        completed_at = now()
        result = RemoteResult(job.job_id, worker.worker_id, host.host_id, job.required_capability, status, started_at, completed_at,
                              round(time.monotonic() - started, 6), payload if isinstance(payload, dict) else {"value": payload},
                              cost_receipt={"cost_class": worker.cost_class}, error=error, retry_classification=retry)
        result.content_hash = digest(result.result)
        result.receipt_hash = digest(asdict(result))
        self.receipts[job.job_id] = result
        worker.active_jobs = max(0, worker.active_jobs - 1)
        lease.status = "RELEASED"
        return result

    def submit(self, job: RemoteJob, *, claimed_by: str, fn: Callable[[RemoteJob, Worker, Host], dict[str, Any]]) -> RemoteResult:
        self.select(job)
        lease = self.claim(job, claimed_by=claimed_by)
        return self.execute(job, lease, fn)

    def validate_receipt(self, result: RemoteResult) -> tuple[bool, str]:
        if result.job_id not in self.receipts:
            return False, "RECEIPT_NOT_REGISTERED"
        if not result.worker_id or not result.host_id or not result.capability or not result.started_at or not result.completed_at:
            return False, "RESULT_CONTRACT_INCOMPLETE"
        if result.status == "SUCCEEDED" and not result.content_hash:
            return False, "RESULT_HASH_MISSING"
        return True, "PASS"

    def snapshot(self) -> dict[str, Any]:
        return {"hosts": [asdict(x) for x in self.hosts.values()], "workers": [asdict(x) for x in self.workers.values()],
                "capabilities": [asdict(x) for x in self.capabilities.values()], "leases": [asdict(x) for x in self.leases.values()],
                "receipts": [asdict(x) for x in self.receipts.values()],
                "capability_health": [asdict(x) for x in self.capability_health.values()]}

    def set_capability_health(self, health: CapabilityHealth) -> None:
        if health.capability not in self.capabilities:
            raise ControlPlaneError(f"CAPABILITY_NOT_REGISTERED: {health.capability}")
        self.capability_health[(health.host_id, health.capability)] = health

    def health_projection(self) -> dict[str, Any]:
        """Canonical read model consumed by Nova/Admin; no provider calls occur here."""
        return {
            "generated_at": now(),
            "hosts": [asdict(host) for host in self.hosts.values()],
            "workers": [asdict(worker) for worker in self.workers.values()],
            "capabilities": [asdict(health) for health in self.capability_health.values()],
            "active_jobs": [asdict(result) for result in self.receipts.values() if result.status == "RUNNING"],
        }


def oracle_tunnel_status(*, endpoint: str = "http://127.0.0.1:11435", model: str = "gemma3:4b") -> dict[str, Any]:
    """Check the tunnel, Ollama service, model, and a real bounded canary."""
    import urllib.request
    result: dict[str, Any] = {"endpoint": endpoint, "model": model, "public_exposure": False, "checked_at": now()}
    try:
        with urllib.request.urlopen(endpoint.rstrip("/") + "/api/version", timeout=4) as response:
            result["ollama_version"] = json.loads(response.read().decode() or "{}").get("version")
        with urllib.request.urlopen(endpoint.rstrip("/") + "/api/tags", timeout=6) as response:
            models = [item.get("name") for item in json.loads(response.read().decode() or "{}").get("models", [])]
        result["model_available"] = model in models
        if not result["model_available"]:
            result.update({"status": "CAPABILITY_UNAVAILABLE", "inference": "NOT_RUN", "error": "MODEL_NOT_PRESENT"})
            return result
        payload = json.dumps({"model": model, "prompt": "Reply exactly with NEXUS_ORACLE_TUNNEL_CANARY_OK", "stream": False, "options": {"num_predict": 20}}).encode()
        request = urllib.request.Request(endpoint.rstrip("/") + "/api/generate", data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode() or "{}")
        result["inference"] = "PASS_REAL" if "NEXUS_ORACLE_TUNNEL_CANARY_OK" in str(body.get("response", "")) else "INVALID_OUTPUT"
        result["status"] = "HEALTHY" if result["inference"] == "PASS_REAL" else "DEGRADED"
        return result
    except Exception as exc:
        result.update({"status": "OFFLINE", "inference": "NOT_RUN", "error": type(exc).__name__})
        return result


def ensure_oracle_tunnel(*, script: str = "scripts/ops/nexus_oracle_ollama_tunnel.sh", endpoint: str = "http://127.0.0.1:11435", model: str = "gemma3:4b") -> dict[str, Any]:
    """Start only the approved existing tunnel script when the route is absent."""
    before = oracle_tunnel_status(endpoint=endpoint, model=model)
    if before.get("status") == "HEALTHY":
        return {"status": "HEALTHY", "repair_attempted": False, "before": before, "after": before}
    process = subprocess.Popen([script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.monotonic() + 12
    after = oracle_tunnel_status(endpoint=endpoint, model=model)
    while time.monotonic() < deadline and after.get("status") != "HEALTHY":
        time.sleep(0.4)
        after = oracle_tunnel_status(endpoint=endpoint, model=model)
    return {"status": "HEALTHY" if after.get("status") == "HEALTHY" else "FAILED", "repair_attempted": True,
            "pid": process.pid, "before": before, "after": after, "owner": "Systems control-plane lifecycle"}


def classify_failure(exc: Exception) -> str:
    text = str(exc).lower()
    if "auth" in text or "credential" in text:
        return "AUTH_FAILURE"
    if "network" in text or "connection" in text:
        return "NETWORK_FAILURE"
    if "host" in text:
        return "HOST_FAILURE"
    if "provider" in text:
        return "PROVIDER_FAILURE"
    if "input" in text:
        return "JOB_INPUT_FAILURE"
    return "WORKER_FAILURE"


def default_capabilities() -> Iterable[Capability]:
    rows = {
        "research.web": "bounded web acquisition",
        "research.youtube": "bounded YouTube acquisition",
        "research.last30days": "bounded recent-web acquisition",
        "research.seo": "bounded SEO analysis",
        "creative.copy": "bounded creative copy generation",
        "creative.image_generate": "bounded image generation",
        "creative.video_compose": "bounded video composition",
        "creative.media_process": "bounded media processing",
        "creative.voice_generate": "bounded voice generation",
        "creative.avatar_generate": "bounded avatar generation",
        "creative.product_design": "bounded product design",
        "creative.design_qa": "bounded design QA",
        "engineering.code_execute": "bounded code execution",
        "engineering.browser_test": "bounded browser test",
        "trading.backtest": "bounded backtest; no live execution",
    }
    for capability_id, description in rows.items():
        yield Capability(capability_id, description, "Nexus capability certification registry")
