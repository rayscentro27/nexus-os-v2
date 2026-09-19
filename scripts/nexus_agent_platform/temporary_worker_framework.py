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
import re
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
    @staticmethod
    def _auth_source() -> str | None:
        """Detect supported credential locations without reading or exposing secrets."""
        if os.environ.get("KAGGLE_API_TOKEN"):
            return "KAGGLE_API_TOKEN"
        config_dir = Path(os.environ.get("KAGGLE_CONFIG_DIR", str(Path.home() / ".kaggle")))
        if config_dir.joinpath("access_token").exists():
            return "~/.kaggle/access_token"
        if config_dir.joinpath("kaggle.json").exists():
            return "~/.kaggle/kaggle.json"
        if os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY"):
            return "KAGGLE_USERNAME+KAGGLE_KEY"
        return None

    @staticmethod
    def _cli_path() -> str | None:
        configured = os.environ.get("KAGGLE_CLI_PATH")
        return configured if configured and Path(configured).exists() else shutil.which("kaggle")

    def _cli(self) -> list[str]:
        path = self._cli_path()
        if not path:
            raise RuntimeError("Kaggle CLI unavailable")
        return [path]

    def _run_cli(self, args: list[str], *, timeout: int, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(self._cli() + args, cwd=cwd, capture_output=True, text=True,
                              timeout=timeout, env=os.environ.copy(), check=False)

    def probe(self) -> dict[str, Any]:
        cli_path = self._cli_path(); auth_source = self._auth_source(); auth = auth_source is not None
        quota_known = False; quota = {}
        if cli_path and auth:
            try:
                quota_result = self._run_cli(["quota"], timeout=30)
                for line in quota_result.stdout.splitlines():
                    match = re.search(r"^(GPU|TPU)\s+([0-9.]+h)\s+([0-9.]+h)\s+([0-9.]+h)\s+(.+)$", line.strip())
                    if match:
                        quota[match.group(1)] = {"used": match.group(2), "remaining": match.group(3), "total": match.group(4), "refresh_at": match.group(5).strip()}
                quota_known = bool(quota)
            except Exception:
                quota_known = False
        return {"provider_id": self.provider_id, "available": bool(cli_path and auth), "configured": auth,
                "cli_present": bool(cli_path), "cli_path_present": bool(cli_path), "auth_source": auth_source,
                "authorization_state": "AUTHORIZED" if auth else "REAUTH_REQUIRED",
                "capabilities": {"cpu": True, "gpu": "UNKNOWN", "artifact_download": bool(cli_path and auth), "timeout": "UNKNOWN"},
                "quota_known": quota_known, "quota": quota, "cost_state": "FREE_QUOTA" if quota_known else "UNKNOWN"}
    def prepare(self, job: WorkerJob) -> dict[str, Any]:
        probe = self.probe()
        return {"status": "PREPARED", "provider": self.provider_id, "transport": "kaggle kernels push/status/output"} if probe["available"] else {"status": "BLOCKED_EXTERNAL", "reason": "Kaggle credentials or CLI unavailable"}

    def _kernel_ref(self, job: WorkerJob) -> str:
        explicit = job.parameters.get("kaggle_kernel_id")
        if explicit:
            return str(explicit)
        owner = str(job.parameters.get("kaggle_username") or "rayscentro")
        worker_slug = "-".join(part for part in job.worker_type.lower().replace("_", "-").split("-") if part)[:22]
        job_suffix = hashlib.sha256(job.worker_job_id.encode()).hexdigest()[:12]
        slug = f"nexus-{worker_slug}-{job_suffix}"
        return f"{owner}/{slug}"

    def launch(self, job: WorkerJob, workdir: Path | None = None) -> dict[str, Any]:
        if not self.probe()["available"]:
            return {"status": "BLOCKED_EXTERNAL", "reason": "Kaggle credentials or CLI unavailable"}
        if workdir is None:
            return {"status": "BLOCKED_EXTERNAL", "reason": "Kaggle workdir required"}
        timeout = min(int(job.runtime.get("startup_timeout", 60)), int(job.runtime.get("max_runtime", 300)))
        completed = self._run_cli(["kernels", "push", "-p", str(workdir), "--timeout", str(timeout)], timeout=timeout + 30)
        ref = self._kernel_ref(job)
        output = (completed.stdout + "\n" + completed.stderr)[-2000:]
        if completed.returncode != 0:
            return {"status": "FAILED", "provider_job_id": ref, "error": output}
        return {"status": "STARTING", "provider_job_id": ref, "output": output}

    def stage_inputs(self, job: WorkerJob, workdir: Path) -> None:
        workdir.mkdir(parents=True, exist_ok=True)
        (workdir / "job_manifest.json").write_text(json.dumps(asdict(job), default=asdict, sort_keys=True), encoding="utf-8")
        kernel_ref = self._kernel_ref(job)
        metadata = {"id": kernel_ref, "title": kernel_ref.split("/", 1)[-1],
                    "code_file": "worker.py", "language": "python", "kernel_type": "script",
                    "is_private": True, "enable_gpu": bool(job.resource_requirements.gpu_required),
                    "enable_internet": False}
        (workdir / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
        manifest_literal = repr(json.dumps(asdict(job), default=asdict, sort_keys=True))
        worker = ("import json, pathlib, platform, time\n"
                  f"manifest=json.loads({manifest_literal})\n"
                  "payload={'worker_job_id':manifest['worker_job_id'],'provider':'kaggle','status':'SUCCEEDED',"
                  "'platform':platform.platform(),'started_at':time.time()}\n"
                  "if manifest['worker_type'] == 'FAILURE_TEST_V1': raise RuntimeError('intentional bounded Nexus failure canary')\n"
                  "pathlib.Path('result.json').write_text(json.dumps(payload, sort_keys=True))\n"
                  "pathlib.Path('artifact.txt').write_text('nexus kaggle smoke artifact\\n')\n"
                  "if manifest['worker_type'] == 'CREATIVE_IMAGE_CANDIDATE':\n"
                  " pathlib.Path('creative_candidate.svg').write_text('''<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"1080\" height=\"1080\" viewBox=\"0 0 1080 1080\"><rect width=\"1080\" height=\"1080\" fill=\"#f4f0e8\"/><rect x=\"100\" y=\"100\" width=\"880\" height=\"880\" rx=\"44\" fill=\"#17324d\"/><text x=\"150\" y=\"390\" fill=\"#f4f0e8\" font-size=\"72\" font-family=\"Arial\">FUNDING</text><text x=\"150\" y=\"485\" fill=\"#d7b56d\" font-size=\"72\" font-family=\"Arial\">READINESS</text><text x=\"150\" y=\"620\" fill=\"#f4f0e8\" font-size=\"34\" font-family=\"Arial\">Turn uncertainty into a clearer next step.</text><text x=\"150\" y=\"850\" fill=\"#d7b56d\" font-size=\"28\" font-family=\"Arial\">INTERNAL CONCEPT · NO GUARANTEE</text></svg>''')\n")
        (workdir / "worker.py").write_text(worker, encoding="utf-8")

    def install_or_restore_environment(self, manifest: EnvironmentManifest) -> dict[str, Any]:
        return {"status": "READY", "environment_id": manifest.environment_id, "base_runtime": manifest.base_runtime, "provider": self.provider_id}

    def execute(self, job: WorkerJob, workdir: Path) -> WorkerResult:
        started = time.monotonic(); result = WorkerResult(job.worker_job_id, self.provider_id, None, job.worker_type, "STARTING", started_at=_now())
        try:
            launch = self.launch(job, workdir)
            result.provider_job_id = launch.get("provider_job_id")
            if launch.get("status") != "STARTING":
                result.status = launch.get("status", "FAILED"); result.errors.append(str(launch.get("error", launch.get("reason", "Kaggle launch failed")))); result.completed_at = _now(); result.total_runtime_seconds = time.monotonic() - started; return result
            deadline = time.monotonic() + min(int(job.runtime.get("execution_timeout", 240)), int(job.runtime.get("max_runtime", 300)))
            result.status = "RUNNING"
            while time.monotonic() < deadline:
                status = self._run_cli(["kernels", "status", str(result.provider_job_id)], timeout=30)
                text = (status.stdout + "\n" + status.stderr).lower()
                if "not found" in text or "does not exist" in text:
                    result.status = "FAILED"; result.errors.append(text[-500:]); break
                if any(word in text for word in ("complete", "finished", "success")):
                    result.status = "SUCCEEDED"; break
                if any(word in text for word in ("error", "failed", "cancelled")):
                    result.status = "FAILED"; result.errors.append(text[-500:]); break
                time.sleep(5)
            else:
                result.status = "TIMED_OUT"; result.errors.append("Kaggle kernel execution timeout")
            if result.status == "SUCCEEDED":
                result = self.collect_outputs(result, workdir)
            result.execution_seconds = time.monotonic() - started
            result.completed_at = _now(); result.total_runtime_seconds = time.monotonic() - started
            return result
        except subprocess.TimeoutExpired:
            result.status = "TIMED_OUT"; result.errors.append("Kaggle CLI timeout"); result.completed_at = _now(); result.total_runtime_seconds = time.monotonic() - started; return result
        except Exception as exc:
            result.status = "FAILED"; result.errors.append(str(exc)); result.completed_at = _now(); result.total_runtime_seconds = time.monotonic() - started; return result

    def collect_outputs(self, result: WorkerResult, workdir: Path) -> WorkerResult:
        output_dir = workdir / "kaggle-output"; output_dir.mkdir(exist_ok=True)
        downloaded = self._run_cli(["kernels", "output", "-p", str(output_dir), "-q", "-o", str(result.provider_job_id)], timeout=90)
        if downloaded.returncode != 0:
            result.status = "FAILED"; result.errors.append((downloaded.stdout + downloaded.stderr)[-500:]); return result
        expected = [("result.json", "application/json"), ("artifact.txt", "text/plain")]
        if result.worker_type == "CREATIVE_IMAGE_CANDIDATE":
            expected.append(("creative_candidate.svg", "image/svg+xml"))
        for name, kind in expected:
            path = output_dir / name
            if path.exists():
                result.artifacts.append(WorkerArtifact(name, kind, str(path), "governed_artifacts", sha256_file(path), path.stat().st_size))
        required = {"result.json", "creative_candidate.svg"} if result.worker_type == "CREATIVE_IMAGE_CANDIDATE" else {"result.json", "artifact.txt"}
        if not required.issubset({item.logical_name for item in result.artifacts}):
            result.status = "FAILED"; result.errors.append(f"missing required Kaggle output: {sorted(required)}")
        return result
    def write_receipt(self, result: WorkerResult, destination: Path) -> Path: destination.write_text(json.dumps(asdict(result), indent=2, sort_keys=True), encoding="utf-8"); return destination
    def cleanup(self, job: WorkerJob, workdir: Path) -> bool:
        ref = self._kernel_ref(job)
        remote_ok = True
        if self.probe()["available"]:
            try:
                deleted = self._run_cli(["kernels", "delete", "-y", ref], timeout=60)
                remote_ok = deleted.returncode == 0
            except Exception:
                remote_ok = False
        shutil.rmtree(workdir, ignore_errors=True)
        return remote_ok and not workdir.exists()
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
