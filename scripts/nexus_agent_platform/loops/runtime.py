"""Token-efficient Nexus loop runtime.

The loop runtime is intentionally bounded and on-demand. A loop run starts with
deterministic reads, compares against cached structured state, deduplicates the
delta, and only then decides whether an AI call is materially necessary.

No loop is a background daemon and no loop is an always-on model.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from nexus_agent_platform.capabilities.shared import execute_shared_capability
from nexus_agent_platform.opportunities.engine import (
    build_opportunity_discovery_packet,
    merge_ai_result as merge_opportunity_ai_result,
)
from nexus_agent_platform.runtime.execution_telemetry import execution_run
from nexus_agent_platform.runtime.paths import nexus_data_path

TIER_ORDER = {
    "T0_DETERMINISTIC": 0,
    "T1_CHEAP_AI": 1,
    "T2_STANDARD_AI": 2,
    "T3_PREMIUM_AI": 3,
}

DEFAULT_LOOP_HISTORY = 20
DEFAULT_TOKEN_TO_COST = {
    "T0_DETERMINISTIC": 0.0,
    "T1_CHEAP_AI": 0.0005,
    "T2_STANDARD_AI": 0.0025,
    "T3_PREMIUM_AI": 0.01,
}


class LoopExecutionError(RuntimeError):
    """Raised when a loop cannot be executed within policy."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)


def _atomic_write_json(path: Path, data: Dict[str, Any]) -> None:
    _ensure_parent(path)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True, default=str)
            fh.write("\n")
        os.chmod(tmp_name, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(tmp_name, path)
    finally:
        try:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
        except OSError:
            pass


def _append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    _ensure_parent(path)
    if not path.exists():
        path.touch(mode=0o600)
        os.chmod(path, 0o600)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True, separators=(",", ":"), default=str))
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())


def _truncate_text(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit]


def _approx_tokens(value: Any) -> int:
    text = value if isinstance(value, str) else json.dumps(value, sort_keys=True, default=str)
    return max(0, len(text) // 4)


def _stable_hash(payload: Any) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize_records(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized = []
    for record in records:
        if isinstance(record, dict):
            normalized.append(json.loads(json.dumps(record, sort_keys=True, default=str)))
    normalized.sort(key=lambda item: json.dumps(item, sort_keys=True, default=str))
    return normalized


def _dedupe_records(records: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    deduped = []
    for record in records:
        key = _stable_hash(record)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)
    return deduped


def _cost_for_tier(tier: str, input_tokens: int, output_tokens: int) -> float:
    rate = DEFAULT_TOKEN_TO_COST.get(tier, DEFAULT_TOKEN_TO_COST["T1_CHEAP_AI"])
    return round((input_tokens + output_tokens) * rate, 6)


def _bounded_history(history: List[Dict[str, Any]], limit: int = DEFAULT_LOOP_HISTORY) -> List[Dict[str, Any]]:
    if len(history) <= limit:
        return history
    return history[-limit:]


@dataclass(frozen=True)
class LoopSpec:
    loop_id: str
    name: str
    owner: str
    trigger: str
    goal: str
    inputs: Sequence[str]
    deterministic_precheck: Callable[[Dict[str, Any], Optional[Dict[str, Any]]], Dict[str, Any]]
    delta_only: bool
    cache_enabled: bool
    dedupe_enabled: bool
    deterministic_steps: Sequence[str]
    ai_steps: Sequence[str]
    model_tier: str
    max_ai_calls: int
    max_input_tokens: int
    max_output_tokens: int
    estimated_token_budget: int
    cost_ceiling: float
    verifier: Callable[[Dict[str, Any], Dict[str, Any], Optional[Dict[str, Any]]], Dict[str, Any]]
    retry_policy: str
    max_retries: int
    stop_if_no_change: bool
    stop_conditions: Sequence[str]
    approval_boundary: str
    output: str
    memory_write_mode: str
    metrics: Sequence[str]
    ai_decider: Callable[[Dict[str, Any], Dict[str, Any], Optional[Dict[str, Any]]], Dict[str, Any]]
    ai_context_builder: Callable[[Dict[str, Any], Dict[str, Any], Optional[Dict[str, Any]]], Dict[str, Any]]
    memory_projection: Callable[[Dict[str, Any], Dict[str, Any], Optional[Dict[str, Any]]], Dict[str, Any]]


@dataclass
class LoopRunResult:
    loop_id: str
    run_id: str
    status: str
    zero_token_execution: bool
    ai_used: bool
    ai_calls: int
    tier1_calls: int
    tier2_calls: int
    tier3_calls: int
    input_tokens: int
    output_tokens: int
    estimated_cost: float
    successful_outputs: int
    value_events: int
    deterministic_execution_share: float
    ai_execution_share: float
    tokens_per_success: float
    cost_per_success: float
    deterministic_precheck: Dict[str, Any]
    reduced: Dict[str, Any]
    result: Dict[str, Any]
    verifier: Dict[str, Any]
    memory_record: Dict[str, Any]
    ledger_record: Dict[str, Any]
    telemetry_run_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "loop_id": self.loop_id,
            "run_id": self.run_id,
            "status": self.status,
            "zero_token_execution": self.zero_token_execution,
            "ai_used": self.ai_used,
            "ai_calls": self.ai_calls,
            "tier1_calls": self.tier1_calls,
            "tier2_calls": self.tier2_calls,
            "tier3_calls": self.tier3_calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "estimated_cost": self.estimated_cost,
            "successful_outputs": self.successful_outputs,
            "value_events": self.value_events,
            "deterministic_execution_share": self.deterministic_execution_share,
            "ai_execution_share": self.ai_execution_share,
            "tokens_per_success": self.tokens_per_success,
            "cost_per_success": self.cost_per_success,
            "deterministic_precheck": self.deterministic_precheck,
            "reduced": self.reduced,
            "result": self.result,
            "verifier": self.verifier,
            "memory_record": self.memory_record,
            "ledger_record": self.ledger_record,
            "telemetry_run_id": self.telemetry_run_id,
        }


class LoopStateStore:
    """Structured bounded loop state with atomic writes."""

    def __init__(self, path: Optional[Path] = None, history_limit: int = DEFAULT_LOOP_HISTORY):
        self.path = path or nexus_data_path("runtime", "nexus_loops", "loop_state.json")
        self.history_limit = history_limit

    def load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {"loops": {}}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"loops": {}}

    def save(self, state: Dict[str, Any]) -> None:
        _atomic_write_json(self.path, state)

    def get_loop_state(self, loop_id: str) -> Dict[str, Any]:
        return self.load().get("loops", {}).get(loop_id, {})

    def update_loop_state(self, loop_id: str, record: Dict[str, Any]) -> Dict[str, Any]:
        state = self.load()
        loops = state.setdefault("loops", {})
        loop_state = loops.get(loop_id, {"history": []})
        loop_state["history"] = _bounded_history(loop_state.get("history", []), self.history_limit)
        loop_state["history"].append(record)
        loop_state["history"] = _bounded_history(loop_state["history"], self.history_limit)
        loop_state["last_run"] = record
        loop_state["last_input_hash"] = record.get("input_hash")
        loop_state["last_output_hash"] = record.get("output_hash")
        loop_state["last_material_hash"] = record.get("material_hash")
        loop_state["last_updated_at"] = record.get("completed_at")
        loops[loop_id] = loop_state
        self.save(state)
        return loop_state


@dataclass
class LoopRuntime:
    state_store: LoopStateStore = field(default_factory=LoopStateStore)
    ledger_path: Path = field(default_factory=lambda: nexus_data_path("runtime", "nexus_loops", "execution_ledger.jsonl"))

    def run(
        self,
        spec: LoopSpec,
        trigger: Optional[Dict[str, Any]] = None,
        *,
        capability_call: Optional[Callable[[str, Dict[str, Any], str], Dict[str, Any]]] = None,
        ai_call: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        previous_state: Optional[Dict[str, Any]] = None,
        explicit_premium_escalation: bool = False,
    ) -> LoopRunResult:
        trigger = trigger or {}
        previous_state = previous_state or self.state_store.get_loop_state(spec.loop_id)
        if not spec.delta_only:
            raise LoopExecutionError("loops must operate on deltas only")
        if not spec.cache_enabled:
            previous_state = {}
        run_id = f"{spec.loop_id}_{uuid.uuid4().hex}"
        started_at = _utc_now()
        start = time.monotonic()

        collected = spec.deterministic_precheck(trigger, previous_state)
        normalized = _normalize_records(collected.get("records", []))
        if spec.dedupe_enabled:
            normalized = _dedupe_records(normalized)

        current_material = {
            "trigger": trigger,
            "records": normalized,
            "summary": collected.get("summary", {}),
            "state_version": collected.get("state_version", 1),
        }
        input_hash = _stable_hash(current_material)
        material_hash = _stable_hash(collected.get("material", current_material))
        previous_input_hash = previous_state.get("last_input_hash")

        zero_token_execution = False
        ai_used = False
        ai_calls = 0
        tier1_calls = 0
        tier2_calls = 0
        tier3_calls = 0
        input_tokens = 0
        output_tokens = 0
        ai_result: Dict[str, Any] = {}
        verifier_result: Dict[str, Any] = {"status": "not_run"}

        if spec.stop_if_no_change and previous_input_hash == input_hash:
            zero_token_execution = True
            deterministic_output = collected.get("deterministic_output", {})
            reduced = collected.get("reduced", deterministic_output)
            result = deterministic_output or reduced
            verifier_result = spec.verifier(result, collected, previous_state)
        else:
            reduced = collected.get("reduced", {})
            if not reduced:
                reduced = spec.ai_context_builder(collected, previous_state, trigger)

            ai_decision = spec.ai_decider(collected, reduced, previous_state)
            ai_needed = bool(ai_decision.get("use_ai"))
            effective_tier = ai_decision.get("requested_tier", spec.model_tier)
            reason = ai_decision.get("reason", "")

            if ai_needed and ai_call is not None:
                tier = effective_tier or spec.model_tier
                if TIER_ORDER.get(tier, 0) > TIER_ORDER.get(spec.model_tier, 0):
                    if tier == "T3_PREMIUM_AI" and not explicit_premium_escalation:
                        raise LoopExecutionError("premium escalation requires explicit rule")
                    if TIER_ORDER.get(tier, 0) > TIER_ORDER.get(spec.model_tier, 0) + 1 and not explicit_premium_escalation:
                        raise LoopExecutionError("requested tier exceeds loop policy")
                input_context = spec.ai_context_builder(collected, reduced, previous_state)
                input_tokens = _approx_tokens(input_context)
                if input_tokens > spec.max_input_tokens:
                    raise LoopExecutionError("input token budget exceeded")
                if ai_calls >= spec.max_ai_calls:
                    raise LoopExecutionError("max_ai_calls exceeded")
                ai_calls += 1
                if tier == "T1_CHEAP_AI":
                    tier1_calls += 1
                elif tier == "T2_STANDARD_AI":
                    tier2_calls += 1
                elif tier == "T3_PREMIUM_AI":
                    tier3_calls += 1
                ai_result = ai_call({
                    "loop_id": spec.loop_id,
                    "name": spec.name,
                    "tier": tier,
                    "reason": reason,
                    "input_context": input_context,
                    "previous_state": previous_state,
                    "material_hash": material_hash,
                    "input_hash": input_hash,
                }) or {}
                ai_used = True
                output_text = json.dumps(ai_result, sort_keys=True, default=str)
                output_tokens = _approx_tokens(output_text)
                if output_tokens > spec.max_output_tokens:
                    raise LoopExecutionError("output token budget exceeded")
                if input_tokens + output_tokens > spec.estimated_token_budget:
                    raise LoopExecutionError("estimated token budget exceeded")
                estimated_cost = _cost_for_tier(tier, input_tokens, output_tokens)
                if estimated_cost > spec.cost_ceiling:
                    raise LoopExecutionError("cost ceiling exceeded")
                if spec.loop_id == "opportunity_discovery_loop":
                    result = merge_opportunity_ai_result(reduced, ai_result)
                else:
                    result = dict(reduced)
                    result.update(ai_result)
                verifier_result = spec.verifier(result, collected, previous_state)
            else:
                result = collected.get("deterministic_output", reduced or collected)
                verifier_result = spec.verifier(result, collected, previous_state)

            if ai_used and verifier_result.get("status") != "pass" and ai_calls < spec.max_ai_calls:
                retries = 0
                while retries < spec.max_retries and verifier_result.get("status") != "pass":
                    retries += 1
                    ai_calls += 1
                    if ai_calls > spec.max_ai_calls:
                        raise LoopExecutionError("max_ai_calls exceeded during retry")
                    retry_context = spec.ai_context_builder(collected, reduced, previous_state)
                    retry_payload = ai_call({
                        "loop_id": spec.loop_id,
                        "name": spec.name,
                        "tier": effective_tier,
                        "retry": retries,
                        "input_context": retry_context,
                        "previous_state": previous_state,
                    }) or {}
                    ai_result = retry_payload
                    output_tokens = _approx_tokens(json.dumps(ai_result, sort_keys=True, default=str))
                    if output_tokens > spec.max_output_tokens:
                        raise LoopExecutionError("output token budget exceeded")
                    estimated_cost = _cost_for_tier(effective_tier, input_tokens, output_tokens)
                    if estimated_cost > spec.cost_ceiling:
                        raise LoopExecutionError("cost ceiling exceeded")
                    if spec.loop_id == "opportunity_discovery_loop":
                        result = merge_opportunity_ai_result(reduced, ai_result)
                    else:
                        result = dict(reduced)
                        result.update(ai_result)
                    verifier_result = spec.verifier(result, collected, previous_state)

            result = ai_result if ai_used else collected.get("deterministic_output", reduced or collected)
            if ai_used:
                if spec.loop_id == "opportunity_discovery_loop":
                    result = merge_opportunity_ai_result(reduced, ai_result)
                else:
                    result = dict(reduced)
                    result.update(ai_result)

        completed_at = _utc_now()
        duration_ms = round((time.monotonic() - start) * 1000)
        successful_outputs = 1 if verifier_result.get("status") == "pass" else 0
        value_events = successful_outputs
        estimated_cost = _cost_for_tier(effective_tier if ai_used else "T0_DETERMINISTIC", input_tokens, output_tokens)
        if ai_used and ai_calls == 0:
            ai_calls = 1
        deterministic_share = 1.0 if not ai_used else 0.0
        ai_share = 0.0 if not ai_used else 1.0
        tokens_per_success = round((input_tokens + output_tokens) / successful_outputs, 3) if successful_outputs else 0.0
        cost_per_success = round(estimated_cost / successful_outputs, 6) if successful_outputs else 0.0

        memory_record = spec.memory_projection(result, collected, previous_state)
        memory_record.update({
            "loop_id": spec.loop_id,
            "run_id": run_id,
            "input_hash": input_hash,
            "output_hash": _stable_hash(result),
            "material_hash": material_hash,
            "completed_at": completed_at,
            "ai_used": ai_used,
            "ai_calls": ai_calls,
            "zero_token_execution": zero_token_execution or not ai_used,
        })
        memory_record = json.loads(json.dumps(memory_record, sort_keys=True, default=str))
        self.state_store.update_loop_state(spec.loop_id, memory_record)

        ledger_record = {
            "record_id": f"ledger_{uuid.uuid4().hex}",
            "loop_id": spec.loop_id,
            "loop_name": spec.name,
            "run_id": run_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "duration_ms": duration_ms,
            "deterministic_precheck": collected.get("deterministic_precheck", True),
            "delta_only": spec.delta_only,
            "cache_enabled": spec.cache_enabled,
            "dedupe_enabled": spec.dedupe_enabled,
            "zero_token_execution": zero_token_execution or not ai_used,
            "deterministic_execution_share": deterministic_share,
            "ai_execution_share": ai_share,
            "ai_used": ai_used,
            "ai_calls": ai_calls,
            "tier1_calls": tier1_calls,
            "tier2_calls": tier2_calls,
            "tier3_calls": tier3_calls,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost": estimated_cost,
            "successful_outputs": successful_outputs,
            "value_events": value_events,
            "tokens_per_success": tokens_per_success,
            "cost_per_success": cost_per_success,
            "model_tier": spec.model_tier,
            "effective_tier": effective_tier if ai_used else "T0_DETERMINISTIC",
            "explicit_premium_escalation": explicit_premium_escalation,
            "verifier_status": verifier_result.get("status"),
            "verifier_reason": verifier_result.get("reason"),
            "result_status": result.get("status") if isinstance(result, dict) else type(result).__name__,
            "input_hash": input_hash,
            "output_hash": _stable_hash(result),
            "material_hash": material_hash,
        }
        _append_jsonl(self.ledger_path, ledger_record)

        telemetry_run_id = ""
        with execution_run(
            process_id=spec.loop_id,
            process_name=spec.name,
            worker_id="nexus_loop_runtime",
            agent_id="nexus_hermes",
            execution_type=f"loop:{spec.loop_id}",
            source="scripts/nexus_agent_platform/loops/runtime.py",
            metadata={
                "loop_id": spec.loop_id,
                "model_tier": spec.model_tier,
                "ai_used": ai_used,
                "zero_token_execution": zero_token_execution or not ai_used,
            },
        ) as telemetry_run_id:
            pass

        return LoopRunResult(
            loop_id=spec.loop_id,
            run_id=run_id,
            status="completed" if verifier_result.get("status") == "pass" else "partial",
            zero_token_execution=zero_token_execution or not ai_used,
            ai_used=ai_used,
            ai_calls=ai_calls,
            tier1_calls=tier1_calls,
            tier2_calls=tier2_calls,
            tier3_calls=tier3_calls,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=estimated_cost,
            successful_outputs=successful_outputs,
            value_events=value_events,
            deterministic_execution_share=deterministic_share,
            ai_execution_share=ai_share,
            tokens_per_success=tokens_per_success,
            cost_per_success=cost_per_success,
            deterministic_precheck=collected,
            reduced=reduced,
            result=result if isinstance(result, dict) else {"value": result},
            verifier=verifier_result,
            memory_record=memory_record,
            ledger_record=ledger_record,
            telemetry_run_id=telemetry_run_id,
        )


def _system_health_collect(trigger: Dict[str, Any], previous_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    system = execute_shared_capability("hermes_nova", "get_system_health", {}, trace_id="loop_system_health")
    process = execute_shared_capability("hermes_nova", "get_process_registry", {}, trace_id="loop_system_health")
    runtime = execute_shared_capability("hermes_nova", "get_runtime_execution_summary", {"window": trigger.get("window", "last_24_hours")}, trace_id="loop_system_health")
    approvals = execute_shared_capability("hermes_nova", "get_pending_approvals", {}, trace_id="loop_system_health")
    return {
        "deterministic_precheck": True,
        "state_version": 1,
        "trigger": trigger,
        "records": [system, process, runtime, approvals],
        "summary": {
            "system_status": system.get("data", {}).get("overall_status"),
            "process_total": process.get("data", {}).get("total") or process.get("data", {}).get("total_count"),
            "active_runs": runtime.get("summary", {}).get("active_count"),
            "failed_runs": runtime.get("summary", {}).get("failed_count"),
            "pending_approvals": approvals.get("data", {}).get("count"),
        },
        "material": {
            "system": system,
            "process": process,
            "runtime": runtime,
            "approvals": approvals,
        },
        "deterministic_output": {
            "status": "success",
            "loop": "system_health_loop",
            "summary": {
                "system_status": system.get("data", {}).get("overall_status"),
                "process_total": process.get("data", {}).get("total") or process.get("data", {}).get("total_count"),
                "active_runs": runtime.get("summary", {}).get("active_count"),
                "failed_runs": runtime.get("summary", {}).get("failed_count"),
                "pending_approvals": approvals.get("data", {}).get("count"),
            },
            "records": [
                {
                    "capability": "get_system_health",
                    "status": system.get("status"),
                },
                {
                    "capability": "get_process_registry",
                    "status": process.get("status"),
                },
                {
                    "capability": "get_runtime_execution_summary",
                    "status": runtime.get("status"),
                },
                {
                    "capability": "get_pending_approvals",
                    "status": approvals.get("status"),
                },
            ],
            "source_types": [
                system.get("source_type"),
                process.get("source_type"),
                runtime.get("source_type"),
                approvals.get("source_type"),
            ],
        },
    }


def _system_health_reduce(collected: Dict[str, Any], previous_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return collected.get("deterministic_output", {})


def _system_health_ai_decider(collected: Dict[str, Any], reduced: Dict[str, Any], previous_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "use_ai": False,
        "requested_tier": "T0_DETERMINISTIC",
        "reason": "system health loop is deterministic-first and does not require AI",
    }


def _system_health_ai_context(collected: Dict[str, Any], reduced: Dict[str, Any], previous_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "loop_id": "system_health_loop",
        "summary": reduced.get("summary", {}),
        "material": {
            "system_status": reduced.get("summary", {}).get("system_status"),
            "failed_runs": reduced.get("summary", {}).get("failed_runs"),
        },
        "previous_state": {
            "last_input_hash": previous_state.get("last_input_hash") if previous_state else None,
            "last_output_hash": previous_state.get("last_output_hash") if previous_state else None,
        },
    }


def _system_health_memory_projection(result: Dict[str, Any], collected: Dict[str, Any], previous_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "status": result.get("status", "success"),
        "summary": result.get("summary", {}),
        "deterministic_only": True,
        "loop_type": "system_health",
        "source_caps": ["get_system_health", "get_process_registry", "get_runtime_execution_summary", "get_pending_approvals"],
    }


def _system_health_verifier(result: Dict[str, Any], collected: Dict[str, Any], previous_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    summary = result.get("summary", {}) if isinstance(result, dict) else {}
    if summary.get("system_status") is None:
        return {"status": "fail", "reason": "missing system status"}
    return {"status": "pass", "reason": "deterministic system health summary produced"}


def _opportunity_collect(trigger: Dict[str, Any], previous_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    opportunities = execute_shared_capability("hermes_nova", "get_opportunities", {}, trace_id="loop_opportunity")
    research = execute_shared_capability("hermes_nova", "get_recent_research", {"limit": trigger.get("research_limit", 5)}, trace_id="loop_opportunity")
    business = execute_shared_capability("hermes_nova", "get_business_model_summary", {}, trace_id="loop_opportunity")
    collected = build_opportunity_discovery_packet(
        opportunities_payload=opportunities,
        research_payload=research,
        business_payload=business,
        previous_state=previous_state,
        trigger=trigger,
    )
    packet_snapshot = json.loads(json.dumps(collected, sort_keys=True, default=str))
    collected.update({
        "deterministic_precheck": True,
        "state_version": 1,
        "trigger": trigger,
        "records": [
            {
                "source": "opportunities",
                "items": opportunities.get("data", {}).get("items", []),
                "total": opportunities.get("data", {}).get("total", 0),
            },
            {
                "source": "recent_research",
                "items": research.get("data", {}).get("results", {}).get("items", []),
                "runs": research.get("data", {}).get("runs", {}),
            },
            {
                "source": "business_model",
                "offers": business.get("offers", []),
                "offers_count": business.get("offers_count", 0),
            },
        ],
        "material": {
            "opportunities": opportunities,
            "research": research,
            "business": business,
        },
        "summary": {
            "opportunity_total": collected.get("summary", {}).get("opportunity_total", 0),
            "research_run_total": collected.get("summary", {}).get("research_run_total", 0),
            "offer_total": collected.get("summary", {}).get("offer_total", 0),
        },
        "reduced": packet_snapshot,
        "deterministic_output": packet_snapshot,
    })
    return collected


def _score_opportunities(items: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    scored = []
    for item in items:
        title = item.get("title") or item.get("name") or "Opportunity"
        status = (item.get("status") or "").lower()
        revenue = item.get("revenue_potential")
        action_state = (item.get("action_state") or "").lower()
        base = 10
        if status in {"new", "open", "discovered"}:
            base += 20
        if action_state in {"ready", "queued", "approved"}:
            base += 15
        if isinstance(revenue, (int, float)):
            if revenue >= 5000:
                base += 20
            elif revenue >= 1000:
                base += 10
        scored.append({
            "id": item.get("id"),
            "title": title,
            "status": status or "unknown",
            "revenue_potential": revenue,
            "action_state": action_state or "unknown",
            "score": min(base, 100),
            "updated_at": item.get("updated_at"),
        })
    scored.sort(key=lambda item: (item["score"], item.get("updated_at") or ""), reverse=True)
    return scored


def _opportunity_ai_decider(collected: Dict[str, Any], reduced: Dict[str, Any], previous_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    materiality = reduced.get("materiality", {})
    top_score = materiality.get("top_score", 0)
    new_candidates = materiality.get("new_candidates", 0)
    use_ai = bool(new_candidates and top_score >= 55)
    return {
        "use_ai": use_ai,
        "requested_tier": reduced.get("recommended_ai_tier", "T1_CHEAP_AI") if use_ai else "T0_DETERMINISTIC",
        "reason": "promising new opportunities detected" if use_ai else "no materially new opportunity evidence",
    }


def _opportunity_ai_context(collected: Dict[str, Any], reduced: Dict[str, Any], previous_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    context = reduced.get("ai_context", {})
    return {
        "loop_id": "opportunity_discovery_loop",
        "summary": context.get("summary", reduced.get("summary", {})),
        "top_candidates": context.get("top_candidates", [])[:3],
        "changed_candidates": context.get("changed_candidates", [])[:3],
        "previous_state": context.get("previous_state", {
            "last_input_hash": previous_state.get("last_input_hash") if previous_state else None,
            "last_output_hash": previous_state.get("last_output_hash") if previous_state else None,
            "last_result": previous_state.get("last_result", {}) if previous_state else {},
        }),
        "instructions": context.get("instructions", [
            "Use only the compact delta.",
            "Do not restate the full history.",
            "Return a short synthesis, not a long essay.",
        ]),
    }


def _opportunity_memory_projection(result: Dict[str, Any], collected: Dict[str, Any], previous_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "status": result.get("status", "success"),
        "summary": result.get("summary", {}),
        "canonical_opportunities": result.get("canonical_opportunities", [])[:5],
        "canonical_record": result.get("canonical_record", {}),
        "materiality": result.get("materiality", {}),
        "last_result": {
            "summary": result.get("summary", {}),
            "canonical_opportunities": result.get("canonical_opportunities", [])[:5],
            "canonical_record": result.get("canonical_record", {}),
            "materiality": result.get("materiality", {}),
        },
        "loop_type": "opportunity_discovery",
        "deterministic_only": not bool(result.get("ai_summary")),
    }


def _opportunity_verifier(result: Dict[str, Any], collected: Dict[str, Any], previous_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(result, dict):
        return {"status": "fail", "reason": "result must be structured"}
    if "canonical_opportunities" not in result or "canonical_record" not in result:
        return {"status": "fail", "reason": "canonical opportunity record missing"}
    if result.get("ai_summary"):
        ids = {item.get("id") for item in result.get("canonical_opportunities", []) if item.get("id")}
        if not ids:
            return {"status": "fail", "reason": "AI summary returned without candidate ids"}
        canonical = result.get("canonical_record", {})
        if canonical.get("base_score") is None:
            return {"status": "fail", "reason": "base score missing"}
    return {"status": "pass", "reason": "opportunity candidates verified"}


def build_loop_runtime() -> LoopRuntime:
    return LoopRuntime()


system_health_loop_spec = LoopSpec(
    loop_id="system_health_loop",
    name="System Health Loop",
    owner="Hermes",
    trigger="system or runtime health check requested",
    goal="Detect operational drift with deterministic reads and zero-token no-change exits.",
    inputs=("system health", "process registry", "runtime telemetry", "pending approvals"),
    deterministic_precheck=_system_health_collect,
    delta_only=True,
    cache_enabled=True,
    dedupe_enabled=True,
    deterministic_steps=(
        "read system health",
        "read process registry",
        "read runtime telemetry",
        "read pending approvals",
        "compare against cached state",
    ),
    ai_steps=(),
    model_tier="T0_DETERMINISTIC",
    max_ai_calls=0,
    max_input_tokens=0,
    max_output_tokens=0,
    estimated_token_budget=0,
    cost_ceiling=0.0,
    verifier=_system_health_verifier,
    retry_policy="none",
    max_retries=0,
    stop_if_no_change=True,
    stop_conditions=("no_change", "missing_deterministic_signal"),
    approval_boundary="read_only",
    output="bounded system health summary",
    memory_write_mode="bounded_structured",
    metrics=(
        "executions",
        "zero_token_executions",
        "ai_executions",
        "tier1_calls",
        "tier2_calls",
        "tier3_calls",
        "input_tokens",
        "output_tokens",
        "estimated_cost",
        "successful_outputs",
        "value_events",
        "tokens_per_success",
        "cost_per_success",
    ),
    ai_decider=_system_health_ai_decider,
    ai_context_builder=_system_health_ai_context,
    memory_projection=_system_health_memory_projection,
)


opportunity_discovery_loop_spec = LoopSpec(
    loop_id="opportunity_discovery_loop",
    name="Opportunity Discovery Loop",
    owner="Hermes",
    trigger="opportunity or research review requested",
    goal="Collect, dedupe, score, and selectively synthesize promising opportunities.",
    inputs=("opportunities", "research history", "business model summary"),
    deterministic_precheck=_opportunity_collect,
    delta_only=True,
    cache_enabled=True,
    dedupe_enabled=True,
    deterministic_steps=(
        "read opportunities",
        "read recent research",
        "read business model summary",
        "dedupe opportunities",
        "score opportunities deterministically",
        "compare against cached state",
    ),
    ai_steps=(
        "compact delta synthesis only when material new evidence exists",
    ),
    model_tier="T1_CHEAP_AI",
    max_ai_calls=1,
    max_input_tokens=2048,
    max_output_tokens=1024,
    estimated_token_budget=3072,
    cost_ceiling=1.5,
    verifier=_opportunity_verifier,
    retry_policy="bounded",
    max_retries=1,
    stop_if_no_change=True,
    stop_conditions=("no_change", "insufficient_materiality", "budget_exceeded"),
    approval_boundary="read_only",
    output="structured opportunity candidate",
    memory_write_mode="bounded_structured",
    metrics=(
        "executions",
        "zero_token_executions",
        "ai_executions",
        "tier1_calls",
        "tier2_calls",
        "tier3_calls",
        "input_tokens",
        "output_tokens",
        "estimated_cost",
        "successful_outputs",
        "value_events",
        "tokens_per_success",
        "cost_per_success",
    ),
    ai_decider=_opportunity_ai_decider,
    ai_context_builder=_opportunity_ai_context,
    memory_projection=_opportunity_memory_projection,
)


def _run_with_capabilities(
    spec: LoopSpec,
    trigger: Optional[Dict[str, Any]] = None,
    *,
    capability_call: Optional[Callable[[str, Dict[str, Any], str], Dict[str, Any]]] = None,
    ai_call: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    previous_state: Optional[Dict[str, Any]] = None,
    explicit_premium_escalation: bool = False,
) -> LoopRunResult:
    runtime = build_loop_runtime()
    return runtime.run(
        spec,
        trigger or {},
        capability_call=capability_call,
        ai_call=ai_call,
        previous_state=previous_state,
        explicit_premium_escalation=explicit_premium_escalation,
    )


def run_system_health_loop(
    trigger: Optional[Dict[str, Any]] = None,
    *,
    ai_call: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    previous_state: Optional[Dict[str, Any]] = None,
    explicit_premium_escalation: bool = False,
) -> LoopRunResult:
    return _run_with_capabilities(
        system_health_loop_spec,
        trigger,
        ai_call=ai_call,
        previous_state=previous_state,
        explicit_premium_escalation=explicit_premium_escalation,
    )


def run_opportunity_discovery_loop(
    trigger: Optional[Dict[str, Any]] = None,
    *,
    ai_call: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    previous_state: Optional[Dict[str, Any]] = None,
    explicit_premium_escalation: bool = False,
) -> LoopRunResult:
    return _run_with_capabilities(
        opportunity_discovery_loop_spec,
        trigger,
        ai_call=ai_call,
        previous_state=previous_state,
        explicit_premium_escalation=explicit_premium_escalation,
    )
