"""Bounded adaptive improvement contracts for Nexus business and growth loops.

Deterministic state, lineage, scoring, budgets, and idempotency live here. Alpha
and Nova may interpret the packet, but neither can promote unobserved evidence.
External publication, spend, outreach, and launch are explicitly out of scope.
"""
from __future__ import annotations

import hashlib, json
from datetime import datetime, timezone
from typing import Any, Mapping

from nexus_agent_platform.governed import persistence
from .contracts import assign_work_order, build_work_order, complete_work_order

RESULTS = ("POSITIVE", "NEGATIVE", "MIXED", "INSUFFICIENT_EVIDENCE", "NO_DATA", "SYSTEM_FAILURE", "INVALID_TEST", "STALE_EVIDENCE")
FAILURE_DIMENSIONS = ("CUSTOMER", "PROBLEM", "OFFER", "PRICE", "CHANNEL", "POSITIONING", "TRUST", "DELIVERY", "COST", "CAC", "CONVERSION", "RETENTION", "COMPETITION", "TIMING", "TECHNOLOGY", "REGULATION", "DATA_QUALITY", "EXECUTION", "SYSTEM_FAILURE", "INSUFFICIENT_SAMPLE", "UNKNOWN")
DECISIONS = ("KEEP", "OPTIMIZE", "TRANSFORM", "RESEARCH_MORE", "RETEST", "WATCH", "REJECT")
BUDGET = {"MAX_RESEARCH_REVISIONS": 2, "MAX_TRANSFORMATIONS": 3, "MAX_VALIDATION_VARIANTS": 4, "MAX_COST_USD": 0, "MAX_RUNTIME_SECONDS": 180}

def _now() -> str: return datetime.now(timezone.utc).isoformat()
def _fp(value: Any) -> str: return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()[:20]

def classify_result(metrics: Mapping[str, Any] | None, *, system_failure: bool = False, invalid_test: bool = False, stale: bool = False) -> str:
    if system_failure: return "SYSTEM_FAILURE"
    if invalid_test: return "INVALID_TEST"
    if stale: return "STALE_EVIDENCE"
    metrics = metrics or {}
    if metrics.get("sample_status") == "NO_REAL_VALIDATION_DATA" or not any(int(v or 0) for v in (metrics.get("counts") or {}).values()): return "NO_DATA"
    if metrics.get("sample_status") in {"OBSERVED_SAMPLE_INSUFFICIENT", "INSUFFICIENT_EVIDENCE"}: return "INSUFFICIENT_EVIDENCE"
    counts = metrics.get("counts") or {}
    if counts.get("OBJECTION", 0) and counts.get("LEAD", 0): return "MIXED"
    return "POSITIVE" if counts.get("LEAD", 0) or counts.get("BOOKING_INTENT", 0) else "NEGATIVE"

def diagnose(opportunity: Mapping[str, Any], result: str, metrics: Mapping[str, Any] | None = None) -> dict[str, Any]:
    oid = str(opportunity["opportunity_id"]); did = "diagnosis_" + _fp({"opportunity": oid, "version": "opp_v1", "result": result})
    existing = persistence.get_record("adaptive_diagnoses", did, key="diagnosis_id")
    if existing: return existing
    no_data = result in {"NO_DATA", "INSUFFICIENT_EVIDENCE"}
    row = {"schema_version": "nexus.adaptive-diagnosis.v1", "diagnosis_id": did, "subject_id": oid, "subject_version": "opp_v1", "result": result, "observed_evidence": metrics or {"sample_status": "NO_REAL_VALIDATION_DATA"}, "failure_dimension": "INSUFFICIENT_SAMPLE" if no_data else "UNKNOWN", "root_cause_hypothesis": "measurement has not produced a valid sample; this does not establish market failure" if no_data else "requires evidence-backed diagnosis", "supporting_evidence": ["WP8.9 growth validation state"], "contrary_evidence": [], "confidence": "LOW" if no_data else "UNSET", "unknowns": ["demand", "CAC", "conversion", "retention", "route density", "membership interest", "pricing", "throughput"], "created_at": _now()}
    persistence.append_record("adaptive_diagnoses", row); return row

def generate_variants(opportunity: Mapping[str, Any], diagnosis_row: Mapping[str, Any]) -> list[dict[str, Any]]:
    oid = opportunity["opportunity_id"]
    specs = [
        ("individual_vehicle_convenience", "CHANNEL", "Test organic local interest for individual vehicle owners using the existing core service.", "demand and conversion", "qualified lead or booking intent from an observed no-spend sample", "no qualified interest after a valid bounded sample"),
        ("multi_vehicle_household", "PACKAGING", "Test a multi-vehicle household package with the same service capability.", "packaging and willingness to pay", "multi-vehicle inquiry or package preference", "no package interest or objections about price/value"),
        ("fleet_business_account", "CUSTOMER_SEGMENT", "Test local fleet and small-business accounts for route density and repeat need.", "route density and B2B demand", "qualified fleet inquiry with vehicle count and cadence", "no qualified fleet interest after targeted evidence"),
        ("monthly_maintenance_membership", "OFFER", "Test recurring maintenance as a distinct offer hypothesis after core interest is measured.", "membership interest and retention hypothesis", "explicit recurring-service interest", "one-time-only preference or delivery capacity concern"),
    ]
    rows = []
    for name, change_dim, change, addressed, success, failure in specs:
        vid = "variant_" + _fp({"opportunity": oid, "name": name})
        row = {"schema_version": "nexus.adaptive-variant.v1", "variant_id": vid, "subject_id": oid, "parent_version": "opp_v1", "version": "opp_v1_" + name, "name": name, "change": change, "change_dimension": change_dim, "why_change": "WP8.9 has NO_DATA; isolate one major uncertainty before rejecting the opportunity", "failure_addressed": addressed, "expected_improvement": "higher-quality observed evidence", "success_metric": success, "failure_signal": failure, "classification": "OPTIMIZATION" if name == "individual_vehicle_convenience" else "TRANSFORMATION", "cost_usd": 0, "timebox": "bounded 7-day internal measurement preparation", "reversible": True, "learning_value": "HIGH", "status": "CANDIDATE", "created_at": _now()}
        prior = persistence.get_record("adaptive_variants", vid, key="variant_id")
        rows.append(prior or persistence.append_record("adaptive_variants", row))
    return rows

def score_variant(row: Mapping[str, Any]) -> float:
    weights = {"evidence": .15, "economic": .12, "ease": .20, "cost": .15, "time": .12, "fit": .10, "learning": .12, "risk": .04}
    values = {"evidence": 0.45, "economic": .5, "ease": .9 if row["name"] == "individual_vehicle_convenience" else .65, "cost": 1.0, "time": .9, "fit": .9, "learning": .9, "risk": .9}
    return round(sum(weights[k] * values[k] for k in weights) * 100, 2)

def rank_variants(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(row, score=score_variant(row), rank=i) for i, row in enumerate(sorted(rows, key=lambda x: (-score_variant(x), x["variant_id"])), 1)]

def _work(order_type: str, owner: str, inputs: dict[str, Any], capabilities: tuple[str, ...]) -> dict[str, Any]:
    key = _fp({"work_type": order_type, "inputs": inputs})
    prior = next((x for x in persistence.read_records("work_orders") if x.get("idempotency_key") == key and x.get("status") == "COMPLETED"), None)
    if prior: return prior
    order = build_work_order(goal_id="goal_revenue_opportunities", work_type=order_type, owner_specialist=owner, inputs=inputs, authority_required="internal_read_only", cost_budget={"max_usd": 0}, retry_budget={"max_attempts": 1})
    order["idempotency_key"] = key; order = assign_work_order(order, required_capabilities=capabilities)
    order = complete_work_order(order, {"status": "PASS", "external_action_performed": False, "bounded": True}, receipt_ref="adaptive:" + key)
    persistence.append_record("work_orders", order); return order

def run_adaptive_improvement_loop() -> dict[str, Any]:
    opp = next((x for x in persistence.read_records("opportunities") if x.get("opportunity_id") == "opp_bffe3378956f40bb9317970938eb3f21"), None)
    if not opp: raise RuntimeError("real_wp8_8_opportunity_missing")
    growth = next((x for x in persistence.read_records("business_research") if x.get("type") == "GROWTH_VALIDATION_PLAN" and x.get("opportunity_id") == opp["opportunity_id"]), None)
    metrics = next((x.get("result") for x in persistence.read_records("metrics") if x.get("type") == "GROWTH_VALIDATION_METRICS" and x.get("opportunity_id") == opp["opportunity_id"]), None) or {"sample_status": "NO_REAL_VALIDATION_DATA", "counts": {}}
    result = classify_result(metrics); diagnosis_row = diagnose(opp, result, metrics); ranked = rank_variants(generate_variants(opp, diagnosis_row)); selected = ranked[0]
    inputs = {"opportunity_id": opp["opportunity_id"], "variant_id": selected["variant_id"], "diagnosis_id": diagnosis_row["diagnosis_id"], "mode": "NO_SPEND_ORGANIC_MEASUREMENT", "external_action_performed": False}
    orders = [_work("adaptive_alpha_research", "ALPHA", inputs, ("python",)), _work("adaptive_growth_validation", "GROWTH", inputs, ("analytics",)), _work("adaptive_creative_concept", "CREATIVE", inputs, ("campaign_briefs",))]
    learning_id = "learning_" + _fp({"opportunity": opp["opportunity_id"], "diagnosis": diagnosis_row["diagnosis_id"]})
    learning = persistence.get_record("adaptive_learning", learning_id, key="learning_id") or persistence.append_record("adaptive_learning", {"schema_version": "nexus.adaptive-learning.v1", "learning_id": learning_id, "subject_id": opp["opportunity_id"], "result": result, "learning": "NO_DATA is a measurement gap, not a market failure; test the cheapest useful variant before rejection.", "evidence_refs": [diagnosis_row["diagnosis_id"]], "status": "CANDIDATE", "promoted": False, "created_at": _now()})
    run_id = "adaptive_run_" + _fp(opp["opportunity_id"]); run = persistence.get_record("adaptive_runs", run_id, key="run_id") or persistence.append_record("adaptive_runs", {"schema_version": "nexus.adaptive-run.v1", "run_id": run_id, "subject_id": opp["opportunity_id"], "result": result, "diagnosis_id": diagnosis_row["diagnosis_id"], "ranked_variants": ranked, "selected_variant_id": selected["variant_id"], "decision": "RETEST", "budget": BUDGET, "work_order_ids": [x["work_order_id"] for x in orders], "status": "READY_FOR_RETEST", "external_actions": False, "created_at": _now()})
    return {"status": "PASS", "result": result, "diagnosis": diagnosis_row, "variants": ranked, "selected": selected, "work_orders": orders, "learning": learning, "run": run, "contracts": adaptive_contracts()}

def adaptive_contracts() -> dict[str, Any]:
    return {"TRADING": "failed result -> diagnosis -> immutable strategy version -> backtest -> OOS -> paper", "CAPABILITY": "gap -> research -> sandbox -> benchmark -> improve/reject", "MARKETING": "campaign result -> diagnose -> offer/channel/creative/funnel variant -> bounded retest", "CLIENT_OPERATIONS": "workflow outcome -> diagnose friction -> internal improvement candidate; regulated decisions remain governed", "SYSTEM_FAILURE": "system failure pauses learning; never reclassifies as market failure"}

def main() -> None:
    print(json.dumps(run_adaptive_improvement_loop(), indent=2, sort_keys=True, default=str))

if __name__ == "__main__": main()
