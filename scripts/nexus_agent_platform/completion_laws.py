"""Permanent completion and Hermes communication laws.

This module is the policy boundary for cycle events. It returns explicit work
and communication outcomes; callers must execute and verify the returned work.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:20]


def evaluate_event(event: Dict[str, Any], *, hermes_delivery_verified: bool = False) -> Dict[str, Any]:
    """Convert one technical event into a non-terminal governed decision."""
    status = str(event.get("status", "UNKNOWN")).upper()
    machine = bool(event.get("machine_solvable", True))
    repeated = int(event.get("same_signature_count", event.get("repair_count", 0)) or 0)
    signature = str(event.get("failure_signature") or _fingerprint({"objective_id": event.get("objective_id"), "stage": event.get("stage"), "reason": event.get("reason")}))
    result: Dict[str, Any] = {"status": status, "objective_id": event.get("objective_id", "UNKNOWN"), "failure_signature": signature, "diagnosis": "NONE", "work": [], "communication": "NONE", "campaign_action": "CONTINUE", "created_at": _now()}
    if status == "PARTIAL":
        result.update(status="ACTIVE", diagnosis="PARTIAL_IS_NOT_TERMINAL", work=["continue_next_bounded_objective"])
    elif status in {"FAIL", "FAILED"}:
        result["status"] = "RECOVERING" if machine else "BLOCKED_EXTERNAL"
        result["diagnosis"] = "FIRST_FAILED_STAGE" if event.get("stage") else "FAILURE_EVIDENCE_REQUIRED"
        if machine:
            result["work"].append("create_recovery_work")
            # A repair hypothesis is not knowledge until it has supporting
            # evidence and a successful compatible receipt.  Unknown is the
            # safe default; every first failure therefore learns before repair.
            knowledge = str(event.get("repair_knowledge_state") or ("PROVEN" if event.get("solution_known") is True and event.get("repair_evidence_refs") else "UNKNOWN"))
            result["repair_knowledge_state"] = knowledge
            if knowledge != "PROVEN": result["work"].append("bounded_research")
            if repeated >= 2:
                result["work"].append("architecture_alternative")
                result["diagnosis"] = "ARCHITECTURE_ALTERNATIVE"
    elif status == "UNKNOWN":
        result.update(status="RECOVERING", diagnosis="MISSING_EVIDENCE", work=["create_diagnosis_work"])
    elif status == "WAITING_HUMAN":
        if hermes_delivery_verified:
            result.update(communication="HERMES_DELIVERED", campaign_action="WAIT_FOR_EXACT_GATE")
        else:
            result.update(status="COMMUNICATION_FAIL", diagnosis="HUMAN_GATE_DELIVERY_UNVERIFIED", work=["repair_hermes_delivery"])
    if int(event.get("risk_level", event.get("risk", 0)) or 0) >= 3 or str(event.get("authority_class", "")) == "CLASS_3":
        result["communication"] = "PROACTIVE_RAY_GATE" if hermes_delivery_verified else "COMMUNICATION_FAIL"
        if not hermes_delivery_verified: result["work"].append("repair_hermes_delivery")
    result["executive_decision_brief"] = build_executive_decision_brief(event, result)
    return result


def build_executive_decision_brief(event: Dict[str, Any], decision: Dict[str, Any]) -> Dict[str, Any]:
    return {"gate_id": event.get("gate_id"), "objective_id": event.get("objective_id", "UNKNOWN"), "state": decision.get("status"), "stage": event.get("stage", "UNKNOWN"), "what_happened": event.get("what_happened", event.get("reason", "No failure reason recorded")), "why_it_matters": event.get("why_it_matters", "Nexus requires an explicit decision at this gate."), "what_nexus_did": event.get("what_nexus_did", "Nexus preserved the checkpoint and continues independent work."), "decision_needed": decision.get("work", []), "ray_action": event.get("exact_ray_action", "NONE"), "evidence": list(event.get("proof_refs", [])), "safe_boundary": "No approval or production mutation is implied."}


def close_exact_gate(event: Dict[str, Any], *, reply_gate_id: str, reply_decision: str) -> Dict[str, Any]:
    gate_id = str(event.get("gate_id", ""))
    if not gate_id or gate_id != reply_gate_id:
        return {"status": "IGNORED", "reason": "reply_does_not_match_exact_gate", "campaign_action": "CONTINUE"}
    return {"status": "GATE_CLOSED", "gate_id": gate_id, "decision": reply_decision, "campaign_action": "RESUME_FROM_CHECKPOINT", "checkpoint_sha": event.get("checkpoint_sha", "UNKNOWN"), "created_at": _now()}


def enforce_cycle_laws(events: Iterable[Dict[str, Any]], *, receipt_path: Optional[Path] = None, hermes_sender: Optional[Callable[[Dict[str, Any]], bool]] = None) -> Dict[str, Any]:
    decisions = []
    for event in events:
        status = str(event.get("status", "UNKNOWN")).upper()
        requires_human = status == "WAITING_HUMAN" or int(event.get("risk_level", event.get("risk", 0)) or 0) >= 3 or str(event.get("authority_class", "")) == "CLASS_3"
        # Delivery is an action, not a post-condition.  Invoke Hermes before
        # evaluating the human gate so an undelivered gate can never become
        # WAITING_HUMAN by accident.
        delivery = None
        if requires_human and hermes_sender:
            provisional = evaluate_event(event, hermes_delivery_verified=True)
            try:
                delivery = hermes_sender(provisional["executive_decision_brief"])
            except Exception as exc:  # transport failures become governed work
                delivery = {"delivered": False, "error": type(exc).__name__}
        delivered = bool(delivery.get("delivered")) if isinstance(delivery, dict) else bool(delivery)
        decision = evaluate_event(event, hermes_delivery_verified=delivered)
        if requires_human:
            decision["delivery_receipt"] = delivery or {"delivered": False, "reason": "sender_not_configured"}
        if requires_human and not delivered:
            decision.update(status="COMMUNICATION_FAIL", communication="COMMUNICATION_FAIL", work=[*decision.get("work", []), "repair_hermes_delivery"])
        elif requires_human:
            decision["communication"] = "PROACTIVE_RAY_GATE" if int(event.get("risk_level", event.get("risk", 0)) or 0) >= 3 or str(event.get("authority_class", "")) == "CLASS_3" else "HERMES_DELIVERED"
        decisions.append(decision)
    receipt = {"schema_version": "nexus.completion-laws-receipt.v1", "status": "PASS", "terminal_partial_forbidden": True, "decisions": decisions, "created_at": _now()}
    if receipt_path:
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt
