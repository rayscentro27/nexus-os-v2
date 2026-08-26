"""Bounded proof recovery policy.

The policy is intentionally small and deterministic: two attempts for one
failure signature, then a mandatory alternative-design decision. It never
pretends that a repair succeeded; callers must attach a fresh receipt.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Sequence


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def failure_signature(*, executor: str, failure_stage: str, reason: str) -> str:
    value = f"{executor}:{failure_stage}:{reason}".encode()
    return hashlib.sha256(value).hexdigest()[:20]


def recover(objective: Dict[str, Any], *, repair_budget: int = 2) -> Dict[str, Any]:
    signature = objective.get("failure_signature") or failure_signature(
        executor=str(objective.get("executor", "unknown")),
        failure_stage=str(objective.get("failure_stage", "UNKNOWN")),
        reason=str(objective.get("failure_reason", "missing proof")),
    )
    attempts = int(objective.get("repair_cycles_used", objective.get("repair_count", 0)) or 0)
    if attempts < repair_budget:
        return {"status": "RECOVERING", "action": "REPAIR", "repair_cycles_used": attempts + 1,
                "repair_budget": repair_budget, "failure_signature": signature,
                "proof_required": True, "created_at": _now(),
                "reason": "bounded repair attempt; retry requires a new receipt"}
    return {"status": "ARCHITECTURE_ALTERNATIVE", "action": "STOP_REPEATING_SIGNATURE",
            "repair_cycles_used": attempts, "repair_budget": repair_budget,
            "failure_signature": signature, "proof_required": True, "created_at": _now(),
            "alternatives": list(alternative_options(objective)),
            "reason": "repair budget exhausted for this unique failure signature"}


def alternative_options(objective: Dict[str, Any]) -> Sequence[Dict[str, Any]]:
    stage = str(objective.get("failure_stage", "UNKNOWN"))
    return (
        {"option_id": "replace_executor", "description": f"Use a separately certified executor for {stage}.", "risk": "medium", "canary": "isolated bounded task"},
        {"option_id": "reduce_scope", "description": f"Split the objective before {stage} into a smaller handoff.", "risk": "low", "canary": "deterministic contract check"},
        {"option_id": "add_receiver_contract", "description": f"Add an explicit receiver acknowledgement before {stage}.", "risk": "low", "canary": "acknowledgement fixture"},
    )


def apply_recovery(objective: Dict[str, Any], *, repair_budget: int = 2) -> Dict[str, Any]:
    """Return updated objective state; no executor is invoked by this policy."""
    decision = recover(objective, repair_budget=repair_budget)
    return {**objective, **decision, "updated_at": decision["created_at"]}
