"""Dependency-aware handling for resource-scoped durable campaign work."""
from __future__ import annotations

from typing import Any, Iterable

RESOURCE_CLASS = {
    "cost": "COST_LIMIT",
    "rate": "PROVIDER_RATE_LIMIT",
    "health": "RESOURCE_HEALTH_LIMIT",
    "host": "HOST_SAFETY_LIMIT",
    "anomaly": "ANOMALY_LIMIT",
    "budget": "INTERNAL_BUDGET_LIMIT",
}


def classify_policy(*, provider: str, capability: str, state: str,
                    limits: dict[str, Any] | None = None,
                    circuit_class: str = "budget") -> dict[str, Any]:
    category=RESOURCE_CLASS.get(circuit_class,"INTERNAL_BUDGET_LIMIT")
    values=limits or {}
    return {"resource":provider.upper(),"capability":capability,"policy_state":state,
        "classification":category,"limit":values,"requires_global_stop":False,
        "global_stop_allowed_only_if":"NO_EXECUTABLE_ZERO_COST_JOB_REMAINS"}


def partition_jobs(jobs: Iterable[dict[str, Any]], *, paused_resources: set[str]) -> tuple[list[dict[str, Any]],list[dict[str, Any]]]:
    executable=[]; waiting=[]; paused={item.upper() for item in paused_resources}
    for job in jobs:
        required={str(x).upper() for x in (job.get("required_resources") or [])}
        if required & paused:
            waiting.append({**job,"status":"WAITING_RESOURCE_WINDOW",
                "waiting_for":sorted(required & paused),"checkpoint_preserved":True})
        else:
            executable.append({**job,"status":"READY"})
    return executable,waiting


def can_resume_waiting_job(job: dict[str, Any], *, normalized_resources: set[str]) -> bool:
    wait=job.get("resource_wait") or {}
    resource=str(wait.get("resource") or "").upper()
    return bool(resource and resource in {x.upper() for x in normalized_resources}
        and wait.get("resume_condition") in {None,"NOTEBOOKLM_POLICY_NORMAL"})


def global_stop_allowed(executable_jobs: Iterable[dict[str, Any]]) -> bool:
    """A resource circuit can stop the campaign only when no zero-cost work can run."""
    return not any(job.get("zero_cost_executable", True) for job in executable_jobs)
