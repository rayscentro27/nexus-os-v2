"""Canonical completion-campaign execution engine.

This is the consumer of completion-law work.  It deliberately sits on the
Phase15 scheduler boundary and uses the existing governed work-order store and
capability broker; it is not a second scheduler.
"""
from __future__ import annotations

import json
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from nexus_agent_platform.capability_broker import run_capability
from nexus_agent_platform.completion_laws import enforce_cycle_laws
from nexus_agent_platform.governed import persistence, work_orders
from nexus_agent_platform.phase15.common import ROOT, atomic_write_json, utc_now

CAMPAIGN_ID = "NEXUS_COMPLETION_DAY_2026_08_26"
CAMPAIGN_PATH = ROOT / "data/runtime/nexus_completion_campaign.json"
LEDGER_PATH = ROOT / "reports/runtime/campaign_execution_ledger.jsonl"
ENGINE_RECEIPT = ROOT / "reports/runtime/campaign_execution_latest.json"
BACKLOG_STATUSES = {"UNMATERIALIZED", "DIAGNOSING", "READY", "RUNNING", "VERIFYING", "RECOVERING", "RESEARCHING", "WAITING_HUMAN", "BLOCKED_EXTERNAL", "PASS", "DEFERRED_BY_RAY"}
BACKLOG_SPECS = (
    ("REAL_CONDITION_WATCH_END_TO_END", "Condition watch end-to-end", "condition watch", "LOCAL_ONLY", "proof.watchdog"),
    ("REAL_WORLD_CONVERSATION_25", "Real-world conversation 25", "conversation acceptance", "MODEL_DEPENDENT", "model.router"),
    ("CALENDAR_CAPABILITY", "Governed calendar capability", "calendar capability", "NETWORK_DEPENDENT", None),
    ("TRIAD_SEMANTIC_GRADING", "Triad semantic grading", "independent semantic grading", "MODEL_DEPENDENT", "model.router"),
    ("TRUE_VISUAL_ACCEPTANCE", "True visual acceptance", "authenticated image-capable critique", "VISUAL_DEPENDENT", "visual.critic"),
    ("VOICE_FULL_MACHINE_ACCEPTANCE", "Voice full machine acceptance", "Voice-to-Hermes-to-TTS continuity", "VOICE_DEPENDENT", None),
    ("FULL_REGRESSION", "Full regression", "full regression receipt", "LOCAL_ONLY", "tests.run"),
    ("FINAL_IMMUTABLE_CANDIDATE", "Final immutable candidate", "immutable candidate receipt", "RELEASE_DEPENDENT", None),
    ("FINAL_CANARY", "Final canary", "isolated canary verification", "RELEASE_DEPENDENT", None),
    ("RAY_MICROPHONE_ACCEPTANCE", "Ray microphone acceptance", "human microphone evidence", "VOICE_DEPENDENT", None),
    ("PRODUCTION_APPROVAL", "Production approval", "exact Ray approval", "RELEASE_DEPENDENT", None),
)


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _append_jsonl(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(value), sort_keys=True, default=str) + "\n")


def _save_state(state: Dict[str, Any], path: Path = CAMPAIGN_PATH) -> None:
    state["last_updated"] = utc_now()
    atomic_write_json(path, state)


def materialize_backlog(state: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate loose campaign backlog into durable, identity-keyed records."""
    existing = {str(item.get("backlog_id")): dict(item) for item in state.get("backlog_items") or [] if isinstance(item, dict) and item.get("backlog_id")}
    historical = list(state.get("remaining_work") or [])
    for backlog_id, title, criterion, domain, capability in BACKLOG_SPECS:
        if backlog_id in existing:
            continue
        historical_match = next((item for item in historical if title.lower().split()[0] in str(item).lower() or backlog_id.lower() in str(item).lower()), None)
        existing[backlog_id] = {"backlog_id": backlog_id, "title": title, "acceptance_criteria": [criterion], "capability_requirements": [capability] if capability else [], "dependency_domain": domain, "authority_class": "CLASS_1" if capability else "CLASS_3", "machine_executable": bool(capability), "human_gate_required": not bool(capability), "status": "UNMATERIALIZED", "diagnosis_state": "NOT_STARTED", "objective_ids": [], "proof_refs": [], "failure_signature": None, "repair_count": 0, "backlog_version": 1, "historical_text": historical_match, "created_at": utc_now(), "updated_at": utc_now()}
    state["backlog_items"] = list(existing.values())
    return state


def load_campaign(path: Path = CAMPAIGN_PATH, *, materialize_queue: bool = True) -> Dict[str, Any]:
    state = _read(path, {})
    if not isinstance(state, dict):
        state = {}
    state.setdefault("campaign_id", CAMPAIGN_ID)
    state.setdefault("status", "ACTIVE")
    state.setdefault("objective_queue", [])
    state.setdefault("active_work_orders", [])
    state.setdefault("recovering_objectives", [])
    state.setdefault("completed_objectives", [])
    state.setdefault("failure_dispositions", {})
    state.setdefault("cycle_number", 0)
    state.setdefault("objective_queue_seeded", False)
    state.setdefault("feature_backlog_seeded", False)
    materialize_backlog(state)
    # Older campaign checkpoints predate the canonical objective queue. Once
    # the scheduler owns such a checkpoint, materialize one bounded,
    # machine-safe audit objective from the existing backlog. This prevents a
    # flag-only ACTIVE state while preserving human-gated release work.
    if materialize_queue and state.get("status") == "ACTIVE" and state.get("remaining_work") and not state.get("objective_queue") and not state.get("objective_queue_seeded"):
        state["objective_queue"] = [{
            "objective_id": "campaign.next_bounded_completion_audit",
            "title": "Next bounded completion audit",
            "capability_id": "proof.watchdog",
            "dependency_domain": "LOCAL_ONLY",
            "expected_outcome": "fresh proof watchdog receipt",
            "test_only": True,
        }]
        state["objective_queue_seeded"] = True
    if materialize_queue and state.get("status") == "ACTIVE" and state.get("remaining_work") and state.get("objective_queue_seeded") and not state.get("objective_queue") and not state.get("feature_backlog_seeded"):
        # Resume only capabilities that are actually registered. Human gates,
        # production promotion, and provider configuration remain untouched.
        state["objective_queue"] = [
            {"objective_id": "feature.completion_audit", "capability_id": "proof.watchdog", "dependency_domain": "LOCAL_ONLY", "expected_outcome": "fresh completion evidence"},
            {"objective_id": "feature.alpha_research", "capability_id": "research.alpha", "dependency_domain": "MODEL_DEPENDENT", "expected_outcome": "bounded research receipt"},
            {"objective_id": "feature.creative_intelligence", "capability_id": "creative.intelligence", "dependency_domain": "LOCAL_ONLY", "expected_outcome": "creative capability receipt"},
            {"objective_id": "feature.forex_research", "capability_id": "forex.research", "dependency_domain": "LOCAL_ONLY", "expected_outcome": "research-only forex receipt"},
            {"objective_id": "feature.model_router", "capability_id": "model.router", "dependency_domain": "MODEL_DEPENDENT", "expected_outcome": "model routing receipt"},
            {"objective_id": "feature.visual_critic", "capability_id": "visual.critic", "dependency_domain": "VISUAL_DEPENDENT", "expected_outcome": "visual critic receipt"},
        ]
        state["feature_backlog_seeded"] = True
    if materialize_queue and state.get("status") == "ACTIVE" and _machine_backlog(state) and state.get("feature_backlog_seeded") and not state.get("objective_queue") and not any(item.get("status") == "UNMATERIALIZED" and item.get("machine_executable") for item in state.get("backlog_items", [])):
        state["objective_queue"] = [{"objective_id": "campaign.recovery.machine_backlog_diagnosis", "title": "Diagnose next machine-executable campaign backlog item", "capability_id": "proof.watchdog", "dependency_domain": "LOCAL_ONLY", "expected_outcome": "fresh diagnosis/proof receipt", "diagnosis_target": _machine_backlog(state)[0], "test_only": True}]
    if materialize_queue and state.get("status") == "ACTIVE" and not state.get("objective_queue"):
        next_item = next((item for item in state.get("backlog_items", []) if item.get("machine_executable") and item.get("status") in {"UNMATERIALIZED", "READY", "RESEARCHING", "RECOVERING"}), None)
        if next_item:
            next_item["status"] = "READY"
            next_item["diagnosis_state"] = "MATERIALIZED"
            next_item["updated_at"] = utc_now()
            objective_id = f"backlog.{next_item['backlog_id']}.v{next_item.get('backlog_version', 1)}"
            if objective_id not in next_item.get("objective_ids", []):
                next_item.setdefault("objective_ids", []).append(objective_id)
            state["objective_queue"] = [{"objective_id": objective_id, "backlog_id": next_item["backlog_id"], "capability_id": next_item["capability_requirements"][0], "dependency_domain": next_item["dependency_domain"], "expected_outcome": next_item["acceptance_criteria"][0], "acceptance_verified": False}]
    return state


def _domain(objective: Mapping[str, Any]) -> str:
    return str(objective.get("dependency_domain") or objective.get("domain") or "INDEPENDENT")


def _machine_backlog(state: Mapping[str, Any]) -> List[str]:
    human_only = ("microphone", "production approval", "approval", "deploy exact approved")
    return [str(item) for item in state.get("remaining_work") or [] if not any(token in str(item).lower() for token in human_only)]


def _capability(objective: Mapping[str, Any]) -> str:
    return str(objective.get("capability_id") or "system.health")


def _failure_result(objective: Mapping[str, Any]) -> Dict[str, Any]:
    """A real, harmless executor result after dispatch and receiver ACK."""
    return {"status": "FAIL", "failure_stage": "S4_EXECUTOR_STARTED", "failure_signature": str(objective.get("failure_signature") or "CERTIFICATION_BOUNDED_FAILURE"), "error": "bounded certification failure", "test_only": True}


def _execute_one(objective: Mapping[str, Any], *, cycle_id: str, receipt_dir: Path) -> Dict[str, Any]:
    objective_id = str(objective["objective_id"])
    capability = _capability(objective)
    action_id = str(objective.get("action_id") or "system_health.run")
    order = work_orders.create_work_order(
        approval_id=f"campaign:{CAMPAIGN_ID}", action_id=action_id,
        requested_by="nexus_campaign_execution_engine", approved_by="system",
        inputs={"objective_id": objective_id, "cycle_id": cycle_id, "test_only": bool(objective.get("test_only"))},
        expected_outcome=str(objective.get("expected_outcome") or "verified result"),
        idempotency_key=f"{CAMPAIGN_ID}:{objective_id}:{cycle_id}", status="queued",
    )
    work_order_id = order["work_order_id"]
    dispatch_id = f"dispatch_{uuid.uuid4().hex}"
    ack = {"type": "receiver_ack", "campaign_id": CAMPAIGN_ID, "cycle_id": cycle_id, "objective_id": objective_id, "work_order_id": work_order_id, "dispatch_id": dispatch_id, "status": "PASS", "receiver": "campaign_execution_engine", "created_at": utc_now()}
    persistence.emit_audit_event(ack)
    work_orders.transition(work_order_id, "running", telemetry_run_id=dispatch_id)
    if objective.get("force_failure"):
        raw = _failure_result(objective)
        terminal = "failed"
    else:
        raw = run_capability(capability, dict(objective.get("args") or {}), receipt_dir=receipt_dir)
        terminal = "completed" if raw.get("status") == "PASS" else "failed"
    result = work_orders.record_result(work_order_id, status=terminal, result=raw, error=None if terminal == "completed" else str(raw.get("error") or raw.get("status")), telemetry_run_id=dispatch_id)
    result_ref = str(receipt_dir / f"{raw.get('receipt_id')}.json") if raw.get("receipt_id") else None
    verified = terminal == "completed" and bool(result_ref and Path(result_ref).exists() and raw.get("status") == "PASS") and (not objective.get("backlog_id") or bool(objective.get("acceptance_verified")))
    if terminal == "failed":
        failure = {"status": "FAIL", "objective_id": objective_id, "stage": raw.get("failure_stage", "S4_EXECUTOR_STARTED"), "reason": raw.get("error", "bounded failure"), "failure_signature": raw.get("failure_signature"), "machine_solvable": True, "solution_known": True, "repair_count": int(objective.get("repair_count", 0))}
    else:
        failure = None
    return {"objective_id": objective_id, "backlog_id": objective.get("backlog_id"), "work_order_id": work_order_id, "dispatch_id": dispatch_id, "receiver_ack": "PASS", "execution": raw, "result_ref": result_ref, "verification": "PASS" if verified else "PASS_RECEIPT_ACCEPTANCE_PENDING" if terminal == "completed" and objective.get("backlog_id") else "FAIL", "state": "COMPLETED" if verified else "VERIFYING" if terminal == "completed" and objective.get("backlog_id") else "RECOVERING" if failure else "FAIL", "failure_event": failure, "domain": _domain(objective)}


def consume_completion_law_work(decisions: Sequence[Mapping[str, Any]], *, scheduler_instance: str, state_path: Path = CAMPAIGN_PATH, ledger_path: Path = LEDGER_PATH, receipt_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Consume Phase15 completion-law directives through the same scheduler.

    A directive is not acknowledged as consumed until this function has
    created and dispatched a governed work order (or the directive is empty).
    """
    state = load_campaign(state_path, materialize_queue=False)
    generated = _consume_directives(decisions, state=state)
    _save_state(state, state_path)
    if not generated:
        return {"generated_work": [], "execution": None, "status": "NO_WORK"}
    execution = run_campaign_cycle(scheduler_instance=scheduler_instance, state_path=state_path, ledger_path=ledger_path, receipt_dir=receipt_dir)
    return {"generated_work": generated, "execution": execution, "status": "DISPATCHED"}


def _consume_directives(decisions: Sequence[Mapping[str, Any]], *, state: Dict[str, Any]) -> List[Dict[str, Any]]:
    generated: List[Dict[str, Any]] = []
    queue = list(state.get("objective_queue") or [])
    for decision in decisions:
        for directive in decision.get("work") or []:
            signature = str(decision.get("failure_signature") or "unknown")
            if directive == "continue_next_bounded_objective":
                continue
            if directive in {"create_recovery_work", "create_diagnosis_work", "bounded_research", "architecture_alternative", "repair_hermes_delivery"}:
                oid = f"recovery.{signature}.{directive}"
                if any(str(item.get("objective_id")) == oid for item in queue if isinstance(item, dict)):
                    continue
                # Keep generated recovery executable only through a capability
                # present in the canonical manifest. More specialized
                # diagnosis/research handlers can be added when registered;
                # they must never be guessed from a directive string.
                capability = "system.health"
                generated.append({"objective_id": oid, "title": directive, "capability_id": capability, "dependency_domain": "INDEPENDENT", "expected_outcome": f"verified {directive}", "repair_of": decision.get("objective_id"), "failure_signature": signature, "repair_count": int(decision.get("repair_count", 0)), "test_only": True})
    queue.extend(generated)
    state["objective_queue"] = queue
    return generated


def run_campaign_cycle(*, scheduler_instance: str, objectives: Optional[Sequence[Mapping[str, Any]]] = None, state_path: Path = CAMPAIGN_PATH, ledger_path: Path = LEDGER_PATH, receipt_dir: Optional[Path] = None, max_workers: int = 3) -> Dict[str, Any]:
    """Run one canonical scheduled campaign cycle and consume its decisions."""
    state = load_campaign(state_path, materialize_queue=objectives is None)
    cycle_no = int(state.get("cycle_number", 0)) + 1
    cycle_id = f"{scheduler_instance}:{cycle_no}"
    if objectives is not None:
        existing = {str(item.get("objective_id")): dict(item) for item in state.get("objective_queue") or [] if isinstance(item, dict)}
        existing.update({str(item.get("objective_id")): dict(item) for item in objectives})
        state["objective_queue"] = list(existing.values())
    queue = [dict(item) for item in state.get("objective_queue") or [] if isinstance(item, dict)]
    # Only executable, dependency-free objectives are dispatched this cycle.
    runnable = [item for item in queue if not item.get("dependency_ids") and item.get("status", "READY") not in {"COMPLETED", "WAITING_HUMAN", "BLOCKED_EXTERNAL"}]
    state["cycle_number"] = cycle_no
    state["scheduler_instance"] = scheduler_instance
    state["campaign_health"] = "RUNNING" if runnable else "STALLED" if queue else "WAITING_HUMAN"
    _save_state(state, state_path)
    receipt_dir = receipt_dir or (ROOT / "reports/runtime/campaign_execution" / str(cycle_no))
    results: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_execute_one, item, cycle_id=cycle_id, receipt_dir=receipt_dir) for item in runnable]
        for future in as_completed(futures):
            results.append(future.result())
    events = [row["failure_event"] for row in results if row.get("failure_event")]
    decisions = enforce_cycle_laws(events)
    generated = _consume_directives(decisions.get("decisions", []), state=state)
    completed = list(state.get("completed_objectives") or [])
    for row in results:
        if row["state"] == "COMPLETED" and row["objective_id"] not in completed:
            completed.append(row["objective_id"])
        if row.get("backlog_id"):
            item = next((candidate for candidate in state.get("backlog_items", []) if candidate.get("backlog_id") == row["backlog_id"]), None)
            if item:
                item["status"] = "PASS" if row["verification"] == "PASS" else "VERIFYING"
                item["proof_refs"] = list(dict.fromkeys([*item.get("proof_refs", []), *([row["result_ref"]] if row.get("result_ref") else [])]))
                item["updated_at"] = utc_now()
    state["completed_objectives"] = completed
    state["active_work_orders"] = [row["work_order_id"] for row in results if row["state"] == "RECOVERING"]
    state["recovering_objectives"] = [row["objective_id"] for row in results if row["state"] == "RECOVERING"]
    state["failure_dispositions"].update({row["objective_id"]: "queued repair" for row in results if row.get("failure_event")})
    finished_or_recovering = set(completed) | {row["objective_id"] for row in results if row["state"] in {"RECOVERING", "VERIFYING"}}
    state["objective_queue"] = [item for item in state.get("objective_queue", []) if str(item.get("objective_id")) not in finished_or_recovering]
    state["campaign_health"] = "RECOVERING" if state["recovering_objectives"] else "RUNNING" if state["objective_queue"] else "STALLED" if _machine_backlog(state) else "PASS"
    _save_state(state, state_path)
    cycle = {"schema_version": "nexus.campaign-execution-receipt.v1", "campaign_id": state["campaign_id"], "scheduler_instance": scheduler_instance, "cycle_id": cycle_id, "cycle_number": cycle_no, "objectives": results, "completion_law_decisions": decisions.get("decisions", []), "generated_work": generated, "active_executor_count": len([r for r in results if r["state"] == "RECOVERING"]), "queued_dispatch_count": len(generated), "campaign_health": state["campaign_health"], "next_runnable_objective": (state["objective_queue"] or [{}])[0].get("objective_id") if state["objective_queue"] else None, "created_at": utc_now()}
    _append_jsonl(ledger_path, cycle)
    atomic_write_json(ENGINE_RECEIPT, cycle)
    return cycle


def campaign_status(path: Path = CAMPAIGN_PATH) -> Dict[str, Any]:
    state = load_campaign(path)
    queue = state.get("objective_queue") or []
    active = state.get("active_work_orders") or []
    recovering = state.get("recovering_objectives") or []
    state["campaign_health"] = "RUNNING" if queue or active or recovering else "STALLED" if _machine_backlog(state) else state.get("campaign_health", "PASS")
    return {"campaign_id": state.get("campaign_id"), "campaign_state": state.get("status"), "campaign_health": state["campaign_health"], "active_executors": len(active), "queued_executable_work": len(queue), "recovering_work": len(recovering), "next_runnable_objective": queue[0].get("objective_id") if queue and isinstance(queue[0], dict) else None}
