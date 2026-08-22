"""Modal adapter for the existing provider-neutral remote worker contract.

Modal authentication is delegated to the fixed ``modal curl`` client, while
the worker still validates the Nexus HMAC inside the Modal container.
"""
from __future__ import annotations

import json
import time
import os
import subprocess
from pathlib import Path
from typing import Optional

from scripts.nexus_agent_platform.remote_worker import (
    RemoteWorkerProvider,
    canonical_json,
    sign_request,
    validate_result,
    validate_result_tenant,
)


class ModalRemoteWorkerProvider:
    """Synchronous, fixed-command Modal transport; no scheduler or retry loop."""

    def __init__(self, endpoint_url: str = "", *, modal_bin: str = "modal", timeout: int = 75,
                 profile: str = "goclearonline", shared_secret: str | None = None,
                 app_name: str = "nexus-remote-cpu-worker"):
        self.endpoint_url = endpoint_url.rstrip("/")
        self.modal_bin = modal_bin
        self.timeout = timeout
        self.profile = profile
        self.shared_secret = shared_secret or os.environ.get("NEXUS_REMOTE_WORKER_SHARED_SECRET")
        self.app_name = app_name

    def _function(self, name: str):
        # Native Modal SDK calls use the authenticated local Modal profile. The
        # web endpoint remains proxy-authenticated, but is not the Nexus
        # transport path and therefore needs no proxy credential in the repo.
        os.environ["MODAL_PROFILE"] = self.profile
        import modal
        return modal.Function.from_name(self.app_name, name)

    def _curl(self, method: str, path: str = "", payload: Optional[dict] = None) -> dict:
        if not self.endpoint_url:
            raise RuntimeError("NEXUS_MODAL_WORKER_URL is required for Modal curl compatibility transport")
        command = [self.modal_bin, "curl", "-X", method, self.endpoint_url + path,
                   "-H", "Content-Type: application/json"]
        if payload is not None:
            if not self.shared_secret:
                raise RuntimeError("NEXUS_REMOTE_WORKER_SHARED_SECRET is required for signed Modal jobs")
            timestamp = str(int(time.time()))
            command += ["--data", canonical_json(payload).decode("utf-8")]
            command += ["-H", f"X-Nexus-Timestamp: {timestamp}"]
            command += ["-H", f"X-Nexus-Signature: {sign_request(payload, self.shared_secret, timestamp)}"]
        env = {**os.environ, "MODAL_PROFILE": self.profile}
        completed = subprocess.run(command, capture_output=True, text=True, timeout=self.timeout, env=env, check=False)
        if completed.returncode != 0:
            raise RuntimeError(f"modal transport failed with exit {completed.returncode}: {completed.stderr[-300:]}")
        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("modal transport returned non-JSON result") from exc

    def submit(self, job: dict) -> dict:
        if not self.shared_secret:
            raise RuntimeError("NEXUS_REMOTE_WORKER_SHARED_SECRET is required for signed Modal jobs")
        timestamp = str(int(time.time()))
        result = self._function("submit_job").remote(job, timestamp, sign_request(job, self.shared_secret, timestamp))
        valid, reason = validate_result(result)
        if not valid:
            raise ValueError(f"invalid remote result: {reason}")
        if result.get("job_id") != job.get("job_id"):
            raise ValueError("remote result job mismatch")
        if result.get("capability") != job.get("capability"):
            raise ValueError("remote result capability mismatch")
        tenant_valid, tenant_reason = validate_result_tenant(job, result)
        if not tenant_valid:
            raise ValueError(f"remote result tenant mismatch: {tenant_reason}")
        return result

    def get_status(self, job_id: str) -> dict:
        return {"job_id": job_id, "status": "NOT_AVAILABLE", "reason": "synchronous Modal function"}

    def cancel(self, job_id: str) -> dict:
        return {"job_id": job_id, "status": "NOT_AVAILABLE", "reason": "synchronous bounded Modal function"}

    def health(self) -> dict:
        return self._function("health_check").remote()


def provider_from_environment() -> ModalRemoteWorkerProvider:
    # Native SDK transport uses the authenticated local Modal profile and
    # Modal Function.from_name(). An endpoint is only needed by the optional
    # curl compatibility transport; absence must not mask native capability.
    endpoint = os.environ.get("NEXUS_MODAL_WORKER_URL", "")
    return ModalRemoteWorkerProvider(
        endpoint,
        modal_bin=os.environ.get("NEXUS_MODAL_BIN", "modal"),
        profile=os.environ.get("MODAL_PROFILE", "goclearonline"),
        app_name=os.environ.get("NEXUS_MODAL_APP", "nexus-remote-cpu-worker"),
    )
