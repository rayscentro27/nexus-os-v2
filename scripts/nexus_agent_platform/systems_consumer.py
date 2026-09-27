"""Canonical Systems department consumer.

This module is a specialized consumer over the existing governed handoff and
work-order stores.  It does not create a queue or replace Alpha.  For a real
Alpha TEST/QUALIFY handoff it creates an isolated-test planning order.  For
the current Needle/Jev RESEARCH_MORE handoff it supports a bounded evidence
assessment only, preserving Alpha's disposition and returning the exact gap
to Research.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from nexus_agent_platform.bridge.oracle_hermes_cli import run_oracle_hermes
from nexus_agent_platform.governed import persistence
from nexus_foundation.contracts import build_work_order, transition_work_order


SYSTEMS_PROACTIVE_MISSION = (
    "Continuously identify and safely validate technology that makes Nexus "
    "faster, cheaper, more capable, autonomous, reliable, or easier to operate."
)
SYSTEMS_OWNER = "SYSTEMS_AI_WORKER"
SYSTEMS_PROVIDER = "openrouter"
SYSTEMS_MODEL = "openai/gpt-4o-mini"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _latest(rows: list[dict[str, Any]], key: str, value: str) -> dict[str, Any] | None:
    for row in rows:
        if str(row.get(key) or "") == str(value):
            return row
    return None


def _work_order_for_handoff(handoff_id: str) -> dict[str, Any] | None:
    for row in persistence.read_records("work_orders"):
        if row.get("handoff_id") == handoff_id or row.get("inputs", {}).get("handoff_id") == handoff_id:
            return row
    return None


def _json_object(text: str) -> dict[str, Any] | None:
    candidate = text.strip()
    if "```" in candidate:
        blocks = re.findall(r"```(?:json)?\s*(.*?)```", candidate, re.IGNORECASE | re.DOTALL)
        candidate = blocks[0].strip() if blocks else candidate
    try:
        value = json.loads(candidate)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            value = json.loads(candidate[start : end + 1])
            return value if isinstance(value, dict) else None
        except json.JSONDecodeError:
            return None


def _source_refs(handoff: dict[str, Any], handoffs: list[dict[str, Any]]) -> list[str]:
    refs = list(handoff.get("source_refs") or [])
    if refs:
        return refs
    return next((list(row.get("source_refs") or []) for row in handoffs if row.get("handoff_id") == handoff.get("handoff_id") and row.get("source_refs")), [])


def _enrich_from_research_request(handoff: dict[str, Any]) -> dict[str, Any]:
    """Recover lineage fields when the older handoff projection omitted them."""
    alpha = _latest(persistence.read_records("alpha_evaluations"), "receipt_id", str(handoff.get("alpha_receipt_id") or ""))
    if alpha:
        enriched = dict(handoff)
        enriched.setdefault("finding_id", alpha.get("finding_id") or alpha.get("research_id") or alpha.get("investigation_id"))
        enriched.setdefault("objective_id", alpha.get("investigation_id") or alpha.get("research_id"))
        enriched.setdefault("project_id", alpha.get("investigation_id") or alpha.get("research_id"))
        enriched.setdefault("question", alpha.get("recommended_next_step") or alpha.get("why"))
        enriched.setdefault("source_refs", list(alpha.get("source_refs") or alpha.get("evidence_refs") or []))
        enriched.setdefault("unknowns", list(alpha.get("unknowns") or alpha.get("deficiencies") or []))
        enriched.setdefault("recommended_next_step", alpha.get("recommended_next_step"))
        if enriched.get("finding_id"):
            return enriched
    request_id = handoff.get("request_id")
    if not request_id:
        return handoff
    request = _latest(persistence.read_records("research_requests"), "request_id", str(request_id))
    if not request:
        return handoff
    merged = dict(handoff)
    merged.setdefault("finding_id", request.get("parent_finding_id") or request.get("objective_id") or request.get("project_id"))
    merged.setdefault("objective_id", request.get("objective_id"))
    merged.setdefault("project_id", request.get("project_id") or request.get("objective_id"))
    merged.setdefault("question", request.get("question"))
    merged.setdefault("mission", request.get("mission"))
    merged.setdefault("source_refs", [candidate.get("source_url") for candidate in request.get("source_candidates", []) if candidate.get("source_url")])
    merged.setdefault("unknowns", request.get("missing_evidence"))
    merged.setdefault("recommended_next_step", request.get("next_action"))
    return merged


def systems_input_contract(handoff: dict[str, Any]) -> dict[str, Any]:
    """Normalize the governed handoff into the Systems reasoning contract."""
    return {
        "work_order_id": handoff.get("work_order_id"),
        "parent_handoff_id": handoff.get("handoff_id"),
        "parent_alpha_receipt_id": handoff.get("alpha_receipt_id"),
        "parent_research_finding_id": handoff.get("finding_id") or handoff.get("objective_id"),
        "mission": handoff.get("mission") or "Systems capability intelligence",
        "question": handoff.get("question") or "Verify the candidate and its safe Nexus value.",
        "candidate_name": handoff.get("candidate_name") or "Needle / Jev",
        "candidate_type": handoff.get("candidate_type") or "technology_candidate",
        "evidence_summary": handoff.get("evidence_summary") or handoff.get("reasoning_summary") or "Partial public evidence; identity and compatibility unresolved.",
        "evidence_for": list(handoff.get("evidence_for") or []),
        "evidence_against": list(handoff.get("evidence_against") or []),
        "unknowns": list(handoff.get("unknowns") or ["official identity", "license", "runtime", "dependencies", "compatibility", "benchmark value"]),
        "hard_blockers": list(handoff.get("hard_blockers") or []),
        "soft_risks": list(handoff.get("soft_risks") or []),
        "testable_unknowns": list(handoff.get("testable_unknowns") or []),
        "recommended_next_step": handoff.get("recommended_next_step") or handoff.get("next_action"),
        "approval_required": bool(handoff.get("approval_required", False)),
        "expected_output": "identity, license, compatibility, resource requirements, safe host, benchmark plan, and recommendation",
        "source_refs": list(handoff.get("source_refs") or []),
        "project_id": handoff.get("project_id") or handoff.get("finding_id") or handoff.get("objective_id"),
        "goal_id": handoff.get("goal_id"),
    }


def create_systems_work_order(handoff: dict[str, Any], *, assessment_only: bool = False) -> dict[str, Any]:
    """Create one idempotent Systems order without changing Alpha's decision."""
    handoff_id = str(handoff.get("handoff_id") or "")
    if not handoff_id:
        raise ValueError("handoff_id_required")
    department = str(handoff.get("department_target") or "").upper()
    if department != "SYSTEMS":
        raise ValueError("not_systems_handoff")
    existing = _work_order_for_handoff(handoff_id)
    if existing:
        return {**existing, "deduplicated": True}
    decision = str(handoff.get("alpha_decision") or handoff.get("decision") or "").upper()
    allowed = {"TEST", "QUALIFY", "QUALIFIED"}
    if assessment_only:
        allowed.add("RESEARCH_MORE")
    if decision not in allowed:
        raise ValueError("systems_handoff_not_executable")
    contract = systems_input_contract(handoff)
    work_type = "systems_evidence_assessment" if assessment_only else "systems_isolated_test_planning"
    order = build_work_order(
        goal_id=str(contract.get("project_id") or handoff_id),
        work_type=work_type,
        owner_specialist=SYSTEMS_OWNER,
        inputs={**contract, "handoff_id": handoff_id, "decision": decision, "department": "SYSTEMS", "external_action_allowed": False},
        authority_required="internal_read_only",
        approval_required=False,
        priority="normal",
        cost_budget={"max_usd": 0},
        retry_budget={"max_attempts": 1},
    )
    order.update({"handoff_id": handoff_id, "owner": SYSTEMS_OWNER, "department": "SYSTEMS", "idempotency_key": f"systems-intake:{handoff_id}"})
    persistence.append_record("work_orders", order)
    return order


def _systems_prompt(contract: dict[str, Any], *, assessment_only: bool) -> str:
    mode = "evidence assessment only; do not treat this as Alpha TEST or QUALIFY" if assessment_only else "isolated-test planning"
    return (
        "You are the Nexus Systems Engineering reasoning worker. Perform a governed "
        f"{mode} for the supplied public evidence. Do not browse, install, spend, "
        "modify production, or invent facts. Alpha remains the qualification authority. "
        "Return ONLY compact JSON with keys: candidate_identity_status, evidence_for, "
        "evidence_against, unknowns, hard_blockers, soft_risks, capability_value, "
        "test_host, test_host_reason, resource_requirements, isolation_method, "
        "rollback_method, production_risk, disposition, next_action. Disposition must "
        "be one of READY_FOR_ISOLATED_TEST, NEEDS_MORE_EVIDENCE, MONITOR, "
        "NOT_TECHNICALLY_VIABLE, BLOCKED_EXTERNAL, BLOCKED_HUMAN. Prefer ORACLE or "
        "REMOTE_WORKER_CONTROL_PLANE over the Intel production Mac when appropriate.\n\n"
        + json.dumps({"systems_mission": SYSTEMS_PROACTIVE_MISSION, "contract": contract, "known_hosts": {
            "MAC_MINI": "Intel Mac, 8 GiB RAM, production/control-plane importance",
            "ORACLE": "remote Linux, Hermes 0.20.6, isolated server-side test host",
            "REMOTE_WORKER_CONTROL_PLANE": "existing shared bounded remote path",
        }}, ensure_ascii=True)
    )


def claim_and_execute_systems(handoff_id: str, *, assessment_only: bool = False, model_runner=run_oracle_hermes) -> dict[str, Any]:
    """Claim and execute one Systems order through the real model transport."""
    handoffs = persistence.read_records("research_v2_handoffs")
    handoff = _latest(handoffs, "handoff_id", handoff_id)
    if not handoff:
        raise ValueError("handoff_not_found")
    handoff = _enrich_from_research_request(handoff)
    order = create_systems_work_order(handoff, assessment_only=assessment_only)
    if order.get("status") == "COMPLETED":
        analyses = persistence.read_records("systems_ai_analyses")
        latest_analysis = _latest(analyses, "work_order_id", str(order.get("work_order_id")))
        contract = systems_input_contract(handoff)
        refs = _source_refs(handoff, handoffs) or list(contract.get("source_refs") or [])
        if latest_analysis and (not latest_analysis.get("parent_research_finding_id") or not latest_analysis.get("source_refs")):
            persistence.append_record("systems_ai_analyses", {**latest_analysis, "parent_research_finding_id": contract.get("parent_research_finding_id"), "source_refs": refs, "input_contract": contract, "updated_at": _now()})
        if not handoff.get("finding_id") and contract.get("parent_research_finding_id"):
            persistence.append_record("research_v2_handoffs", {**handoff, "status": handoff.get("status") or "RETURNED", "finding_id": contract.get("parent_research_finding_id"), "objective_id": contract.get("project_id"), "project_id": contract.get("project_id"), "source_refs": refs, "updated_at": _now()})
        return {"handoff": handoff, "work_order": order, "deduplicated": True}
    order = transition_work_order(order, "ASSIGNED", assignment_reason="Systems AI worker claim")
    persistence.append_record("work_orders", order)
    order = transition_work_order(order, "IN_PROGRESS", worker_id=SYSTEMS_OWNER, execution_class="AI_REASONING_WORKER")
    persistence.append_record("work_orders", order)
    contract = systems_input_contract(handoff)
    source_refs = _source_refs(handoff, handoffs)
    receipt = model_runner(_systems_prompt(contract, assessment_only=assessment_only), f"systems-{handoff_id[:80]}", timeout_seconds=180, request_id=f"systems:{handoff_id}")
    judgment = _json_object(receipt.response or "") or {
        "disposition": "BLOCKED_EXTERNAL",
        "unknowns": ["model returned no structured judgment"],
        "next_action": "Retry the bounded Systems assessment through the existing worker path.",
    }
    disposition = str(judgment.get("disposition") or "NEEDS_MORE_EVIDENCE").upper()
    if disposition not in {"READY_FOR_ISOLATED_TEST", "NEEDS_MORE_EVIDENCE", "MONITOR", "NOT_TECHNICALLY_VIABLE", "BLOCKED_EXTERNAL", "BLOCKED_HUMAN"}:
        disposition = "NEEDS_MORE_EVIDENCE"
    artifact = {
        "schema_version": "nexus.systems-ai-analysis.v1",
        "analysis_id": persistence.new_id("systems_analysis"),
        "work_order_id": order["work_order_id"],
        "parent_handoff_id": handoff_id,
        "parent_alpha_receipt_id": handoff.get("alpha_receipt_id"),
        "parent_research_finding_id": handoff.get("finding_id") or handoff.get("objective_id"),
        "provider": receipt.provider or SYSTEMS_PROVIDER,
        "model": receipt.model or SYSTEMS_MODEL,
        "model_call_status": receipt.status,
        "model_calls": 1 if receipt.response else 0,
        "model_latency_ms": receipt.latency_ms,
        "runtime_host": receipt.runtime_host,
        "hermes_version": receipt.hermes_version,
        "source_refs": source_refs,
        "input_contract": contract,
        "judgment": judgment,
        "disposition": disposition,
        "production_touch": False,
        "created_at": _now(),
    }
    persistence.append_record("systems_ai_analyses", artifact)
    next_owner = "RESEARCH" if disposition in {"NEEDS_MORE_EVIDENCE", "BLOCKED_EXTERNAL", "BLOCKED_HUMAN"} else SYSTEMS_OWNER
    next_action = {
        "action": judgment.get("next_action") or "Return the exact missing Systems evidence to Research.",
        "owner": next_owner,
        "work_type": "RESEARCH_FOLLOWUP" if next_owner == "RESEARCH" else "SYSTEMS_ISOLATED_TEST",
        "expected_output": "matched identity, license, compatibility, resources, and benchmark evidence" if next_owner == "RESEARCH" else "isolated benchmark result artifact",
        "approval_required": False,
        "return_target": "ALPHA" if next_owner == SYSTEMS_OWNER else "RESEARCH",
    }
    review = {"status": "REVIEWED", "reviewer": "SYSTEMS_AI_REVIEW", "decision": disposition, "reason": judgment.get("next_action") or "Systems bounded assessment completed."}
    result = {"output": artifact, "review": review, "next_action": next_action, "systems_disposition": disposition, "production_touch": False}
    order = transition_work_order(order, "COMPLETED", result=result, receipt_refs=[artifact["analysis_id"]], next_action=next_action)
    order["completed_by"] = SYSTEMS_OWNER
    persistence.append_record("work_orders", order)
    timestamp = _now()
    persistence.append_record("research_v2_handoffs", {**handoff, "systems_assessment_work_order_id": order["work_order_id"], "systems_assessment_status": disposition, "systems_assessment_at": timestamp, "project_state": "SYSTEMS_ASSESSED_NEEDS_EVIDENCE" if next_owner == "RESEARCH" else "READY_FOR_ISOLATED_TEST", "systems_next_action": next_action, "updated_at": timestamp})
    return {"handoff": handoff, "work_order": order, "artifact": artifact, "review": review, "next_action": next_action, "deduplicated": False}


def systems_metrics(*, since: str | None = None) -> dict[str, Any]:
    rows = persistence.read_records("work_orders")
    analyses = persistence.read_records("systems_ai_analyses")
    if since:
        rows = [row for row in rows if str(row.get("created_at") or "") >= since]
        analyses = [row for row in analyses if str(row.get("created_at") or "") >= since]
    latest_analyses: dict[str, dict[str, Any]] = {}
    for row in analyses:
        key = str(row.get("analysis_id") or row.get("work_order_id") or "")
        latest_analyses.setdefault(key, row)
    analyses = list(latest_analyses.values())
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.get("department") == "SYSTEMS" and row.get("work_order_id"):
            latest.setdefault(str(row["work_order_id"]), row)
    return {
        "systems_work_received": len(latest),
        "systems_work_claimed": sum(1 for row in latest.values() if row.get("status") in {"ASSIGNED", "IN_PROGRESS", "COMPLETED"}),
        "systems_ai_analyses": len(analyses),
        "systems_tests_planned": sum(1 for row in latest.values() if row.get("work_type") == "systems_isolated_test_planning"),
        "systems_tests_executed": 0,
        "systems_tests_blocked": sum(1 for row in analyses if row.get("disposition") in {"NEEDS_MORE_EVIDENCE", "BLOCKED_EXTERNAL", "BLOCKED_HUMAN"}),
        "systems_research_returns": sum(1 for row in analyses if row.get("disposition") in {"NEEDS_MORE_EVIDENCE", "BLOCKED_EXTERNAL", "BLOCKED_HUMAN"}),
        "systems_alpha_returns": sum(1 for row in analyses if row.get("disposition") == "READY_FOR_ISOLATED_TEST"),
        "systems_project_transitions": len(analyses),
        "active_systems_candidates": sorted({str((row.get("input_contract") or {}).get("candidate_name") or "UNKNOWN") for row in analyses}),
    }
