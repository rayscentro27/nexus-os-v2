"""Small fail-closed HTTP helper for standalone Nexus connector probes."""
from __future__ import annotations

import json
import os
import ssl
import urllib.request
from typing import Any


def get_json(url: str, *, provider: str, service: str, headers: dict[str, str] | None = None,
             timeout: int = 20, estimated_units: int = 1, billable: bool = True,
             cost: float | None = None, purpose: str | None = None) -> Any:
    """GET JSON only for an identified durable job through the spend governor."""
    from nexus_agent_platform.provider_enforcement import execute

    job_id = os.environ.get("NEXUS_DURABLE_JOB_ID")
    correlation_id = os.environ.get("NEXUS_CORRELATION_ID")
    department = os.environ.get("NEXUS_DEPARTMENT")
    if not job_id or not correlation_id or not department:
        raise RuntimeError("GOVERNOR_DENIED:JOB_CORRELATION_DEPARTMENT_REQUIRED")

    def request() -> Any:
        req = urllib.request.Request(url, headers=headers or {}, method="GET")
        try:
            import certifi
            context = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            context = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout, context=context) as response:
            return json.loads(response.read(2_000_000).decode("utf-8", "replace"))

    return execute(provider, service, "READ", {
        "requests": 1, "api_calls": estimated_units, "usage_units": estimated_units,
        "billable": bool(billable), "cost": cost,
    }, request, job_id=job_id, job_type=os.environ.get("NEXUS_JOB_TYPE"),
       correlation_id=correlation_id, purpose=purpose)
