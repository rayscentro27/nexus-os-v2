"""Exact, high-priority Telegram responses for governed human gates."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from .completion_laws import close_exact_gate
from .truth_kernel import DEFAULT_DB_PATH, TruthKernel

ROOT = Path(__file__).resolve().parents[2]
LEDGER_PATH = ROOT / "data/runtime/nexus_human_gate_ledger.json"
RESPONSE = re.compile(r"^(ACK\s+TEST|PASS|FAIL|APPROVE|REJECT)\s+([A-Za-z0-9][A-Za-z0-9_.:-]{2,100})(?:\s+(.{1,240}))?$", re.I)
TRUTH_GATE_RESPONSE = re.compile(r"^(APPROVE|HOLD)\s+([A-Za-z0-9][A-Za-z0-9_.:-]{2,100})$", re.I)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(path: Path = LEDGER_PATH) -> Dict[str, Any]:
    try:
        import json
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {"gates": []}
    except (OSError, ValueError, TypeError):
        return {"gates": []}


def _write(value: Dict[str, Any], path: Path = LEDGER_PATH) -> None:
    import json
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def create_gate(gate_id: str, *, objective_id: str, candidate_sha: str, expected: str = "ACK_TEST", checkpoint_sha: str = "UNKNOWN", brief: Optional[Dict[str, Any]] = None, path: Path = LEDGER_PATH) -> Dict[str, Any]:
    ledger = _read(path)
    gates = [row for row in ledger.get("gates", []) if isinstance(row, dict)]
    if any(row.get("gate_id") == gate_id for row in gates):
        return next(row for row in gates if row.get("gate_id") == gate_id)
    gate = {"gate_id": gate_id, "objective_id": objective_id, "candidate_sha": candidate_sha, "expected_response": expected, "checkpoint_sha": checkpoint_sha, "status": "OPEN", "brief": brief or {}, "created_at": _now()}
    gates.append(gate)
    ledger.update({"schema_version": "nexus.human-gate-ledger.v1", "gates": gates, "updated_at": _now()})
    _write(ledger, path)
    return gate


def parse_response(text: str) -> Optional[Dict[str, str]]:
    match = RESPONSE.fullmatch(re.sub(r"\s+", " ", text.strip()))
    if not match:
        return None
    action, gate_id, explanation = match.groups()
    action = action.upper().replace(" ", "_")
    return {"action": action, "gate_id": gate_id, "explanation": explanation or ""}


def _truth_kernel_gate_response(text: str, *, chat_id: Optional[int], authorized_chat_ids: set[int],
                                db_path: Path) -> Dict[str, Any]:
    match = TRUTH_GATE_RESPONSE.fullmatch(re.sub(r"\s+", " ", text.strip()))
    if not match:
        return {"route": "TRUTH_KERNEL_HUMAN_GATE", "outcome": "DENIED_MALFORMED", "response": "Malformed gate response. No Nexus state was changed."}
    action, gate_id = match.group(1).upper(), match.group(2)
    kernel = TruthKernel(db_path)
    actor = str(chat_id) if chat_id is not None else None
    if chat_id is None or chat_id not in authorized_chat_ids:
        event_id = kernel.record_human_gate_event(gate_id, action=action, outcome="DENIED_UNAUTHORIZED_CHAT", actor=actor, source="telegram_human_gate")
        return {"route": "TRUTH_KERNEL_HUMAN_GATE", "outcome": "DENIED_UNAUTHORIZED_CHAT", "gate_id": gate_id, "gate_event_id": event_id, "response": "This Telegram identity is not authorized for Nexus human gates. No Nexus state was changed."}
    gate = kernel.get_human_gate(gate_id)
    if not gate:
        event_id = kernel.record_human_gate_event(gate_id, action=action, outcome="DENIED_UNKNOWN_GATE", actor=actor, source="telegram_human_gate")
        return {"route": "TRUTH_KERNEL_HUMAN_GATE", "outcome": "DENIED_UNKNOWN_GATE", "gate_id": gate_id, "gate_event_id": event_id, "response": "I could not find that active Nexus gate. No Nexus state was changed."}
    exact_action = str(gate.get("exact_action", ""))
    requested_action = f"{action} {gate_id}"
    if action == "HOLD":
        event_id = kernel.record_human_gate_event(gate_id, action=action, outcome="HOLD_NOT_APPROVED", actor=actor, source="telegram_human_gate", reason="HOLD never grants authority", run_id=gate.get("run_id"))
        return {"route": "TRUTH_KERNEL_HUMAN_GATE", "outcome": "HOLD_NOT_APPROVED", "gate_id": gate_id, "gate_event_id": event_id, "response": f"Gate {gate_id} is held. No approval or Nexus action was granted."}
    if exact_action != requested_action:
        event_id = kernel.record_human_gate_event(gate_id, action=action, outcome="DENIED_WRONG_ACTION", actor=actor, source="telegram_human_gate", reason="exact action mismatch", run_id=gate.get("run_id"))
        return {"route": "TRUTH_KERNEL_HUMAN_GATE", "outcome": "DENIED_WRONG_ACTION", "gate_id": gate_id, "gate_event_id": event_id, "response": "That gate requires a different exact action. No Nexus state was changed."}
    if gate.get("status") != "PENDING":
        event_id = kernel.record_human_gate_event(gate_id, action=action, outcome="DENIED_REPLAY_OR_CLOSED", actor=actor, source="telegram_human_gate", reason=f"gate status is {gate.get('status')}", run_id=gate.get("run_id"))
        return {"route": "TRUTH_KERNEL_HUMAN_GATE", "outcome": "DENIED_REPLAY_OR_CLOSED", "gate_id": gate_id, "gate_event_id": event_id, "response": "That gate is no longer pending. No approval was repeated."}
    if kernel.approve_human_gate(gate_id, requested_action, approved_by=f"telegram:{actor}"):
        event_id = kernel.record_human_gate_event(gate_id, action=action, outcome="APPROVED", actor=actor, source="telegram_human_gate", run_id=gate.get("run_id"))
        return {"route": "TRUTH_KERNEL_HUMAN_GATE", "outcome": "APPROVED", "gate_id": gate_id, "gate_event_id": event_id, "authority_scope": [exact_action], "response": f"Gate {gate_id} approved. Authority is limited to its exact requested action."}
    current = kernel.get_human_gate(gate_id) or {}
    outcome = "DENIED_EXPIRED" if current.get("status") == "EXPIRED" else "DENIED_NOT_PENDING"
    event_id = kernel.record_human_gate_event(gate_id, action=action, outcome=outcome, actor=actor, source="telegram_human_gate", reason="TruthKernel rejected approval", run_id=gate.get("run_id"))
    return {"route": "TRUTH_KERNEL_HUMAN_GATE", "outcome": outcome, "gate_id": gate_id, "gate_event_id": event_id, "response": "TruthKernel rejected that gate approval. No Nexus state was changed."}


def route_response(text: str, *, sender: Optional[Callable[[str], Any]] = None, path: Path = LEDGER_PATH,
                  chat_id: Optional[int] = None, authorized_chat_ids: Optional[set[int]] = None,
                  truth_kernel_db_path: Path = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    if authorized_chat_ids is not None and (TRUTH_GATE_RESPONSE.match(re.sub(r"\s+", " ", text.strip())) or re.match(r"^(?:APPROVE|HOLD)\b", text.strip(), re.I)):
        return _truth_kernel_gate_response(text, chat_id=chat_id, authorized_chat_ids=authorized_chat_ids, db_path=Path(truth_kernel_db_path))
    parsed = parse_response(text)
    if not parsed:
        return None
    ledger = _read(path)
    gates = [row for row in ledger.get("gates", []) if isinstance(row, dict)]
    gate = next((row for row in gates if row.get("gate_id") == parsed["gate_id"]), None)
    if not gate:
        return {"route": "HUMAN_GATE", "outcome": "UNKNOWN_GATE", "response": "I could not find an active matching gate. No Nexus state was changed.", "gate_id": parsed["gate_id"]}
    expected = str(gate.get("expected_response", "ACK_TEST")).upper()
    if gate.get("status") == "CLOSED":
        return {"route": "HUMAN_GATE", "outcome": "ALREADY_CLOSED", "gate_id": parsed["gate_id"], "response": f"That gate is already closed. No action was repeated.\nGate: {parsed['gate_id']}"}
    if parsed["action"] != expected:
        return {"route": "HUMAN_GATE", "outcome": "WRONG_RESPONSE_TYPE", "gate_id": parsed["gate_id"], "response": f"That gate expects {expected.replace('_', ' ')}. No Nexus state was changed."}
    ray_response = {"action": parsed["action"], "explanation": parsed["explanation"], "received_at": _now()}
    closure = close_exact_gate(gate, reply_gate_id=parsed["gate_id"], reply_decision=parsed["action"])
    gate.update({"status": "CLOSED", "ray_response": ray_response, "closure": closure, "closed_at": _now()})
    ledger["gates"] = gates
    ledger["updated_at"] = _now()
    _write(ledger, path)
    resume = {"receipt_id": f"resume_{parsed['gate_id']}", "gate_id": parsed["gate_id"], "campaign_action": "RESUME_FROM_CHECKPOINT", "checkpoint_sha": gate.get("checkpoint_sha", "UNKNOWN"), "created_at": _now()}
    gate["resume_receipt"] = resume
    _write(ledger, path)
    response = f"Nexus communication test passed.\n\nI received your acknowledgement and matched it to:\n{parsed['gate_id']}\n\nThe gate is closed and Nexus resumed automatically.\n\nYour action: None."
    delivery = None
    if sender:
        try:
            delivery = sender(response)
        except Exception as exc:
            delivery = {"delivered": False, "error": type(exc).__name__}
    delivered = bool(delivery.get("delivered")) if isinstance(delivery, dict) else bool(delivery) if delivery is not None else False
    gate["confirmation_delivery"] = delivery or {"delivered": False, "reason": "sender_not_configured"}
    _write(ledger, path)
    return {"route": "HUMAN_GATE", "outcome": "CLOSED", "gate_id": parsed["gate_id"], "closure": closure, "resume": resume, "confirmation_delivered": delivered, "response": response}
