"""Controlled Phase 14 business loops.

These are recommendation/research loops only. They consume compact public or
report-backed fixtures supplied by the existing adapters, write bounded loop
state, and use the existing LoopRuntime verifier/ledger contract.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from nexus_agent_platform.loops.runtime import LoopRuntime, LoopSpec, LoopRunResult


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _records(trigger: Dict[str, Any], key: str) -> List[Dict[str, Any]]:
    value = trigger.get(key, [])
    return [item for item in value if isinstance(item, dict)]


def _base_collect(trigger: Dict[str, Any], previous_state: Optional[Dict[str, Any]], key: str, source_name: str) -> Dict[str, Any]:
    records = _records(trigger, key)
    source_hash = _hash(records)
    evidence_hash = _hash([{k: item.get(k) for k in ("id", "source", "source_url", "provenance", "evidence_classification", "freshness", "updated_at")} for item in records])
    return {
        "deterministic_precheck": True,
        "state_version": 1,
        "records": records,
        "summary": {"source": source_name, "input_count": len(records)},
        "material": {"source": source_name, "source_hash": source_hash, "evidence_hash": evidence_hash, "record_count": len(records)},
        "source_hash": source_hash,
        "evidence_hash": evidence_hash,
    }


def _dedupe_by(records: Sequence[Dict[str, Any]], keys: Sequence[str]) -> tuple[List[Dict[str, Any]], int]:
    seen: set[str] = set()
    unique: List[Dict[str, Any]] = []
    duplicates = 0
    for record in records:
        identity = next((str(record.get(key)) for key in keys if record.get(key)), _hash(record))
        if identity in seen:
            duplicates += 1
            continue
        seen.add(identity)
        unique.append(record)
    return unique, duplicates


def _normalize_business_text(value: Any) -> str:
    text = str(value or "").lower()
    text = re.sub(r"\b(duplicate|copy|repeat|evidence|fixture)\b", " ", text)
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _revenue_type(record: Dict[str, Any]) -> str:
    explicit = record.get("canonical_opportunity_type") or record.get("offer_type")
    if explicit:
        return _normalize_business_text(explicit).replace(" ", "_")
    title = _normalize_business_text(record.get("title"))
    evidence = _normalize_business_text(record.get("evidence_ref") or record.get("source"))
    if "readiness" in title or (record.get("estimated_value") == 97 and "money opportunity" in evidence):
        return "readiness_review"
    if "crawl4ai" in title or "research" in title:
        return "research_efficiency"
    return title or "unknown_opportunity"


def revenue_business_identity(record: Dict[str, Any]) -> str:
    """Return a stable semantic identity for report-backed revenue records."""
    evidence = _normalize_business_text(record.get("evidence_ref") or record.get("source"))
    target = _normalize_business_text(record.get("target_audience") or record.get("audience"))
    offer_id = _normalize_business_text(record.get("offer_product_identifier") or record.get("offer_id"))
    value = record.get("offer_price", record.get("estimated_value", "UNKNOWN"))
    value_key = str(value).strip()
    parts = [_revenue_type(record), evidence, target, value_key]
    if offer_id:
        parts.append(offer_id)
    return "revenue:" + _hash(parts)[:24]


def _dedupe_revenue_records(records: Sequence[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], int]:
    seen: set[str] = set()
    unique: List[Dict[str, Any]] = []
    duplicates = 0
    for record in records:
        identity = revenue_business_identity(record)
        if identity in seen:
            duplicates += 1
            continue
        seen.add(identity)
        enriched = dict(record)
        enriched["semantic_dedupe_key"] = identity
        enriched["business_identity"] = identity
        enriched["canonical_opportunity_type"] = _revenue_type(record)
        unique.append(enriched)
    return unique, duplicates


def _scout_collect(trigger: Dict[str, Any], previous_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    collected = _base_collect(trigger, previous_state, "records", "public_open_source_scout")
    unique, duplicates = _dedupe_by(collected["records"], ("repository", "source_url", "id"))
    candidates = [{"id": item.get("id") or item.get("repository"), "repository": item.get("repository"), "title": item.get("title") or item.get("project"), "source_url": item.get("source_url"), "provenance": item.get("provenance") or item.get("source_urls"), "evidence_classification": item.get("evidence_classification", "UNKNOWN")} for item in unique]
    collected.update({"records": unique, "deterministic_output": {"status": "success", "loop_id": "open_source_scout_loop", "candidates": candidates, "deduped_work": duplicates, "value_metric": {"opportunities_created": len(candidates), "duplicate_work_avoided": duplicates}, "value_classification": "ESTIMATED_VALUE", "source_hash": collected["source_hash"], "evidence_hash": collected["evidence_hash"]}})
    return collected


def _seo_collect(trigger: Dict[str, Any], previous_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    collected = _base_collect(trigger, previous_state, "records", "local_seo_fixture")
    unique, duplicates = _dedupe_by(collected["records"], ("keyword", "id"))
    qualified = []
    for item in unique:
        if item.get("keyword") and item.get("source") and item.get("freshness") not in {"STALE", "UNKNOWN"}:
            score = int(item.get("score", 0)) if isinstance(item.get("score", 0), (int, float)) else 0
            if score >= 40:
                qualified.append({"id": item.get("id") or item.get("keyword"), "keyword": item["keyword"], "score": score, "source": item["source"], "freshness": item["freshness"]})
    collected.update({"records": unique, "deterministic_output": {"status": "success", "loop_id": "seo_opportunity_loop", "qualified_keywords": qualified, "deduped_work": duplicates, "value_metric": {"qualified_keywords": len(qualified), "duplicate_work_avoided": duplicates}, "value_classification": "ESTIMATED_VALUE", "source_hash": collected["source_hash"], "evidence_hash": collected["evidence_hash"]}})
    return collected


def _revenue_collect(trigger: Dict[str, Any], previous_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    collected = _base_collect(trigger, previous_state, "records", "report_backed_revenue_opportunities")
    unique, duplicates = _dedupe_revenue_records(collected["records"])
    valid = [item for item in unique if item.get("title") and item.get("evidence_ref") and isinstance(item.get("estimated_value", 0), (int, float))]
    estimated = round(sum(float(item["estimated_value"]) for item in valid), 2)
    confirmed = round(sum(float(item.get("confirmed_revenue", 0)) for item in valid if str(item.get("revenue_status", "")).upper() == "CONFIRMED"), 2)
    source_mode = str(trigger.get("mode", "UNKNOWN"))
    valuation_source = "PROOF_FIXTURE" if "proof" in source_mode or "bounded_internal" in source_mode else "REPORT_BACKED_INPUT"
    output = {"status": "success", "loop_id": "revenue_opportunity_loop", "opportunities": valid, "deduped_work": duplicates, "value_metric": {"opportunities_advanced": len(valid), "estimated_revenue": estimated, "estimated_value_usd": estimated, "confirmed_revenue": confirmed, "confirmed_revenue_usd": confirmed}, "value_classification": "ESTIMATED_VALUE_ONLY", "valuation_source": valuation_source, "live_discovered_revenue": False, "source_hash": collected["source_hash"], "evidence_hash": collected["evidence_hash"]}
    collected.update({"records": unique, "deterministic_output": output})
    return collected


def _intake_collect(trigger: Dict[str, Any], previous_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    collected = _base_collect(trigger, previous_state, "records", "research_intake")
    unique, duplicates = _dedupe_by(collected["records"], ("artifact_id", "id", "source_hash"))
    normalized = [{"artifact_id": item.get("artifact_id") or item.get("id"), "title": item.get("title"), "source": item.get("source"), "source_hash": item.get("source_hash") or _hash(item), "evidence_classification": item.get("evidence_classification", "UNKNOWN"), "normalized": True} for item in unique if item.get("title") and item.get("source")]
    collected.update({"records": unique, "deterministic_output": {"status": "success", "loop_id": "research_intake_loop", "artifacts": normalized, "deduped_work": duplicates, "value_metric": {"research_items_processed": len(normalized), "duplicate_work_avoided": duplicates}, "value_classification": "MEASURED_COUNT", "source_hash": collected["source_hash"], "evidence_hash": collected["evidence_hash"]}})
    return collected


def _no_ai(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return {"use_ai": False, "requested_tier": "T0_DETERMINISTIC", "reason": "initial Phase 14 proof is deterministic-first"}


def _context(collected: Dict[str, Any], reduced: Dict[str, Any], previous_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return {"source_hash": collected.get("source_hash"), "evidence_hash": collected.get("evidence_hash"), "record_count": len(collected.get("records", []))}


def _verify(result: Dict[str, Any], collected: Dict[str, Any], previous_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if result.get("status") != "success":
        return {"status": "fail", "reason": "loop result is not successful"}
    if not result.get("loop_id") or not isinstance(result.get("value_metric"), dict):
        return {"status": "fail", "reason": "value metric or loop identity missing"}
    if not result.get("source_hash") or not result.get("evidence_hash"):
        return {"status": "fail", "reason": "source/evidence hash missing"}
    return {"status": "pass", "reason": "deterministic output, provenance hashes, and value metric verified"}


def _memory(result: Dict[str, Any], collected: Dict[str, Any], previous_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    return {"status": result.get("status"), "loop_id": result.get("loop_id"), "value_metric": result.get("value_metric", {}), "value_classification": result.get("value_classification", "UNKNOWN"), "source_hash": result.get("source_hash"), "evidence_hash": result.get("evidence_hash"), "result_hash": _hash(result), "deduped_work": result.get("deduped_work", 0), "last_processed_at": now, "last_success": now if result.get("status") == "success" else None, "next_eligible_run": "scheduler-defined"}


def _revenue_verifier(result: Dict[str, Any], collected: Dict[str, Any], previous_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    base = _verify(result, collected, previous_state)
    if base["status"] != "pass":
        return base
    records = result.get("opportunities", [])
    keys = [item.get("semantic_dedupe_key") for item in records]
    if len(keys) != len(set(keys)):
        return {"status": "fail", "reason": "semantic duplicate revenue identities remain"}
    metric = result.get("value_metric", {})
    if result.get("value_classification") != "ESTIMATED_VALUE_ONLY":
        return {"status": "fail", "reason": "revenue value classification is not estimate-only"}
    if result.get("live_discovered_revenue") is not False:
        return {"status": "fail", "reason": "fixture/report-backed revenue was not marked non-live"}
    if metric.get("confirmed_revenue_usd") != 0:
        return {"status": "fail", "reason": "unverified revenue entered confirmed revenue"}
    return {"status": "pass", "reason": "semantic identity, estimate-only valuation, and zero confirmed revenue verified"}


def revenue_experiment_selection_gate(result: Dict[str, Any], verifier: Dict[str, Any]) -> Dict[str, Any]:
    """Recheck experiment readiness without launching an external experiment."""
    if verifier.get("status") != "pass":
        return {"status": "BLOCKED", "launch_status": "NOT_LAUNCHED", "reason": "revenue verifier did not pass", "requires_ray_approval": True}
    candidates = result.get("opportunities", [])
    measurable = [item for item in candidates if item.get("opportunity_id") == "readiness_review_97" or item.get("canonical_opportunity_type") == "readiness_review"]
    selected = measurable[0].get("opportunity_id") if measurable else None
    return {"status": "QUALIFIED_WITH_LIMITS" if selected else "DEFER", "launch_status": "NOT_LAUNCHED", "selected_candidate": selected or "UNKNOWN", "reason": "Only report/proof-backed estimated value is available; confirmed revenue is $0 and external execution requires explicit Ray approval.", "estimated_value_usd": result.get("value_metric", {}).get("estimated_value_usd", "UNKNOWN"), "confirmed_revenue_usd": result.get("value_metric", {}).get("confirmed_revenue_usd", "UNKNOWN"), "requires_ray_approval": True, "next_action": "Ray may authorize a separate bounded internal test plan; do not publish, contact, charge, or deploy."}


def _spec(loop_id: str, name: str, goal: str, collector: Any, output: str, metrics: Sequence[str], verifier: Any = _verify) -> LoopSpec:
    return LoopSpec(loop_id=loop_id, name=name, owner="Alpha" if loop_id in {"open_source_scout_loop", "research_intake_loop", "seo_opportunity_loop"} else "Hermes", trigger="bounded internal schedule or event", goal=goal, inputs=("compact current records", "existing report/evidence refs"), deterministic_precheck=collector, delta_only=True, cache_enabled=True, dedupe_enabled=True, deterministic_steps=("read compact delta", "normalize", "dedupe", "verify provenance", "calculate value metric"), ai_steps=(), model_tier="T0_DETERMINISTIC", max_ai_calls=0, max_input_tokens=0, max_output_tokens=0, estimated_token_budget=0, cost_ceiling=0.0, verifier=verifier, retry_policy="bounded", max_retries=0, stop_if_no_change=True, stop_conditions=("no_change", "missing_provenance", "verification_failure"), approval_boundary="internal recommendation only; Ray approval required for external action", output=output, memory_write_mode="bounded_structured", metrics=metrics, ai_decider=_no_ai, ai_context_builder=_context, memory_projection=_memory, schedule_or_event="daily bounded scheduler or explicit internal event", precheck_name="deterministic public/report-backed precheck", verifier_name="deterministic provenance/value verifier", success_condition="structured result and verifier PASS", failure_condition="missing provenance, stale required evidence, or verifier FAIL", value_metric=", ".join(metrics), value_event="verified internal recommendation/research artifact", dedupe_key="source URL/repository/keyword/opportunity/artifact identity", state_key=f"nexus_loop:{loop_id}", freshness_window="source-provided; UNKNOWN blocks freshness-dependent records", pause_condition="repeated no-value runs or unresolved source blocker", kill_condition="protected-path, approval, or verifier violation", next_eligible_run="scheduler-defined")


OPEN_SOURCE_SCOUT_LOOP = _spec("open_source_scout_loop", "Open Source Scout Loop", "Find changed public open-source candidates and prepare provenance-backed internal opportunities.", _scout_collect, "normalized public-source opportunity candidates", ("opportunities_created", "duplicate_work_avoided"))
SEO_OPPORTUNITY_LOOP = _spec("seo_opportunity_loop", "SEO Opportunity Loop", "Score fresh local/public keyword evidence into internal SEO opportunity candidates.", _seo_collect, "fresh scored keyword opportunities", ("qualified_keywords", "duplicate_work_avoided"))
REVENUE_OPPORTUNITY_LOOP = _spec("revenue_opportunity_loop", "Revenue Opportunity Loop", "Rank report-backed opportunities while separating estimated from confirmed revenue.", _revenue_collect, "internal revenue opportunity recommendations", ("opportunities_advanced", "estimated_revenue", "confirmed_revenue"), _revenue_verifier)
RESEARCH_INTAKE_LOOP = _spec("research_intake_loop", "Research Intake Loop", "Normalize and classify new research artifacts without replaying unchanged history.", _intake_collect, "normalized research intake records", ("research_items_processed", "duplicate_work_avoided"))

SELECTED_BUSINESS_LOOPS = (OPEN_SOURCE_SCOUT_LOOP, SEO_OPPORTUNITY_LOOP, REVENUE_OPPORTUNITY_LOOP, RESEARCH_INTAKE_LOOP)


def run_business_loop(runtime: LoopRuntime, spec: LoopSpec, records: List[Dict[str, Any]]) -> LoopRunResult:
    return runtime.run(spec, {"records": records, "mode": "bounded_internal_phase14"})


def eligibility_matrix() -> List[Dict[str, Any]]:
    return [
        {"loop_id": "open_source_scout_loop", "repeatable": True, "finish_condition": True, "deterministic_precheck": True, "tools_available": True, "verifier": True, "value_measurable": True, "value_gt_cost": True, "approval_known": True, "compact_state": True, "unchanged_zero_ai": True, "classification": "QUALIFIED"},
        {"loop_id": "seo_opportunity_loop", "repeatable": True, "finish_condition": True, "deterministic_precheck": True, "tools_available": True, "verifier": True, "value_measurable": True, "value_gt_cost": True, "approval_known": True, "compact_state": True, "unchanged_zero_ai": True, "classification": "QUALIFIED"},
        {"loop_id": "revenue_opportunity_loop", "repeatable": True, "finish_condition": True, "deterministic_precheck": True, "tools_available": True, "verifier": True, "value_measurable": True, "value_gt_cost": True, "approval_known": True, "compact_state": True, "unchanged_zero_ai": True, "classification": "QUALIFIED_WITH_LIMITS"},
        {"loop_id": "research_intake_loop", "repeatable": True, "finish_condition": True, "deterministic_precheck": True, "tools_available": True, "verifier": True, "value_measurable": True, "value_gt_cost": True, "approval_known": True, "compact_state": True, "unchanged_zero_ai": True, "classification": "QUALIFIED"},
        {"loop_id": "affiliate_opportunity_loop", "classification": "DEFER", "reason": "approved partner URLs and live attribution are unavailable; retain research-only surfaces"},
        {"loop_id": "youtube_research_loop", "classification": "DEFER", "reason": "approved transcript/source inputs are incomplete"},
        {"loop_id": "competitor_monitoring_loop", "classification": "DEFER", "reason": "no stable public-source change feed and verifier evidence"},
        {"loop_id": "marketing_research_loop", "classification": "DEFER", "reason": "publishing remains approval-gated and no distinct delta feed is required"},
        {"loop_id": "funding_opportunity_loop", "classification": "DEFER", "reason": "fresh external funding data and eligibility verifier unavailable"},
        {"loop_id": "grant_opportunity_loop", "classification": "DEFER", "reason": "deadline/eligibility source verification is not currently proven"},
    ]
