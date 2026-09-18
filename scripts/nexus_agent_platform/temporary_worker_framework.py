"""Provider-neutral bounded temporary-worker framework.

This module owns execution envelopes and lifecycle receipts only. Nexus remains
the owner of durable state; providers receive bounded inputs and return bounded
results. The existing remote_worker.py v1 envelope remains the Modal/remote
compatibility contract.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol


STATUSES = {"PREPARED", "STARTING", "RUNNING", "SUCCEEDED", "FAILED", "TIMED_OUT", "CANCELLED", "BLOCKED_EXTERNAL"}


@dataclass
class ResourceRequirements:
    cpu: str = "1"
    ram: str = "512MiB"
    gpu_required: bool = False
    gpu_class: str | None = None
    vram: str | None = None
    storage: str = "256MiB"
    network_required: bool = False


@dataclass
class EnvironmentManifest:
    environment_id: str
    worker_class: str
    base_runtime: str
    python_version: str | None
    node_version: str | None
    system_packages: list[str] = field(default_factory=list)
    python_packages: list[str] = field(default_factory=list)
    node_packages: list[str] = field(default_factory=list)
    models: list[str] = field(default_factory=list)
    model_sources: list[str] = field(default_factory=list)
    model_versions: list[str] = field(default_factory=list)
    environment_variables_required: list[str] = field(default_factory=list)
    network_requirements: list[str] = field(default_factory=list)
    input_schema: str = "application/json"
    output_schema: str = "application/json"
    setup_commands: list[str] = field(default_factory=list)
    execution_command: str = ""
    healthcheck_command: str = ""


@dataclass
class WorkerJob:
    worker_job_id: str
    worker_type: str
    production_package_id: str | None = None
    campaign_id: str | None = None
    requested_by: str = "nexus"
    priority: int = 50
    deadline: str | None = None
    input_artifacts: list[str] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    resource_requirements: ResourceRequirements = field(default_factory=ResourceRequirements)
    environment_requirements: dict[str, Any] = field(default_factory=dict)
    runtime: dict[str, int] = field(default_factory=lambda: {"max_runtime": 60, "startup_timeout": 15, "execution_timeout": 45, "cleanup_timeout": 10})
    output_destination: str = "governed_artifacts"
    provider_preferences: list[str] = field(default_factory=list)
    provider_exclusions: list[str] = field(default_factory=list)
    batch_metadata: dict[str, Any] = field(default_factory=dict)
    status: str = "PREPARED"


@dataclass
class WorkerArtifact:
    logical_name: str
    artifact_type: str
    provider_path: str
    canonical_destination: str | None
    sha256: str
    size: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkerResult:
    worker_job_id: str
    provider: str
    provider_job_id: str | None
    worker_type: str
    status: str
    started_at: str | None = None
    completed_at: str | None = None
    startup_seconds: float = 0
    setup_seconds: float = 0
    model_load_seconds: float = 0
    execution_seconds: float = 0
    artifact_transfer_seconds: float = 0
    cleanup_seconds: float = 0
    total_runtime_seconds: float = 0
    artifacts: list[WorkerArtifact] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    tool_versions: list[str] = field(default_factory=list)
    model_versions: list[str] = field(default_factory=list)
    resource_usage: dict[str, Any] = field(default_factory=dict)
    external_mutations: list[str] = field(default_factory=list)
    cleanup_succeeded: bool = False


class ProviderAdapter(Protocol):
    provider_id: str
    def probe(self) -> dict[str, Any]: ...
    def prepare(self, job: WorkerJob) -> dict[str, Any]: ...
    def launch(self, job: WorkerJob) -> dict[str, Any]: ...
    def stage_inputs(self, job: WorkerJob, workdir: Path) -> None: ...
    def install_or_restore_environment(self, manifest: EnvironmentManifest) -> dict[str, Any]: ...
    def execute(self, job: WorkerJob, workdir: Path) -> WorkerResult: ...
    def collect_outputs(self, result: WorkerResult, workdir: Path) -> WorkerResult: ...
    def write_receipt(self, result: WorkerResult, destination: Path) -> Path: ...
    def cleanup(self, job: WorkerJob, workdir: Path) -> bool: ...
    def cancel(self, provider_job_id: str) -> dict[str, Any]: ...
    def health(self) -> dict[str, Any]: ...


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


class MacAdapter:
    provider_id = "mac"

    def probe(self) -> dict[str, Any]:
        return {"provider_id": self.provider_id, "available": True, "configured": True, "capabilities": {"cpu": True, "gpu": False, "network": True, "timeout": True, "artifact_download": True}, "authorization_state": "LOCAL"}

    def prepare(self, job: WorkerJob) -> dict[str, Any]:
        return {"status": "PREPARED", "provider": self.provider_id, "job_id": job.worker_job_id}

    def launch(self, job: WorkerJob) -> dict[str, Any]:
        return {"provider_job_id": f"mac-{job.worker_job_id}", "status": "STARTING"}

    def stage_inputs(self, job: WorkerJob, workdir: Path) -> None:
        (workdir / "input.json").write_text(json.dumps({"worker_job_id": job.worker_job_id, "parameters": job.parameters}, sort_keys=True), encoding="utf-8")

    def install_or_restore_environment(self, manifest: EnvironmentManifest) -> dict[str, Any]:
        return {"status": "READY", "environment_id": manifest.environment_id, "base_runtime": manifest.base_runtime}

    def execute(self, job: WorkerJob, workdir: Path) -> WorkerResult:
        started = time.monotonic(); launch = self.launch(job)
        receipt = WorkerResult(worker_job_id=job.worker_job_id, provider=self.provider_id, provider_job_id=launch["provider_job_id"], worker_type=job.worker_type, status="RUNNING", started_at=_now())
        script = "import json; p=json.load(open('input.json')); json.dump({'worker_job_id':p['worker_job_id'],'result':'bounded-smoke-ok'},open('result.json','w'),sort_keys=True); open('artifact.txt','w').write('nexus temporary worker canary\\n')"
        timeout = min(job.runtime.get("execution_timeout", 45), job.runtime.get("max_runtime", 60))
        try:
            process = subprocess.run([sys.executable, "-c", script], cwd=workdir, capture_output=True, text=True, timeout=timeout, start_new_session=True)
            receipt.execution_seconds = time.monotonic() - started
            if process.returncode:
                receipt.status = "FAILED"; receipt.errors.append(process.stderr[-500:])
            else:
                receipt.status = "SUCCEEDED"; receipt.logs.append(process.stdout[-500:])
            for name, kind in (("result.json", "application/json"), ("artifact.txt", "text/plain")):
                path = workdir / name
                receipt.artifacts.append(WorkerArtifact(name, kind, str(path), job.output_destination, sha256_file(path), path.stat().st_size))
        except subprocess.TimeoutExpired:
            receipt.status = "TIMED_OUT"; receipt.errors.append("execution timeout")
        receipt.completed_at = _now(); receipt.total_runtime_seconds = time.monotonic() - started
        return receipt

    def collect_outputs(self, result: WorkerResult, workdir: Path) -> WorkerResult: return result
    def write_receipt(self, result: WorkerResult, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True); destination.write_text(json.dumps(asdict(result), indent=2, sort_keys=True), encoding="utf-8"); return destination
    def cleanup(self, job: WorkerJob, workdir: Path) -> bool:
        shutil.rmtree(workdir, ignore_errors=True); return not workdir.exists()
    def cancel(self, provider_job_id: str) -> dict[str, Any]: return {"provider_job_id": provider_job_id, "status": "NOT_RUNNING"}
    def health(self) -> dict[str, Any]: return self.probe()


class KaggleAdapter:
    provider_id = "kaggle"
    def probe(self) -> dict[str, Any]:
        cli = shutil.which("kaggle") is not None
        auth = bool(os.environ.get("KAGGLE_API_TOKEN")) or Path.home().joinpath(".kaggle/kaggle.json").exists()
        return {"provider_id": self.provider_id, "available": cli and auth, "configured": auth, "cli_present": cli, "authorization_state": "AUTHORIZED" if auth else "REAUTH_REQUIRED", "capabilities": {"cpu": True, "gpu": "UNKNOWN", "artifact_download": cli and auth, "timeout": "UNKNOWN"}, "quota_known": False}
    def prepare(self, job: WorkerJob) -> dict[str, Any]: return {"status": "BLOCKED_EXTERNAL", "reason": "Kaggle credentials or CLI unavailable"} if not self.probe()["available"] else {"status": "PREPARED"}
    def launch(self, job: WorkerJob) -> dict[str, Any]: return {"status": "BLOCKED_EXTERNAL", "reason": "No authorized Kaggle launch path was available during certification"}
    def stage_inputs(self, job: WorkerJob, workdir: Path) -> None: (workdir / "job_manifest.json").write_text(json.dumps(asdict(job), default=asdict, sort_keys=True), encoding="utf-8")
    def install_or_restore_environment(self, manifest: EnvironmentManifest) -> dict[str, Any]: return {"status": "BLOCKED_EXTERNAL", "reason": "authorization required"}
    def execute(self, job: WorkerJob, workdir: Path) -> WorkerResult: return WorkerResult(job.worker_job_id, self.provider_id, None, job.worker_type, "BLOCKED_EXTERNAL", started_at=_now(), completed_at=_now(), errors=["Kaggle CLI/API credentials unavailable"])
    def collect_outputs(self, result: WorkerResult, workdir: Path) -> WorkerResult: return result
    def write_receipt(self, result: WorkerResult, destination: Path) -> Path: destination.write_text(json.dumps(asdict(result), indent=2, sort_keys=True), encoding="utf-8"); return destination
    def cleanup(self, job: WorkerJob, workdir: Path) -> bool: return True
    def cancel(self, provider_job_id: str) -> dict[str, Any]: return {"status": "UNAVAILABLE", "provider_job_id": provider_job_id}
    def health(self) -> dict[str, Any]: return self.probe()


def provider_registry() -> dict[str, dict[str, Any]]:
    mac = MacAdapter().probe(); kaggle = KaggleAdapter().probe()
    return {"mac": mac, "oracle": {"provider_id": "oracle", "available": "UNKNOWN", "configured": False, "authorization_state": "NOT_PROVEN"}, "modal": {"provider_id": "modal", "available": True, "configured": True, "authorization_state": "DEPLOYED_EXISTING_REMOTE_WORKER", "adapter": "remote_worker.HttpRemoteWorkerProvider", "quota_known": False, "cost_state": "UNKNOWN"}, "kaggle": kaggle}


def batch_compatible(left: WorkerJob, right: WorkerJob) -> bool:
    keys = ("worker_class", "environment_signature", "dependency_signature", "model_signature", "gpu_class")
    return all(left.batch_metadata.get(key) == right.batch_metadata.get(key) for key in keys)


def run_mac_smoke_canary(root: Path = Path("reports/runtime")) -> WorkerResult:
    job = WorkerJob(worker_job_id=f"mac-canary-{int(time.time())}", worker_type="SMOKE_TEST_V1", parameters={"payload": "bounded"}, output_destination="canonical governed receipt")
    adapter = MacAdapter(); workdir = Path(tempfile.mkdtemp(prefix="nexus-worker-")); adapter.stage_inputs(job, workdir)
    try:
        result = adapter.execute(job, workdir); result.cleanup_succeeded = adapter.cleanup(job, workdir); adapter.write_receipt(result, root / "generic_worker_canary_latest.json"); return result
    except Exception as exc:
        adapter.cleanup(job, workdir); return WorkerResult(job.worker_job_id, "mac", None, job.worker_type, "FAILED", errors=[str(exc)], cleanup_succeeded=True)
