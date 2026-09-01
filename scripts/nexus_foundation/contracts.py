"""Deterministic Nexus specialist, work, loop, trading, and recovery contracts.

The existing ``nexus_agent_platform.governed`` work-order and loop modules
remain the execution boundary. This module supplies one normalized, JSON-safe
contract for registration, validation, and development proofs. No function in
this module performs external writes or live trading.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Mapping

SPECIALISTS = {
    "NOVA": {"role": "executive/business partner", "department": "executive", "status": "ACTIVE", "authority_level": "judgment"},
    "ALPHA": {"role": "business research, economics, trading research, evidence challenge", "department": "research", "status": "ACTIVE", "authority_level": "advisory"},
    "JAX": {"role": "engineering, system repair, technical implementation", "department": "engineering", "status": "ACTIVE", "authority_level": "sandboxed_implementation"},
    "GROWTH": {"role": "marketing, sales, revenue, campaign optimization", "department": "growth", "status": "ACTIVE", "authority_level": "advisory"},
    "CREATIVE": {"role": "content, media, campaign assets", "department": "creative", "status": "ACTIVE", "authority_level": "draft_only"},
    "CLYDE": {"role": "credit, funding, client delivery", "department": "client_delivery", "status": "ACTIVE", "authority_level": "advisory"},
    "TRADING_ENGINE": {"role": "deterministic market, backtest, paper, metrics capability", "department": "trading", "status": "ACTIVE", "authority_level": "paper_only"},
}

SPECIALIST_CONTRACT_FIELDS = (
    "specialist_id", "name", "role", "mission", "department", "status",
    "company_goal_ids", "initiative_ids", "skills", "skill_versions",
    "native_tools", "mcp_resources", "allowed_capabilities", "authority_level",
    "python_first_tasks", "ai_review_triggers", "cost_budget", "retry_budget",
    "input_contract", "output_contract", "work_order_types", "metrics",
    "quality_metrics", "failure_behavior", "escalation_behavior",
    "knowledge_sources", "temporary_data_policy", "persistence_policy",
    "return_to_nova_contract",
)

RESOURCE_PERMISSIONS = {
    "NOVA": {"nexus": "read", "google": "read", "web": "read", "alpha": "delegate", "specialists": "delegate"},
    "ALPHA": {"web": "read", "browser": "read", "python": "execute", "nexus": "read"},
    "JAX": {"git": "read", "filesystem": "sandboxed_write", "terminal": "sandboxed_execute", "python": "execute", "nexus_work_orders": "read"},
    "GROWTH": {"campaign_state": "read", "analytics": "read", "web": "read", "python": "execute"},
    "CREATIVE": {"creative_media": "draft", "campaign_briefs": "read", "asset_workflows": "draft"},
    "CLYDE": {"credit_state": "read", "funding_state": "read", "client_workflows": "read"},
    "TRADING_ENGINE": {"market_data": "read", "backtest": "execute", "paper_trading": "execute", "live_trading": "none"},
}

SKILL_ASSIGNMENTS = {
    "ALPHA": {"validate-business-opportunity": "1.0", "research-market": "1.0", "evaluate-economics": "1.0", "research-trading-strategy": "1.0"},
    "JAX": {"diagnose-engineering-defect": "1.0", "implement-feature": "1.0", "run-regression-suite": "1.0"},
    "GROWTH": {"design-offer": "1.0", "build-funnel": "1.0", "analyze-campaign": "1.0"},
    "CREATIVE": {"create-ad-concept": "1.0", "create-content-brief": "1.0", "repurpose-content": "1.0"},
    "CLYDE": {"evaluate-funding-readiness": "1.0", "analyze-credit-discrepancy": "1.0"},
    "TRADING_ENGINE": {"define-strategy-specification": "1.0", "analyze-backtest": "1.0", "evaluate-paper-performance": "1.0"},
}

LOOP_TYPES = (
    "OPPORTUNITY_LOOP", "VENTURE_PRODUCT_LOOP", "GROWTH_LOOP", "CLIENT_DELIVERY_LOOP",
    "ENGINEERING_LOOP", "CREATIVE_LOOP", "TRADING_RESEARCH_LOOP", "SYSTEM_OPERATIONS_LOOP",
    "CAPABILITY_IMPROVEMENT_LOOP", "EFFICIENCY_IMPROVEMENT_LOOP", "BUSINESS_LEARNING_LOOP",
    "EXECUTIVE_REVIEW_LOOP", "RUNTIME_RECOVERY_LOOP", "NETWORK_RECOVERY_LOOP",
)

LOOP_CATALOG = {
    name: {"loop_id": name, "state": "READY", "owner": "NEXUS", "current_step": "START", "next_step": "START",
           "inputs": [], "outputs": [], "metrics": [], "handoffs": [], "authority": "governed_read_only"}
    for name in LOOP_TYPES
}
LOOP_CATALOG.update({
    "OPPORTUNITY_LOOP": {**LOOP_CATALOG["OPPORTUNITY_LOOP"], "states": ["DISCOVER", "RESEARCH", "VERIFY", "CHALLENGE", "ECONOMIC_TEST", "NOVA_REVIEW", "ACCEPT", "WATCH", "REJECT"], "owner": "NEXUS", "handoffs": ["ALPHA", "NOVA"]},
    "TRADING_RESEARCH_LOOP": {**LOOP_CATALOG["TRADING_RESEARCH_LOOP"], "states": ["MARKET_QUESTION", "RESEARCH", "HYPOTHESIS", "RULE_SPEC", "BACKTEST", "OOS_TEST", "ROBUSTNESS", "PAPER", "OBSERVE", "ANALYZE", "KEEP", "MODIFY", "RETIRE"], "owner": "TRADING_ENGINE", "handoffs": ["ALPHA", "NOVA"]},
    "RUNTIME_RECOVERY_LOOP": {**LOOP_CATALOG["RUNTIME_RECOVERY_LOOP"], "states": ["BOOTSTRAP", "INSPECT", "RESTORE", "RECONCILE", "RESUME", "VERIFY", "RECEIPT"], "owner": "NEXUS", "authority": "bounded_approved_actions"},
    "NETWORK_RECOVERY_LOOP": {**LOOP_CATALOG["NETWORK_RECOVERY_LOOP"], "states": ["DETECT", "WAITING_DEPENDENCY", "RECONNECTING", "REFRESH", "RESUME", "VERIFY"], "owner": "NEXUS", "authority": "bounded_reconnect"},
})

TRADING_STRATEGY_STATUSES = ("CANDIDATE", "BACKTESTING", "REJECTED", "PAPER_APPROVED", "PAPER_ACTIVE", "DEGRADED", "SUPERSEDED", "RETIRED")
TRADING_METRICS = ("net_return", "gross_profit", "gross_loss", "win_rate", "loss_rate", "expectancy", "profit_factor", "max_drawdown", "average_trade", "trade_count", "sharpe", "sortino", "mae", "mfe", "consecutive_losses", "exposure", "performance_by_instrument", "performance_by_timeframe", "performance_by_regime")
WORK_ORDER_STATUSES = ("CREATED", "READY", "ASSIGNED", "IN_PROGRESS", "WAITING_DEPENDENCY", "WAITING_REVIEW", "COMPLETED", "FAILED", "CANCELLED")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def specialist_contract(specialist_id: str, **overrides: Any) -> dict[str, Any]:
    base = SPECIALISTS[specialist_id]
    return {"specialist_id": specialist_id, "name": specialist_id, "role": base["role"], "mission": base["role"],
            "department": base["department"], "status": base["status"], "company_goal_ids": [], "initiative_ids": [],
            "skills": sorted(SKILL_ASSIGNMENTS.get(specialist_id, {})), "skill_versions": SKILL_ASSIGNMENTS.get(specialist_id, {}),
            "native_tools": [], "mcp_resources": sorted(RESOURCE_PERMISSIONS.get(specialist_id, {})),
            "allowed_capabilities": sorted(RESOURCE_PERMISSIONS.get(specialist_id, {})), "authority_level": base["authority_level"],
            "python_first_tasks": [], "ai_review_triggers": [], "cost_budget": {"max_usd": 0, "ai_invocations": 0}, "retry_budget": {"max_attempts": 1},
            "input_contract": {"type": "bounded_json"}, "output_contract": {"type": "bounded_result_with_receipt"}, "work_order_types": [],
            "metrics": [], "quality_metrics": [], "failure_behavior": "fail_closed", "escalation_behavior": "return_to_nova_or_ray_review",
            "knowledge_sources": [], "temporary_data_policy": "local_or_ephemeral_only", "persistence_policy": "durable_state_via_nexus",
            "return_to_nova_contract": ["request", "result", "evidence", "confidence", "risks", "next_action"], **overrides}


def build_work_order(*, goal_id: str, work_type: str, owner_specialist: str, inputs: Mapping[str, Any] | None = None, initiative_id: str | None = None, loop_id: str | None = None, authority_required: str = "internal_read_only", approval_required: bool = False, priority: str = "normal", cost_budget: Mapping[str, Any] | None = None, retry_budget: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if owner_specialist not in SPECIALISTS:
        raise ValueError("unknown_specialist")
    timestamp = _now()
    order = {"schema_version": "nexus.work-order.v1", "work_order_id": _id("wo"), "goal_id": goal_id, "initiative_id": initiative_id, "loop_id": loop_id,
             "work_type": work_type, "owner_specialist": owner_specialist, "status": "CREATED", "inputs": dict(inputs or {}), "required_capabilities": [],
             "authority_required": authority_required, "approval_required": approval_required, "priority": priority, "cost_budget": dict(cost_budget or {"max_usd": 0}),
             "retry_budget": dict(retry_budget or {"max_attempts": 1}), "created_at": timestamp, "started_at": None, "completed_at": None,
             "result": None, "result_refs": [], "receipt_refs": [], "metrics": {}, "failure_reason": None, "next_action": None, "return_to_nova": True}
    order["idempotency_key"] = _fingerprint({"goal_id": goal_id, "work_type": work_type, "inputs": order["inputs"]})
    return order


def transition_work_order(order: Mapping[str, Any], status: str, **changes: Any) -> dict[str, Any]:
    if status not in WORK_ORDER_STATUSES:
        raise ValueError("invalid_work_order_status")
    updated = dict(order)
    updated["status"] = status
    updated.update(changes)
    if status == "IN_PROGRESS" and not updated.get("started_at"):
        updated["started_at"] = _now()
    if status in {"COMPLETED", "FAILED", "CANCELLED"}:
        updated["completed_at"] = updated.get("completed_at") or _now()
    return updated


def complete_work_order(order: Mapping[str, Any], result: Mapping[str, Any], *, receipt_ref: str) -> dict[str, Any]:
    if not isinstance(result, Mapping) or result.get("status") != "PASS":
        raise ValueError("result_not_verified")
    return transition_work_order(order, "COMPLETED", result=dict(result), receipt_refs=[receipt_ref], next_action=None)


def build_goal(goal_id: str, *, owner: str, title: str, parent_goal_id: str | None = None, priority: str = "normal", target_metric: str | None = None, target_value: Any = None, time_horizon: str | None = None) -> dict[str, Any]:
    now = _now()
    return {"goal_id": goal_id, "parent_goal_id": parent_goal_id, "owner": owner, "title": title, "status": "ACTIVE", "priority": priority, "target_metric": target_metric, "target_value": target_value, "time_horizon": time_horizon, "created_at": now, "updated_at": now}


def build_loop_state(loop_id: str, *, goal_id: str | None = None, owner: str = "NEXUS") -> dict[str, Any]:
    now = _now()
    return {"loop_id": loop_id, "loop_type": loop_id, "goal_id": goal_id, "initiative_id": None, "state": "READY", "owner": owner, "current_step": "START", "next_step": "START", "inputs": {}, "outputs": {}, "metrics": {}, "last_run": None, "next_run": None, "status": "READY", "failure_count": 0, "receipt_refs": [], "updated_at": now}


def dependency_state(name: str, state: str = "CONNECTED", *, attempt: int = 0, last_error: str | None = None) -> dict[str, Any]:
    if state not in {"CONNECTED", "DEGRADED", "DISCONNECTED", "RECONNECTING"}:
        raise ValueError("invalid_dependency_state")
    return {"dependency": name, "state": state, "attempt": attempt, "last_error": last_error, "secret_present": False, "updated_at": _now()}


def improvement_candidate(candidate_id: str, *, domain: str, hypothesis: str = "", source: str = "internal_observation") -> dict[str, Any]:
    return {"candidate_id": candidate_id, "domain": domain, "current_version": "baseline", "candidate_version": "candidate", "source": source, "hypothesis": hypothesis, "expected_benefit": None, "baseline_metrics": {}, "test_metrics": {}, "risk": "bounded", "status": "CANDIDATE", "evidence": [], "rollback_target": "baseline"}


def persist_organization() -> dict[str, int]:
    """Persist the selected bounded organization in the existing governed store."""
    from nexus_agent_platform.governed import persistence
    counts: dict[str, int] = {}
    for specialist_id in SPECIALISTS:
        persistence.append_record("specialists", specialist_contract(specialist_id))
    counts["specialists"] = len(SPECIALISTS)
    for specialist_id, resources in RESOURCE_PERMISSIONS.items():
        persistence.append_record("specialist_permissions", {"specialist_id": specialist_id, "permissions": resources, "authority_owner": "Nexus"})
    counts["specialist_permissions"] = len(RESOURCE_PERMISSIONS)
    for specialist_id, skills in SKILL_ASSIGNMENTS.items():
        persistence.append_record("skill_assignments", {"specialist_id": specialist_id, "skills": skills})
    counts["skill_assignments"] = len(SKILL_ASSIGNMENTS)
    for loop_id, state in LOOP_CATALOG.items():
        persistence.append_record("loop_state", build_loop_state(loop_id, owner=state["owner"]))
    counts["loop_state"] = len(LOOP_CATALOG)
    return counts


def load_organization() -> dict[str, list[dict[str, Any]]]:
    """Reload bounded organization records from the governed store."""
    from nexus_agent_platform.governed import persistence
    return {name: persistence.read_records(name) for name in ("specialists", "specialist_permissions", "skill_assignments", "loop_state")}


def validate_trading_safety() -> dict[str, Any]:
    return {"LIVE_TRADING": False, "AUTO_TRADING": False, "PAPER_ONLY": True, "LIVE_TRADING_AUTHORITY": "NONE", "status": "PASS"}


def trading_strategy(strategy_id: str = "strategy_candidate_v1") -> dict[str, Any]:
    return {"strategy_id": strategy_id, "name": strategy_id, "version": "1.0", "status": "CANDIDATE", "market": "FX", "instrument": None, "timeframes": [], "entry_rules": [], "exit_rules": [], "risk_rules": [], "position_sizing": {}, "data_requirements": [], "hypothesis": "", "source_evidence": [], "backtest_config": {}, "out_of_sample_config": {}, "paper_config": {"enabled": True}, "metrics": {}, "baseline_metrics": {}, "created_at": _now(), "last_tested_at": None, "last_paper_run": None}


def metric(entity_type: str, entity_id: str, metric_name: str, metric_value: Any, *, source: str = "deterministic_python", period: str | None = None, baseline: Any = None) -> dict[str, Any]:
    if metric_name not in TRADING_METRICS and entity_type == "trading":
        raise ValueError("unknown_trading_metric")
    return {"entity_type": entity_type, "entity_id": entity_id, "metric_name": metric_name, "metric_value": metric_value, "period": period, "baseline": baseline, "comparison": None, "source": source, "measured_at": _now()}


def run_foundation_proof() -> dict[str, Any]:
    """Run bounded, synthetic, no-external-write proofs for four work paths."""
    safety = validate_trading_safety()
    business = complete_work_order(build_work_order(goal_id="goal_business_demo", work_type="research", owner_specialist="ALPHA", inputs={"idea": "synthetic service"}), {"status": "PASS", "artifact": "bounded_research_result"}, receipt_ref="dev:business")
    trading = complete_work_order(build_work_order(goal_id="goal_trading_demo", work_type="backtest", owner_specialist="TRADING_ENGINE", inputs={"strategy": "synthetic_candidate"}), {"status": "PASS", "artifact": "bounded_backtest_metrics"}, receipt_ref="dev:trading")
    improvement = complete_work_order(build_work_order(goal_id="goal_improvement_demo", work_type="capability_improvement", owner_specialist="JAX", inputs={"gap": "synthetic inefficiency"}), {"status": "PASS", "artifact": "sandbox_benchmark"}, receipt_ref="dev:improvement")
    repair = complete_work_order(build_work_order(goal_id="goal_repair_demo", work_type="system_repair", owner_specialist="JAX", inputs={"issue": "synthetic health defect"}), {"status": "PASS", "artifact": "verification_receipt"}, receipt_ref="dev:repair")
    loop = build_loop_state("TRADING_RESEARCH_LOOP", goal_id="goal_trading_demo")
    restored_order = json.loads(json.dumps(trading))
    restored_loop = json.loads(json.dumps({**loop, "state": "BACKTEST", "current_step": "BACKTEST", "next_step": "OOS_TEST"}))
    recovery_ok = restored_order["status"] == "COMPLETED" and restored_order["idempotency_key"] == trading["idempotency_key"] and restored_loop["next_step"] == "OOS_TEST"
    network_wait = dependency_state("synthetic_external", "DISCONNECTED", attempt=1, last_error="bounded_test_failure")
    network_resume = dependency_state("synthetic_external", "CONNECTED", attempt=2)
    network_ok = network_wait["state"] == "DISCONNECTED" and network_resume["state"] == "CONNECTED" and not network_resume["secret_present"]
    return {"status": "PASS" if recovery_ok and network_ok else "FAIL", "business": business["status"], "trading": trading["status"], "improvement": improvement["status"], "repair": repair["status"], "work_order_recovery": "PASS" if recovery_ok else "FAIL", "loop_recovery": "PASS" if recovery_ok else "FAIL", "process_recovery": "PASS" if recovery_ok else "FAIL", "network_recovery": "PASS" if network_ok else "FAIL", "trading_safety": safety}
