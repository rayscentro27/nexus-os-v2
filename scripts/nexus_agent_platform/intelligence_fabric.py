"""Universal department intelligence fabric.

This is a thin contract layer over the existing governed persistence and
``alpha_research`` implementation.  It does not create a second queue, router,
objective engine, or Alpha implementation.  Requests and feedback are
append-only correlation records so every department can pause for knowledge,
receive an Alpha-reviewed result, resume its work, and send the outcome back.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from nexus_agent_platform import alpha_research
from nexus_agent_platform.governed import persistence

REQUEST_SCHEMA = "nexus.department-research-request.v1"
RESULT_SCHEMA = "nexus.department-result-feedback.v1"

DEPARTMENTS = (
    "ALPHA", "HERMES_NOVA", "SYSTEMS_ENGINEERING", "CREATIVE", "MARKETING",
    "SEO", "CLYDE_CREDIT", "FUNDING", "FINANCE", "BUSINESS_OPPORTUNITY",
    "TRADING_RESEARCH",
)
REQUEST_STATES = {"RECEIVED", "RESEARCHING", "ALPHA_REVIEW", "FOLLOW_UP_REQUIRED", "READY_TO_RESUME", "RESUMED", "BLOCKED"}
RESULT_STATES = {"SUCCESS", "FAILURE", "PARTIAL"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str, payload: Any) -> str:
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:20]
    return f"{prefix}_{digest}"


def build_research_request(*, department: str, question: str, knowledge_gap: str,
                           objective_id: str = "", parent_goal_id: str = "",
                           work_order_id: str = "", reason_needed: str = "",
                           desired_evidence: Optional[list[str]] = None,
                           risk_consequence: str = "UNKNOWN",
                           freshness_requirement: str = "CURRENT",
                           priority: str = "P2_REVENUE", next_action: str = "") -> dict[str, Any]:
    department = str(department).upper()
    if department not in DEPARTMENTS:
        raise ValueError("unknown-department")
    if len(str(question).strip()) < 8 or len(str(knowledge_gap).strip()) < 8:
        raise ValueError("question-and-knowledge-gap-required")
    payload = {
        "schema_version": REQUEST_SCHEMA,
        "request_id": _id("research_request", (department, objective_id, question, knowledge_gap)),
        "department": department,
        "objective_id": objective_id,
        "parent_goal_id": parent_goal_id,
        "work_order_id": work_order_id,
        "question": str(question).strip(),
        "knowledge_gap": str(knowledge_gap).strip(),
        "reason_needed": str(reason_needed or "Knowledge is required to continue the originating objective.").strip(),
        "desired_evidence": list(desired_evidence or ["source-backed finding", "freshness", "uncertainty"]),
        "risk_consequence": risk_consequence,
        "freshness_requirement": freshness_requirement,
        "created_at": _now(),
        "priority": priority,
        "research_status": "RECEIVED",
        "alpha_status": "NOT_STARTED",
        "result_reference": None,
        "next_action": next_action or "Run bounded Research, then Alpha review.",
        "follow_up_request_id": None,
        "department_resume": "WAITING_FOR_INTELLIGENCE",
    }
    return payload


def persist_research_request(request: dict[str, Any]) -> dict[str, Any]:
    if request.get("schema_version") != REQUEST_SCHEMA or request.get("department") not in DEPARTMENTS:
        raise ValueError("invalid-research-request")
    if request.get("research_status") not in REQUEST_STATES:
        raise ValueError("invalid-research-request-state")
    persistence.append_record("research_requests", request)
    persistence.emit_audit_event({"event": "department_research_request_recorded", "request_id": request["request_id"], "department": request["department"], "objective_id": request.get("objective_id"), "external_action_performed": False})
    return request


def _evidence(item: dict[str, Any], request_id: str, index: int) -> dict[str, Any]:
    text = str(item.get("text") or item.get("result") or item.get("content") or "")
    return {
        "schema_version": "nexus.evidence.v1",
        "evidence_id": item.get("evidence_id") or f"fabric-evidence-{request_id}-{index}",
        "job_id": request_id,
        "status": item.get("status", "SUCCESS"),
        "source": {"source_type": item.get("source_type", "department_internal_result"), "original_reference": item.get("source", "department fixture"), "retrieved_at": item.get("retrieved_at", _now())},
        "integrity": {"material_hash": hashlib.sha256(text.encode()).hexdigest()},
        "content": {"normalized_text_or_markdown": text},
    }


def run_research_request(request: dict[str, Any], evidence: Iterable[dict[str, Any]], *, claim: str = "") -> dict[str, Any]:
    """Run the existing Alpha research implementation and correlate its result."""
    persist_research_request({**request, "research_status": "RESEARCHING"})
    job = alpha_research.build_research_job(
        objective=request["question"],
        research_type="MARKET_RESEARCH",
        requested_by=request["department"],
        freshness_requirement=request.get("freshness_requirement", "CURRENT"),
        job_id=request["request_id"],
    )
    evidence_rows = [_evidence(item, request["request_id"], index) for index, item in enumerate(evidence)]
    claim_specs = [{"claim": claim or request["knowledge_gap"], "claim_type": "DEPARTMENT_RESEARCH", "confidence": "MEDIUM", "evidence_refs": [row["evidence_id"] for row in evidence_rows], "source_quality": "INTERNAL_OR_PUBLIC"}]
    alpha = alpha_research.run_alpha_research(job, evidence_rows, claim_specs=claim_specs, runtime_root=None)
    pack = alpha["pack"]
    alpha_status = "QUALIFIED" if pack["status"] == "COMPLETE" and pack["findings"] else "MORE_RESEARCH_REQUIRED"
    result_ref = alpha["receipt"]["receipt_id"]
    updated = {**request, "research_status": "READY_TO_RESUME" if alpha_status == "QUALIFIED" else "FOLLOW_UP_REQUIRED", "alpha_status": alpha_status, "result_reference": result_ref, "next_action": "Resume originating department objective." if alpha_status == "QUALIFIED" else "Investigate the evidence deficiency through targeted Research."}
    follow_up = None
    if alpha_status != "QUALIFIED":
        follow_up = build_research_request(department=request["department"], objective_id=request.get("objective_id", ""), parent_goal_id=request.get("parent_goal_id", ""), work_order_id=request.get("work_order_id", ""), question=f"Follow up on: {request['question']}", knowledge_gap="Resolve the evidence deficiency identified by Alpha.", reason_needed="Alpha found insufficient evidence.", desired_evidence=request.get("desired_evidence"), risk_consequence=request.get("risk_consequence", "UNKNOWN"), freshness_requirement=request.get("freshness_requirement", "CURRENT"), priority=request.get("priority", "P2_REVENUE"))
        persist_research_request(follow_up)
        updated["follow_up_request_id"] = follow_up["request_id"]
    persist_research_request(updated)
    return {"request": updated, "alpha": alpha, "alpha_decision": alpha_status, "follow_up": follow_up}


def resume_department(request: dict[str, Any], *, next_action: str) -> dict[str, Any]:
    if request.get("research_status") != "READY_TO_RESUME":
        raise ValueError("research-not-ready-to-resume")
    resumed = {**request, "research_status": "RESUMED", "department_resume": "RESUMED", "next_action": next_action, "resumed_at": _now()}
    persist_research_request(resumed)
    return resumed


def record_result_feedback(*, department: str, action: str, result: str, evidence: Iterable[dict[str, Any]], objective_id: str = "", parent_goal_id: str = "", work_order_id: str = "", measurement: Optional[dict[str, Any]] = None, outcome: str = "PARTIAL", what_changed: str = "", unexpected_result: str = "", knowledge_implication: str = "", next_recommendation: str = "") -> dict[str, Any]:
    department = str(department).upper()
    if department not in DEPARTMENTS or outcome not in RESULT_STATES:
        raise ValueError("invalid-result-feedback")
    feedback = {"schema_version": RESULT_SCHEMA, "result_id": _id("result", (department, objective_id, action, result)), "department": department, "objective_id": objective_id, "parent_goal_id": parent_goal_id, "work_order_id": work_order_id, "action": action, "result": result, "evidence": list(evidence), "measurement": measurement or {}, "evidence_level": "LEVEL_1_SYNTHETIC" if not evidence else "INTERNAL_MEASUREMENT", "outcome": outcome, "what_changed": what_changed, "unexpected_result": unexpected_result, "knowledge_implication": knowledge_implication, "research_review_state": "PENDING", "alpha_review_state": "PENDING", "next_recommendation": next_recommendation or "Research interprets the result before the next objective action.", "created_at": _now(), "follow_up_request_id": None}
    persistence.append_record("result_feedback", feedback)
    persistence.emit_audit_event({"event": "department_result_feedback_recorded", "result_id": feedback["result_id"], "department": department, "objective_id": objective_id, "external_action_performed": False})
    review_evidence = [{"text": json.dumps(feedback, sort_keys=True), "source": f"result:{feedback['result_id']}", "source_type": "department_result"}]
    alpha = run_research_request(build_research_request(department=department, objective_id=objective_id, parent_goal_id=parent_goal_id, work_order_id=work_order_id, question=f"Interpret result from {department}: {action}", knowledge_gap="Determine what this result proves and what should happen next.", reason_needed="Result feedback must update knowledge and the objective.", desired_evidence=["interpretation", "limitation", "next recommendation"], priority="P2_REVENUE"), review_evidence, claim=knowledge_implication or result)
    state = "QUALIFIED" if alpha["alpha_decision"] == "QUALIFIED" else "MORE_RESEARCH_REQUIRED"
    updated = {**feedback, "research_review_state": "COMPLETE", "alpha_review_state": state, "follow_up_request_id": (alpha.get("follow_up") or {}).get("request_id")}
    persistence.append_record("result_feedback", updated)
    return {"feedback": updated, "research": alpha}
