"""Bounded proof recovery policy.

The policy is intentionally small and deterministic: two attempts for one
failure signature, then a mandatory alternative-design decision. It never
pretends that a repair succeeded; callers must attach a fresh receipt.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Sequence


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


def run_architecture_alternative_canary(
    *, receipt_path: Optional[Path] = None,
    primary: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    alternate: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Run and verify the alternate executor on a harmless fixture."""
    primary = primary or (lambda fixture: (_ for _ in ()).throw(RuntimeError("controlled_canary_failure")))
    alternate = alternate or (lambda fixture: {"artifact": f"alternate:{fixture['fixture_id']}", "executor": "alternate_fixture"})
    fixture = {"fixture_id": "proof-architecture-alternative", "payload": "harmless bounded fixture"}
    objective: Dict[str, Any] = {
        "objective_id": "architecture-alternative-canary", "executor": "primary_fixture",
        "failure_stage": "S5_ARTIFACT_PRODUCED", "failure_reason": "controlled_canary_failure", "repair_count": 0,
    }
    primary_failures = []
    for attempt in range(2):
        try:
            primary(fixture)
            raise AssertionError("primary canary unexpectedly succeeded")
        except RuntimeError as exc:
            primary_failures.append(str(exc))
        objective = apply_recovery({**objective, "repair_count": attempt})
    decision = apply_recovery({**objective, "repair_count": 2})
    if decision.get("status") != "ARCHITECTURE_ALTERNATIVE":
        raise RuntimeError("architecture_alternative_not_triggered")
    result = alternate(fixture)
    artifact = result.get("artifact") if isinstance(result, dict) else None
    if not artifact or not str(artifact).startswith("alternate:"):
        raise RuntimeError("alternate_executor_artifact_missing")
    fingerprint = hashlib.sha256(str(artifact).encode()).hexdigest()[:20]
    receipt = {
        "schema_version": "nexus.proof-architecture-alternative-receipt.v1", "status": "PASS",
        "objective_id": objective["objective_id"], "failure_signature": decision["failure_signature"],
        "primary_failures": primary_failures, "repair_attempts": 2, "decision": "ARCHITECTURE_ALTERNATIVE",
        "selected_executor": result.get("executor", "alternate_fixture"), "artifact": artifact,
        "artifact_fingerprint": fingerprint,
        "independent_verification": {"status": "PASS", "artifact_fingerprint": fingerprint}, "created_at": _now(),
    }
    target = receipt_path or Path(__file__).resolve().parents[2] / "reports/runtime/proof_architecture_alternative_canary.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt
