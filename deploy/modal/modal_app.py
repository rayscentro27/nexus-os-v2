"""One bounded Modal app exposing the existing Nexus worker capability."""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import modal

try:
    LOCAL_ROOT = Path(__file__).resolve().parents[2]
except IndexError:
    # Modal imports the mounted app as /root/modal_app.py during hydration.
    # The image has the application tree under /app; no local build context is
    # needed in that runtime.
    LOCAL_ROOT = Path("/app")
ROOT = Path("/app") if Path("/app/scripts/nexus_agent_platform").exists() else LOCAL_ROOT
sys.path.insert(0, "/app")
sys.path.insert(0, str(ROOT))
from scripts.nexus_agent_platform.remote_worker import (  # noqa: E402
    WorkerRuntime,
    utc_now,
    verify_request,
)

app = modal.App("nexus-remote-cpu-worker")
image = modal.Image.from_dockerfile(
    LOCAL_ROOT / "deploy/remote-cpu-worker/Dockerfile",
    context_dir=LOCAL_ROOT,
).entrypoint([])
_deploy_hmac = os.environ.get("NEXUS_MODAL_DEPLOY_HMAC")
worker_secret = (
    modal.Secret.from_dict({"NEXUS_REMOTE_WORKER_SHARED_SECRET": _deploy_hmac})
    if _deploy_hmac
    else modal.Secret.from_name("nexus-remote-worker-hmac-phaseic", required_keys=["NEXUS_REMOTE_WORKER_SHARED_SECRET"])
)


def _runtime() -> WorkerRuntime:
    return WorkerRuntime(
        worker_id=os.environ.get("NEXUS_WORKER_ID", f"modal-worker-{uuid.uuid4().hex[:12]}"),
        provider="modal",
        root=Path("/tmp/nexus-evidence-runtime"),
        shared_secret=os.environ.get("NEXUS_REMOTE_WORKER_SHARED_SECRET"),
        heartbeat_path=Path("/tmp/nexus-remote-worker-heartbeat.json"),
    )


def _modal_health() -> dict:
    value = _runtime().health()
    value["capabilities"] = {"evidence_ingestion": ["crawl4ai"]}
    return value


def _execute_crawl4ai(job: dict, timestamp: str, signature: str) -> dict:
    runtime = _runtime()
    if job.get("capability") != "evidence_ingestion" or job.get("adapter") != "crawl4ai":
        return {
            "schema_version": "nexus.remote-result.v1", "job_id": job.get("job_id", "invalid"),
            "capability": job.get("capability", "unknown"), "worker_id": runtime.worker_id,
            "provider": runtime.provider, "status": "SAFETY_BLOCKED", "started_at": utc_now(),
            "completed_at": utc_now(), "tenant_context": job.get("tenant_context"),
            "error": {"classification": "adapter-not-allowed"},
        }
    if not runtime.shared_secret or not verify_request(job, runtime.shared_secret, timestamp, signature):
        return {"schema_version": "nexus.remote-result.v1", "job_id": job.get("job_id", "invalid"),
                "capability": job.get("capability", "unknown"), "status": "UNAUTHORIZED",
                "worker_id": runtime.worker_id, "provider": runtime.provider,
                "started_at": utc_now(), "completed_at": utc_now(),
                "tenant_context": job.get("tenant_context"),
                "error": {"classification": "invalid-authentication"}}
    return runtime.execute(job)


@app.function(
    image=image,
    secrets=[worker_secret],
    cpu=1.0,
    memory=4096,
    min_containers=0,
    max_containers=1,
    scaledown_window=60,
    timeout=60,
    name="submit",
)
@modal.fastapi_endpoint(method="POST", requires_proxy_auth=True, docs=False)
def submit(job: dict, timestamp: str = "", signature: str = ""):
    return _execute_crawl4ai(job, timestamp, signature)


@app.function(
    image=image,
    secrets=[worker_secret],
    cpu=1.0,
    memory=4096,
    min_containers=0,
    max_containers=1,
    scaledown_window=60,
    timeout=60,
    name="submit_job",
)
def submit_job(job: dict, timestamp: str, signature: str) -> dict:
    return _execute_crawl4ai(job, timestamp, signature)


@app.function(
    image=image,
    secrets=[worker_secret],
    cpu=0.125,
    memory=512,
    min_containers=0,
    max_containers=1,
    scaledown_window=60,
    timeout=20,
    name="health",
)
@modal.fastapi_endpoint(method="GET", requires_proxy_auth=True, docs=False)
def health() -> dict:
    return _modal_health()


@app.function(
    image=image,
    secrets=[worker_secret],
    cpu=0.125,
    memory=512,
    min_containers=0,
    max_containers=1,
    scaledown_window=60,
    timeout=20,
    name="health_check",
)
def health_check() -> dict:
    return _modal_health()
