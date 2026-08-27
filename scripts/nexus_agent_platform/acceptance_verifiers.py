"""Registered acceptance verifiers for the canonical campaign engine.

Verifiers consume receipts and read-only state.  They never accept the legacy
``acceptance_verified`` flag as evidence.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class VerificationResult:
    status: str
    criterion_id: str
    backlog_id: str
    checked_at: str
    evidence_refs: tuple[str, ...]
    observed_facts: Mapping[str, Any]
    failed_checks: tuple[str, ...] = ()
    verification_receipt_id: str = ""
    next_disposition: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status, "criterion_id": self.criterion_id,
            "backlog_id": self.backlog_id, "checked_at": self.checked_at,
            "evidence_refs": list(self.evidence_refs),
            "observed_facts": dict(self.observed_facts),
            "failed_checks": list(self.failed_checks),
            "verification_receipt_id": self.verification_receipt_id,
            "next_disposition": self.next_disposition,
        }


Verifier = Callable[[Mapping[str, Any]], VerificationResult]


def _receipt_exists(context: Mapping[str, Any]) -> VerificationResult:
    criterion = context["criterion"]
    backlog_id = str(context["backlog"]["backlog_id"])
    ref = str(context.get("result_ref") or "")
    exists = bool(ref and Path(ref).is_file())
    return VerificationResult(
        "PASS" if exists else "INSUFFICIENT_EVIDENCE", str(criterion["criterion_id"]),
        backlog_id, _now(), (ref,) if exists else (), {"receipt_exists": exists},
        () if exists else ("capability receipt is absent",),
        f"verification-{backlog_id}-{criterion['criterion_id']}-{int(exists)}",
        "PASS" if exists else "RECOVERING",
    )


def _condition_watch(context: Mapping[str, Any]) -> VerificationResult:
    """Verify an actual condition-watch receipt, never a helper return value."""
    criterion = context["criterion"]
    backlog_id = str(context["backlog"]["backlog_id"])
    evidence = context.get("condition_watch_evidence")
    if evidence is None and context.get("result_ref"):
        try:
            evidence = json.loads(Path(str(context["result_ref"])).read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            evidence = None
    checks = (
        "governed_synthetic_source", "watch_persisted", "no_false_trigger",
        "source_transition_reread", "exact_entity_match", "verification_receipt",
        "telegram_message_id", "delivery_receipt", "watch_closed", "idempotent_repeat",
    )
    observed = {name: bool(evidence and evidence.get(name)) for name in checks}
    missing = tuple(name for name, value in observed.items() if not value)
    status = "PASS" if not missing else "INSUFFICIENT_EVIDENCE"
    refs = tuple(str(x) for x in (evidence or {}).get("proof_refs", []) if x)
    return VerificationResult(status, str(criterion["criterion_id"]), backlog_id, _now(), refs,
                              observed, missing,
                              f"verification-{backlog_id}-{criterion['criterion_id']}",
                              "PASS" if not missing else "RECOVERING")


REGISTRY: dict[str, Verifier] = {
    "receipt_exists.v1": _receipt_exists,
    "condition_watch.e2e.v1": _condition_watch,
}


def resolve_verifier(backlog_id: str, criterion: Mapping[str, Any]) -> tuple[str, Verifier] | None:
    requested = str(criterion.get("verifier") or "")
    if requested in REGISTRY:
        return requested, REGISTRY[requested]
    if backlog_id == "REAL_CONDITION_WATCH_END_TO_END":
        return "condition_watch.e2e.v1", REGISTRY["condition_watch.e2e.v1"]
    # A generic receipt verifier is explicit and bounded; it is not a claim
    # that a receipt satisfies a specialized product acceptance contract.
    if requested == "receipt_exists.v1":
        return requested, REGISTRY[requested]
    return None


def registry_metadata() -> list[dict[str, Any]]:
    return [{"verifier_id": key, "registered": True} for key in sorted(REGISTRY)]
