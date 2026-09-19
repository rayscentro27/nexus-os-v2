"""Resource Governor V1 in shadow mode.

The Governor evaluates and explains resource choices; it never executes jobs.
Execution remains owned by temporary_worker_framework provider adapters.
"""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from scripts.nexus_agent_platform.temporary_worker_framework import WorkerJob, provider_registry


@dataclass
class Reservation:
    reservation_id: str
    provider: str
    resource_class: str
    requested_by: str
    job_id: str
    amount: str
    unit: str
    priority: int
    reason: str
    created_at: str
    expires_at: str
    status: str = "ACTIVE"


@dataclass
class GovernorStore:
    reservations: list[Reservation] = field(default_factory=list)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    execution_history: list[dict[str, Any]] = field(default_factory=list)


RESOURCE_CLASSES = {
    "mac": "ABUNDANT_LOCAL",
    "oracle": "PERSISTENT_CLOUD",
    "modal": "TEMPORARY_REMOTE",
    "kaggle": "TEMPORARY_GPU",
}


def classify_job(job: WorkerJob) -> dict[str, Any]:
    params = job.parameters
    return {
        "worker_type": job.worker_type, "priority": params.get("priority", job.priority), "deadline": job.deadline,
        "expected_business_value": params.get("expected_business_value", "UNKNOWN"), "urgency": params.get("urgency", "UNKNOWN"),
        "risk_level": params.get("risk_level", "LOW"), "data_sensitivity": params.get("data_sensitivity", "LOW"),
        "estimated_runtime": params.get("estimated_runtime", job.runtime.get("max_runtime", "UNKNOWN")),
        "max_runtime": job.runtime.get("max_runtime", "UNKNOWN"), "batch_compatible": job.batch_metadata.get("batch_compatible", True),
        "cost_tolerance": params.get("cost_tolerance", "FREE_ONLY"), "gpu_required": job.resource_requirements.gpu_required,
        "network_required": job.resource_requirements.network_required, "tool_requirements": params.get("tool_requirements", []),
        "model_requirements": params.get("model_requirements", []),
    }


class ResourceGovernor:
    """Explainable provider evaluation with automatic routing disabled."""

    mode = "SHADOW"
    autonomous_routing_enabled = False

    def __init__(self, store: GovernorStore | None = None, registry: dict[str, dict[str, Any]] | None = None):
        self.store = store or GovernorStore()
        self.registry = registry or provider_registry()

    def evaluate_job(self, job: WorkerJob) -> dict[str, Any]:
        requirements = classify_job(job)
        eligibility = self.eligible_providers(job)
        ranking = self.rank_providers(job, eligibility)
        selected = ranking[0]["provider"] if ranking else None
        decision = {"job_id": job.worker_job_id, "mode": self.mode, "requirements": requirements,
                    "eligibility": eligibility, "ranking": ranking, "selected_provider": selected,
                    "fallback_provider": ranking[1]["provider"] if len(ranking) > 1 else None,
                    "executed": False, "reason": ranking[0]["reasons"] if ranking else ["No eligible provider"]}
        self.store.decisions.append(decision)
        return decision

    def eligible_providers(self, job: WorkerJob) -> list[dict[str, Any]]:
        result = []
        for provider, state in self.registry.items():
            result.append(self._eligibility(provider, state, job))
        return result

    def _eligibility(self, provider: str, state: dict[str, Any], job: WorkerJob) -> dict[str, Any]:
        req = classify_job(job); reasons: list[str] = []; outcome = "ELIGIBLE"
        if provider in job.provider_exclusions: outcome, reasons = "INELIGIBLE_SECURITY", ["Provider explicitly excluded"]
        elif state.get("available") is not True: outcome, reasons = ("INELIGIBLE_AUTH" if state.get("authorization_state") in {"REAUTH_REQUIRED", "NOT_PROVEN"} else "INELIGIBLE_UNAVAILABLE"), [f"Provider state: {state.get('authorization_state', 'UNAVAILABLE')}"]
        elif req["gpu_required"] and not job.parameters.get("production_ready", False): outcome, reasons = "INELIGIBLE_CAPABILITY", ["GPU gate requires production_ready=true"]
        elif req["gpu_required"] and state.get("capabilities", {}).get("gpu") is not True: outcome, reasons = "INELIGIBLE_CAPABILITY", ["GPU required but provider GPU capability is not verified"]
        elif req["network_required"] and not state.get("capabilities", {}).get("network", False): outcome, reasons = "INELIGIBLE_CAPABILITY", ["Network required"]
        elif provider == "oracle" and job.parameters.get("protect_hermes", True): outcome, reasons = "INELIGIBLE_CAPACITY", ["Oracle headroom reserved for Hermes/Nova"]
        elif provider in {"modal", "kaggle"} and req["cost_tolerance"] == "FREE_ONLY" and state.get("cost_state") != "FREE_QUOTA": outcome, reasons = "INELIGIBLE_COST", ["Temporary remote execution is not free-authorized"]
        elif provider in {"modal", "kaggle"} and not state.get("quota_known", True): outcome, reasons = "UNKNOWN", ["Quota is not trustworthy; not treated as unlimited"]
        else: reasons = ["Capability and configured policy match"]
        return {"provider": provider, "resource_class": RESOURCE_CLASSES.get(provider, "UNKNOWN"), "outcome": outcome, "reasons": reasons}

    def rank_providers(self, job: WorkerJob, eligibility: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        eligible = [item for item in (eligibility or self.eligible_providers(job)) if item["outcome"] == "ELIGIBLE"]
        order = {"mac": 0, "oracle": 1, "modal": 2, "kaggle": 3}
        ranked = sorted(eligible, key=lambda item: order.get(item["provider"], 99))
        for item in ranked:
            item["reasons"] = ["Lowest-cost capable path", f"resource_class={item['resource_class']}", "No autonomous execution in shadow mode"]
        return ranked

    def select_provider(self, job: WorkerJob) -> dict[str, Any]: return self.evaluate_job(job)

    def reserve_capacity(self, job: WorkerJob, provider: str, amount: str = "1", unit: str = "job", ttl_seconds: int = 900) -> Reservation:
        now = datetime.now(timezone.utc); reservation = Reservation(f"reservation_{uuid.uuid4().hex[:12]}", provider, RESOURCE_CLASSES.get(provider, "UNKNOWN"), job.requested_by, job.worker_job_id, amount, unit, job.priority, "shadow evaluation only", now.isoformat(), (now + timedelta(seconds=ttl_seconds)).isoformat())
        self.store.reservations.append(reservation); return reservation

    def release_reservation(self, reservation_id: str, status: str = "RELEASED") -> bool:
        for reservation in self.store.reservations:
            if reservation.reservation_id == reservation_id: reservation.status = status; return True
        return False

    def record_execution_result(self, result: dict[str, Any]) -> None: self.store.execution_history.append(result)

    def select_fallback(self, job: WorkerJob, failed_provider: str) -> dict[str, Any] | None:
        return next((item for item in self.rank_providers(job) if item["provider"] != failed_provider), None)

    def group_batch_candidates(self, jobs: list[WorkerJob]) -> dict[str, Any] | None:
        if len(jobs) < 2: return None
        first = jobs[0]
        if not all(_batch_key(first) == _batch_key(job) for job in jobs[1:]): return None
        return {"batch_group_id": f"batch_{uuid.uuid4().hex[:12]}", "job_ids": [job.worker_job_id for job in jobs], "estimated_setup_savings": "UNKNOWN", "combined_runtime_estimate": "UNKNOWN", "compatibility_reason": "worker/environment/dependency/model/GPU signatures match"}

    def resource_status(self) -> dict[str, Any]:
        return {"mode": self.mode, "autonomous_routing_enabled": self.autonomous_routing_enabled, "providers": self.registry, "active_reservations": [asdict(item) for item in self.store.reservations if item.status == "ACTIVE"], "history_count": len(self.store.execution_history)}


def _batch_key(job: WorkerJob) -> tuple[Any, ...]:
    return tuple(job.batch_metadata.get(key) for key in ("worker_class", "environment_signature", "dependency_signature", "model_signature", "gpu_class"))


def model_routing_compatibility(task: str) -> dict[str, Any]:
    routes = {"NOVA_CHAT": "openai/gpt-4o-mini", "TOOL_ROUTING": "nex-agi/nex-n2.5-pro:free", "RESEARCH_EXTRACTION": "nex-agi/nex-n2.5-pro:free", "RESEARCH_SYNTHESIS": "google/gemini-2.5-flash", "ALPHA_REVIEW": "google/gemini-2.5-flash"}
    return {"task": task, "model": routes.get(task, "UNKNOWN"), "resource_governor_activation": False, "escalation": ["TOOL_FAILURE", "LOW_CONFIDENCE", "SCHEMA_FAILURE", "QUALITY_FAILURE", "TIMEOUT", "MODEL_UNAVAILABLE"]}
