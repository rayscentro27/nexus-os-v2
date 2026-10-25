"""Pure local handlers for the staged activation and recovery canaries."""
from __future__ import annotations

from typing import Any


def execute_internal_canary(job: Any) -> dict[str, Any]:
    """Run a deterministic check with no external capabilities."""
    if job.job_type not in {"SYSTEMS_INTERNAL_CANARY", "SYSTEMS_FAILURE_CANARY"}:
        raise ValueError("UNSUPPORTED_INTERNAL_CANARY")
    context = job.governance_context if isinstance(job.governance_context, dict) else {}
    if (
        context.get("purpose") != "staged_activation_canary"
        or context.get("external_actions_authorized") is not False
        or context.get("paid_provider_authorized") is not False
        or not job.job_id
        or not job.correlation_id
        or job.payload_ref is not None
    ):
        raise ValueError("INTERNAL_CANARY_CONTEXT_INVALID")

    if job.job_type == "SYSTEMS_FAILURE_CANARY":
        if job.max_attempts != 2 or job.attempt_count not in {1, 2}:
            raise ValueError("FAILURE_CANARY_RETRY_ENVELOPE_INVALID")
        if job.attempt_count == 1:
            raise RuntimeError("CONTROLLED_CANARY_FAILURE_ONCE")
        return {
            "status": "COMPLETED",
            "canary": "failure-recovery",
            "attempt": job.attempt_count,
            "check": sum(range(10)) == 45,
        }

    if job.max_attempts != 1 or job.attempt_count != 1:
        raise ValueError("INTERNAL_CANARY_RETRY_ENVELOPE_INVALID")
    value = sum(index * index for index in range(8))
    return {
        "status": "COMPLETED",
        "canary": "staged-activation",
        "deterministic_value": value,
        "check": value == 140,
    }
