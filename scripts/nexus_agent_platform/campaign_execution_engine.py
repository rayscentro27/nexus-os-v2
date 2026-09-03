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
from nexus_agent_platform.acceptance_verifiers import resolve_verifier

CAMPAIGN_ID = "NEXUS_COMPLETION_DAY_2026_08_26"
CAMPAIGN_PATH = ROOT / "data/runtime/nexus_completion_campaign.json"
LEDGER_PATH = ROOT / "reports/runtime/campaign_execution_ledger.jsonl"
ENGINE_RECEIPT = ROOT / "reports/runtime/campaign_execution_latest.json"
BACKLOG_STATUSES = {"UNMATERIALIZED", "DIAGNOSING", "READY", "RUNNING", "VERIFYING", "RECOVERING", "RESEARCHING", "WAITING_HUMAN", "BLOCKED_EXTERNAL", "PASS", "DEFERRED_BY_RAY"}
# Full regression is a certification workload, not a company-dispatch
# dependency.  Running it in the same bounded worker pool allowed a heavy or
# failing test harness to starve otherwise healthy department work.
CERTIFICATION_ONLY_BACKLOGS = {"FULL_REGRESSION"}
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
    specs = () if state.get("synthetic_campaign") else BACKLOG_SPECS
    for backlog_id, title, criterion, domain, capability in specs:
        if backlog_id in existing:
            continue
        historical_match = next((item for item in historical if title.lower().split()[0] in str(item).lower() or backlog_id.lower() in str(item).lower()), None)
        human = backlog_id in {"RAY_MICROPHONE_ACCEPTANCE", "PRODUCTION_APPROVAL"}
        verifier = "condition_watch.e2e.v1" if backlog_id == "REAL_CONDITION_WATCH_END_TO_END" else None
        existing[backlog_id] = {"backlog_id": backlog_id, "title": title, "acceptance_criteria": [{"criterion_id": f"{backlog_id}.acceptance", "description": criterion, "required_evidence_types": ["capability_receipt", "verification_receipt"], "status": "PENDING", "proof_refs": [], "verifier": verifier, "last_verified_at": None, "failure_reason": None}], "capability_requirements": [capability] if capability else [], "dependency_domain": domain, "authority_class": "CLASS_1", "machine_executable": not human, "capability_available": bool(capability), "capability_gap": (not bool(capability)) and not human, "human_gate_required": human, "status": "UNMATERIALIZED", "diagnosis_state": "NOT_STARTED", "objective_ids": [], "proof_refs": [], "failure_signature": None, "repair_count": 0, "backlog_version": 1, "historical_text": historical_match, "created_at": utc_now(), "updated_at": utc_now()}
    for item in existing.values():
        item.setdefault("machine_executable", True)
        item.setdefault("capability_available", bool(item.get("capability_requirements")))
        item.setdefault("capability_gap", not item["capability_available"])
        item.setdefault("human_gate_required", item.get("backlog_id") in {"RAY_MICROPHONE_ACCEPTANCE", "PRODUCTION_APPROVAL"})
        if item.get("acceptance_criteria") and isinstance(item["acceptance_criteria"][0], str):
            item["acceptance_criteria"] = [{"criterion_id": f"{item['backlog_id']}.acceptance", "description": item["acceptance_criteria"][0], "required_evidence_types": ["capability_receipt", "verification_receipt"], "status": "PENDING", "proof_refs": [], "verifier": "nexus_acceptance_verifier", "last_verified_at": None, "failure_reason": None}]
        for criterion_record in item.get("acceptance_criteria") or []:
            if criterion_record.get("verifier") == "nexus_acceptance_verifier" and item.get("backlog_id") == "REAL_CONDITION_WATCH_END_TO_END":
                criterion_record["verifier"] = "condition_watch.e2e.v1"
            if item.get("backlog_id") != "REAL_CONDITION_WATCH_END_TO_END" and criterion_record.get("verifier") == "receipt_exists.v1":
                # Receipt presence alone cannot certify a specialized
                # acceptance contract. Leave it unresolved for Product
                # Evolution to materialize the correct verifier.
                criterion_record["verifier"] = None
        item["machine_executable"] = bool(item.get("machine_executable", True)) and not bool(item.get("human_gate_required"))
        item["capability_gap"] = bool(item.get("capability_gap")) and bool(item.get("machine_executable"))
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
    if materialize_queue and state.get("status") == "ACTIVE" and (not state.get("synthetic_campaign") or not state.get("objective_queue")):
        queued_ids = {str(x.get("backlog_id")) for x in state.get("objective_queue", []) if isinstance(x, dict)}
        for next_item in (item for item in state.get("backlog_items", []) if item.get("machine_executable") and item.get("status") in {"UNMATERIALIZED", "READY", "RESEARCHING", "RECOVERING", "VERIFYING"} and item.get("backlog_id") not in set(state.get("completed_backlog", [])) and str(item.get("backlog_id")) not in queued_ids):
            verifying = next_item.get("status") == "VERIFYING"
            if not verifying:
                next_item["status"] = "READY"
            next_item["diagnosis_state"] = "MATERIALIZED"
            next_item["updated_at"] = utc_now()
            objective_id = f"backlog.{next_item['backlog_id']}.verify.v{next_item.get('backlog_version', 1)}" if verifying else f"backlog.{next_item['backlog_id']}.v{next_item.get('backlog_version', 1)}"
            if objective_id not in next_item.get("objective_ids", []):
                next_item.setdefault("objective_ids", []).append(objective_id)
            capability = (next_item.get("capability_requirements") or [None])[0]
            objective = None
            if verifying:
                criterion = (next_item.get("acceptance_criteria") or [{}])[0]
                objective = {"objective_id": objective_id, "backlog_id": next_item["backlog_id"], "capability_id": "acceptance.verifier", "dependency_domain": next_item["dependency_domain"], "expected_outcome": "registered acceptance verification", "criterion": criterion, "result_ref": (criterion.get("proof_refs") or [None])[-1], "verification_only": True}
            elif capability:
                objective = {"objective_id": objective_id, "backlog_id": next_item["backlog_id"], "capability_id": capability, "dependency_domain": next_item["dependency_domain"], "expected_outcome": next_item["acceptance_criteria"][0]["description"], "acceptance_verified": False, "verification_only": False}
            else:
                objective = {"objective_id": f"capability-gap.{next_item['backlog_id']}.v1", "backlog_id": next_item["backlog_id"], "capability_id": "product.evolution.bridge", "dependency_domain": next_item["dependency_domain"], "expected_outcome": "Product Evolution capability-gap handoff", "capability_gap": True, "acceptance_verified": False}
            if objective:
                state["objective_queue"].append(objective)
                queued_ids.add(str(next_item.get("backlog_id")))
    return state


def _domain(objective: Mapping[str, Any]) -> str:
    return str(objective.get("dependency_domain") or objective.get("domain") or "INDEPENDENT")


def _machine_backlog(state: Mapping[str, Any]) -> List[Dict[str, Any]]:
    items = [item for item in state.get("backlog_items") or [] if isinstance(item, dict)]
    return [item for item in items if item.get("machine_executable") and item.get("status") not in {"PASS", "BLOCKED_EXTERNAL", "DEFERRED_BY_RAY"}]


def _capability(objective: Mapping[str, Any]) -> str:
    return str(objective.get("capability_id") or "system.health")


def _failure_result(objective: Mapping[str, Any]) -> Dict[str, Any]:
    """A real, harmless executor result after dispatch and receiver ACK."""
    return {"status": "FAIL", "failure_stage": "S4_EXECUTOR_STARTED", "failure_signature": str(objective.get("failure_signature") or "CERTIFICATION_BOUNDED_FAILURE"), "error": "bounded certification failure", "test_only": True}


def _capability_gap_mission(objective: Mapping[str, Any]) -> Dict[str, Any]:
    """Create the real PE handoff for a missing capability.

    Importing lazily keeps the campaign engine below the existing PE consumer
    boundary and ensures Phase15 remains the sole mission owner.
    """
    from nexus_product_evolution.loop import MissionContract
    from nexus_product_evolution.telegram_control import register_mission
    backlog_id = str(objective.get("backlog_id") or objective["objective_id"])
    capability = str(objective.get("missing_capability") or objective.get("capability_id") or "unknown")
    contract = MissionContract(
        goal=f"Recover missing Nexus capability: {capability}",
        user_visible_outcome=f"Register and certify {capability} for campaign backlog {backlog_id}.",
        acceptance_criteria=["discover reusable implementation", "register minimum governed capability", "run bounded canary", "return reconciliation receipt"],
        capability_candidates=[capability, "product.evolution"],
        allowed_files=["scripts/", "configs/", "reports/runtime/"],
        security_boundaries=["no arbitrary shell", "certification-only changes", "no production mutation"],
        human_only_gates=[], max_cycles=3,
    )
    return register_mission(contract, mission_id=f"campaign-capability-gap-{backlog_id.lower()}")


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
    verifier_result = None
    if objective.get("verification_only"):
        backlog = {"backlog_id": objective.get("backlog_id")}
        criterion = objective.get("criterion") or {"criterion_id": f"{objective.get('backlog_id')}.acceptance", "verifier": objective.get("verifier")}
        resolved = resolve_verifier(str(objective.get("backlog_id")), criterion)
        if resolved is None:
            raw = {"status": "FAIL", "failure_stage": "S6_VERIFICATION", "failure_signature": f"VERIFIER_CAPABILITY_GAP:{objective.get('backlog_id')}", "error": "no registered specialized acceptance verifier", "test_only": True}
        else:
            verifier_id, verifier = resolved
            context = {"objective": objective, "backlog": backlog, "criterion": criterion, "result_ref": objective.get("result_ref"), "condition_watch_evidence": objective.get("condition_watch_evidence")}
            verifier_result = verifier(context).as_dict()
            raw = {"status": verifier_result["status"], "verification": verifier_result, "receipt_id": verifier_result["verification_receipt_id"], "test_only": True}
        terminal = "completed" if raw.get("status") == "PASS" else "failed"
    elif objective.get("capability_gap"):
        raw = _capability_gap_mission(objective)
        raw.update({"status": "PASS", "receipt_id": raw.get("mission_id"), "test_only": True, "handoff": "PRODUCT_EVOLUTION"})
        terminal = "completed"
    elif objective.get("force_failure"):
        raw = _failure_result(objective)
        terminal = "failed"
    else:
        if objective.get("backlog_id") == "REAL_CONDITION_WATCH_END_TO_END":
            from nexus_agent_platform.condition_watch import certify_real_synthetic_watch
            raw = certify_real_synthetic_watch(send_notification=True)
            raw["receipt_id"] = f"condition-watch-{uuid.uuid4().hex[:12]}"
            receipt_dir.mkdir(parents=True, exist_ok=True)
            atomic_write_json(receipt_dir / f"{raw['receipt_id']}.json", raw)
        else:
            raw = run_capability(capability, dict(objective.get("args") or {}), receipt_dir=receipt_dir)
        terminal = "completed" if raw.get("status") == "PASS" else "failed"
    result = work_orders.record_result(work_order_id, status=terminal, result=raw, error=None if terminal == "completed" else str(raw.get("error") or raw.get("status")), telemetry_run_id=dispatch_id)
    result_ref = str(receipt_dir / f"{raw.get('receipt_id')}.json") if raw.get("receipt_id") else None
    if verifier_result:
        receipt_dir.mkdir(parents=True, exist_ok=True)
        verification_path = receipt_dir / f"{verifier_result['verification_receipt_id']}.json"
        atomic_write_json(verification_path, verifier_result)
        result_ref = str(verification_path)
    receipt_verified = terminal == "completed" and bool(result_ref and Path(result_ref).exists() and raw.get("status") == "PASS")
    verified = bool(verifier_result and verifier_result.get("status") == "PASS") or (receipt_verified and not objective.get("backlog_id"))
    if terminal == "failed":
        failure = {"status": "FAIL", "objective_id": objective_id, "stage": raw.get("failure_stage", "S4_EXECUTOR_STARTED"), "reason": raw.get("error", "bounded failure"), "failure_signature": raw.get("failure_signature"), "machine_solvable": True, "solution_known": raw.get("failure_signature", "").startswith("VERIFIER_CAPABILITY_GAP") is False, "repair_count": int(objective.get("repair_count", 0))}
    else:
        failure = None
    pending_gap = bool(objective.get("capability_gap"))
    return {"objective_id": objective_id, "backlog_id": objective.get("backlog_id"), "work_order_id": work_order_id, "dispatch_id": dispatch_id, "receiver_ack": "PASS", "execution": raw, "verification": "PASS" if verified else "PASS_RECEIPT_ACCEPTANCE_PENDING" if terminal == "completed" and objective.get("backlog_id") and not pending_gap else "FAIL", "state": "COMPLETED" if verified else "RECOVERING" if pending_gap or failure else "VERIFYING" if terminal == "completed" and objective.get("backlog_id") else "FAIL", "failure_event": failure, "domain": _domain(objective)}


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


def run_campaign_cycle(*, scheduler_instance: str, objectives: Optional[Sequence[Mapping[str, Any]]] = None, state_path: Path = CAMPAIGN_PATH, ledger_path: Path = LEDGER_PATH, receipt_dir: Optional[Path] = None, max_workers: int = 3, include_certification: bool = False) -> Dict[str, Any]:
    """Run one canonical scheduled campaign cycle and consume its decisions."""
    state = load_campaign(state_path, materialize_queue=objectives is None)
    cycle_no = int(state.get("cycle_number", 0)) + 1
    cycle_id = f"{scheduler_instance}:{cycle_no}"
    if objectives is not None:
        if objectives and all(item.get("backlog_id") for item in objectives):
            state["synthetic_campaign"] = True
            requested_backlog_ids = {str(item["backlog_id"]) for item in objectives}
            state["backlog_items"] = [item for item in state.get("backlog_items", []) if str(item.get("backlog_id")) in requested_backlog_ids]
        existing = {str(item.get("objective_id")): dict(item) for item in state.get("objective_queue") or [] if isinstance(item, dict)}
        existing.update({str(item.get("objective_id")): dict(item) for item in objectives})
        state["objective_queue"] = list(existing.values())
        backlog = {str(item.get("backlog_id")): item for item in state.get("backlog_items", []) if item.get("backlog_id")}
        for objective in objectives:
            backlog_id = objective.get("backlog_id")
            if not backlog_id or str(backlog_id) in backlog:
                continue
            backlog[str(backlog_id)] = {"backlog_id": str(backlog_id), "title": str(objective.get("title") or backlog_id), "acceptance_criteria": [{"criterion_id": f"{backlog_id}.acceptance", "description": str(objective.get("expected_outcome") or "verified result"), "required_evidence_types": ["capability_receipt", "verification_receipt"], "status": "PENDING", "proof_refs": [], "verifier": "nexus_acceptance_verifier", "last_verified_at": None, "failure_reason": None}], "capability_requirements": [str(objective.get("capability_id") or "")], "dependency_domain": _domain(objective), "authority_class": "CLASS_1", "machine_executable": True, "capability_available": not bool(objective.get("capability_gap")), "capability_gap": bool(objective.get("capability_gap")), "human_gate_required": False, "status": "READY", "diagnosis_state": "MATERIALIZED", "objective_ids": [str(objective.get("objective_id"))], "proof_refs": [], "failure_signature": None, "repair_count": 0, "backlog_version": 1, "created_at": utc_now(), "updated_at": utc_now()}
        state["backlog_items"] = list(backlog.values())
    queue = [dict(item) for item in state.get("objective_queue") or [] if isinstance(item, dict)]
    # Only executable, dependency-free objectives are dispatched this cycle.
    runnable = [item for item in queue if not item.get("dependency_ids") and item.get("status", "READY") not in {"COMPLETED", "WAITING_HUMAN", "BLOCKED_EXTERNAL"}]
    deferred_certification = []
    if not include_certification:
        deferred_certification = [item for item in runnable if str(item.get("backlog_id")) in CERTIFICATION_ONLY_BACKLOGS]
        runnable = [item for item in runnable if str(item.get("backlog_id")) not in CERTIFICATION_ONLY_BACKLOGS]
    state["cycle_number"] = cycle_no
    state["scheduler_instance"] = scheduler_instance
    state["campaign_health"] = "RUNNING" if runnable else "STALLED" if queue else "WAITING_HUMAN"
    _save_state(state, state_path)
    receipt_dir = receipt_dir or (ROOT / "reports/runtime/campaign_execution" / str(cycle_no))
    results: List[Dict[str, Any]] = []
    # Certification campaigns deliberately serialize their tiny fixture set;
    # production backlog uses bounded portfolio concurrency. This keeps the
    # legacy test fixture from launching several report-generating subprocesses
    # against the same runtime store.
    worker_limit = 1 if state.get("synthetic_campaign") else max_workers
    with ThreadPoolExecutor(max_workers=worker_limit) as pool:
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
                item["status"] = "PASS" if row["verification"] == "PASS" else "RECOVERING" if row.get("execution", {}).get("status") != "PASS" or str(row.get("objective_id", "")).startswith("capability-gap.") else "VERIFYING"
                criterion = (item.get("acceptance_criteria") or [{}])[0]
                criterion["status"] = "PASS" if row["verification"] == "PASS" else "EVIDENCE_PRESENT" if row.get("execution", {}).get("status") == "PASS" else "FAIL"
                if row["verification"] == "PASS":
                    criterion["last_verified_at"] = utc_now()
                item["proof_refs"] = list(dict.fromkeys([*item.get("proof_refs", []), *([row["result_ref"]] if row.get("result_ref") else [])]))
                criterion["proof_refs"] = list(dict.fromkeys([*criterion.get("proof_refs", []), *([row["result_ref"]] if row.get("result_ref") else [])]))
                item["updated_at"] = utc_now()
                if str((row.get("failure_event") or {}).get("failure_signature") or "").startswith("VERIFIER_CAPABILITY_GAP"):
                    gap = {"objective_id": f"capability-gap.verifier.{item['backlog_id']}.v1", "backlog_id": item["backlog_id"], "capability_id": "product.evolution.bridge", "missing_capability": str(criterion.get("verifier")), "capability_gap": True, "dependency_domain": item.get("dependency_domain", "INDEPENDENT"), "expected_outcome": "Product Evolution verifier capability handoff", "test_only": True}
                    if not any(x.get("objective_id") == gap["objective_id"] for x in state["objective_queue"]):
                        state["objective_queue"].append(gap)
    state["completed_objectives"] = completed
    state["active_work_orders"] = [row["work_order_id"] for row in results if row["state"] == "RECOVERING"]
    state["recovering_objectives"] = [row["objective_id"] for row in results if row["state"] == "RECOVERING"]
    state["failure_dispositions"].update({row["objective_id"]: "queued repair" for row in results if row.get("failure_event")})
    finished_or_recovering = set(completed) | {row["objective_id"] for row in results if row["state"] in {"RECOVERING", "VERIFYING"}}
    state["objective_queue"] = [item for item in state.get("objective_queue", []) if str(item.get("objective_id")) not in finished_or_recovering]
    # VERIFYING is executable work: enqueue its verifier before this cycle is
    # persisted, so no observer can see an orphan verification state.
    for row in results:
        if row["state"] != "VERIFYING" or not row.get("backlog_id"):
            continue
        verifier_id = f"backlog.{row['backlog_id']}.verify.v1"
        if not any(str(item.get("objective_id")) == verifier_id for item in state["objective_queue"]):
            item = next((candidate for candidate in state.get("backlog_items", []) if candidate.get("backlog_id") == row["backlog_id"]), {})
            criterion = (item.get("acceptance_criteria") or [{}])[0]
            state["objective_queue"].append({"objective_id": verifier_id, "backlog_id": row["backlog_id"], "capability_id": "acceptance.verifier", "dependency_domain": row["domain"], "expected_outcome": "independent acceptance verification", "criterion": criterion, "result_ref": (criterion.get("proof_refs") or [None])[-1], "verification_only": True})
    state["campaign_health"] = "RECOVERING" if state["recovering_objectives"] else "RUNNING" if state["objective_queue"] else "STALLED" if _machine_backlog(state) else "PASS"
    _save_state(state, state_path)
    cycle = {"schema_version": "nexus.campaign-execution-receipt.v1", "campaign_id": state["campaign_id"], "scheduler_instance": scheduler_instance, "cycle_id": cycle_id, "cycle_number": cycle_no, "objectives": results, "deferred_certification": [{"objective_id": item.get("objective_id"), "backlog_id": item.get("backlog_id"), "reason": "CERTIFICATION_ISOLATED_FROM_COMPANY_DISPATCH"} for item in deferred_certification], "completion_law_decisions": decisions.get("decisions", []), "generated_work": generated, "active_executor_count": len([r for r in results if r["state"] == "RECOVERING"]), "queued_dispatch_count": len(generated), "campaign_health": state["campaign_health"], "next_runnable_objective": (state["objective_queue"] or [{}])[0].get("objective_id") if state["objective_queue"] else None, "created_at": utc_now()}
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
