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
from nexus_agent_platform.research.claim_verification import assess_evidence, classify_claim
from nexus_agent_platform.research_followup_contract import build_contract, question as contract_question, validate_contract, persist_contract
from nexus_agent_platform.research_followup_contract import build_evidence_packet

REQUEST_SCHEMA = "nexus.research-followup-contract.v1"
RESULT_SCHEMA = "nexus.department-result-feedback.v1"

DEPARTMENTS = (
    "ALPHA", "HERMES_NOVA", "SYSTEMS", "SYSTEMS_ENGINEERING", "CREATIVE", "MARKETING", "CUSTOMER_SERVICE", "TRADING",
    "SEO", "CLYDE_CREDIT", "FUNDING", "FINANCE", "BUSINESS_OPPORTUNITY",
    "TRADING_RESEARCH", "OPPORTUNITIES", "UPGRADE_CONTROL", "LEDGER_FINANCE", "ATLAS_OPPORTUNITY",
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
                           priority: str = "P2_REVENUE", next_action: str = "",
                           research_questions: Optional[list[dict[str, Any]]] = None,
                           decision_unlocked_by_answers: str = "Resume the originating department goal with evidence-backed decision.",
                           parent_handoff_id: str | None = None, subject_type: str = "GOAL",
                           subject_id: str | None = None) -> dict[str, Any]:
    department = str(department).upper()
    if department not in DEPARTMENTS:
        raise ValueError("unknown-department")
    if len(str(question).strip()) < 8 or len(str(knowledge_gap).strip()) < 8:
        raise ValueError("question-and-knowledge-gap-required")
    created_at = _now()
    reason = str(reason_needed or "Knowledge is required to continue the originating objective.").strip()
    evidence = list(desired_evidence or ["source-backed finding", "freshness", "uncertainty"])
    questions = research_questions or [contract_question(str(question), "SOURCE_BACKED_FINDING", "OFFICIAL_OR_PRIMARY_WHEN_AVAILABLE", str(knowledge_gap))]
    contract = build_contract(requesting_department=department, reason=reason, research_questions=questions,
        overall_evidence_required=evidence, decision_unlocked_by_answers=decision_unlocked_by_answers,
        return_to_department=department, return_to_goal_id=parent_goal_id or objective_id,
        parent_goal_id=parent_goal_id or objective_id, parent_handoff_id=parent_handoff_id,
        requesting_worker="intelligence_fabric", subject_type=subject_type, subject_id=subject_id or objective_id or parent_goal_id,
        priority=priority, due_or_freshness_requirement=freshness_requirement)
    payload = {
        "schema_version": REQUEST_SCHEMA,
        "request_id": _id("research_request", (department, objective_id, question, knowledge_gap)),
        "department": department,
        "objective_id": objective_id,
        "parent_goal_id": parent_goal_id,
        "work_order_id": work_order_id,
        "question": str(question).strip(),
        "knowledge_gap": str(knowledge_gap).strip(),
        "reason_needed": reason,
        "desired_evidence": evidence,
        "risk_consequence": risk_consequence,
        "freshness_requirement": freshness_requirement,
        "created_at": created_at,
        "updated_at": created_at,
        "priority": priority,
        "research_status": "RECEIVED",
        "alpha_status": "NOT_STARTED",
        "result_reference": None,
        "next_action": next_action or "Run bounded Research, then Alpha review.",
        "follow_up_request_id": None,
        "department_resume": "WAITING_FOR_INTELLIGENCE",
        # Systems-facing aliases keep the canonical request readable to
        # operators while preserving the existing V2 field names.
        "requesting_department": department,
        "business_reason": reason,
        "source_requirements": evidence,
        "constraints": {},
        "deadline_if_any": None,
        "status": "RECEIVED",
        "result_artifact": None,
        "alpha_validation_status": "NOT_STARTED",
        "downstream_destination": "department_resume",
        **contract,
        "request_id": contract["research_request_id"],
    }
    return payload


def persist_research_request(request: dict[str, Any]) -> dict[str, Any]:
    if request.get("schema_version") != REQUEST_SCHEMA or request.get("department") not in DEPARTMENTS:
        raise ValueError("invalid-research-request")
    if request.get("research_status") not in REQUEST_STATES:
        raise ValueError("invalid-research-request-state")
    if request.get("decision") == "MORE_RESEARCH_REQUIRED" and not request.get("research_questions"):
        raise ValueError("more-research-required-needs-structured-contract")
    if request.get("schema_version") == REQUEST_SCHEMA:
        validate_contract(request)
    request = {**request, "updated_at": request.get("updated_at") or _now()}
    if request.get("schema_version") == REQUEST_SCHEMA:
        state_alias = str(request.get("research_status") or request.get("status") or "RECEIVED").upper()
        request["status"] = {"RESEARCHING": "IN_RESEARCH", "READY_TO_RESUME": "ANSWERED",
            "FOLLOW_UP_REQUIRED": "PARTIAL", "RESUMED": "RETURNED", "BLOCKED": "PARTIAL",
            "RECEIVED": "OPEN", "ALPHA_REVIEW": "IN_RESEARCH"}.get(state_alias, state_alias if state_alias in {"OPEN", "IN_RESEARCH", "PARTIAL", "ANSWERED", "RETURNED", "CLOSED", "CANCELLED"} else "PARTIAL")
    previous = persistence.get_record("research_requests", request.get("research_request_id") or request.get("request_id"), key="research_request_id")
    if request.get("schema_version") == REQUEST_SCHEMA and not previous:
        persist_contract(request)
    else:
        persistence.append_record("research_requests", request)
        if request.get("schema_version") == REQUEST_SCHEMA:
            try:
                from nexus_agent_platform import supabase_knowledge
                client = supabase_knowledge.supabase
                if client is not None and client.configured():
                    client.rest("PATCH", f"department_research_requests?request_id=eq.{request['research_request_id']}",
                        body={"status": request.get("status", request.get("research_status")), "contract_payload": request,
                              "updated_at": request["updated_at"]}, prefer="return=minimal")
            except Exception:
                pass
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
    claim_text = claim or request["knowledge_gap"]
    verification = assess_evidence(claim_text, [
        {"source": row["source"].get("original_reference"), "source_class": row["source"].get("source_type")}
        for row in evidence_rows
    ], request.get("claim_type") or classify_claim(claim_text))
    claim_specs = [{"claim": claim_text, "claim_type": verification["claim_type"], "confidence": "MEDIUM", "evidence_refs": [row["evidence_id"] for row in evidence_rows], "source_quality": "INTERNAL_OR_PUBLIC", "verification": verification}]
    alpha = alpha_research.run_alpha_research(job, evidence_rows, claim_specs=claim_specs, runtime_root=None)
    pack = alpha["pack"]
    alpha_status = "QUALIFIED" if pack["status"] == "COMPLETE" and pack["findings"] else "MORE_RESEARCH_REQUIRED"
    result_ref = alpha["receipt"]["receipt_id"]
    contract_request = request.get("schema_version") == REQUEST_SCHEMA and bool(request.get("research_questions"))
    updated = {**request, "research_status": "READY_TO_RESUME" if alpha_status == "QUALIFIED" or contract_request else "FOLLOW_UP_REQUIRED", "alpha_status": alpha_status, "result_reference": result_ref, "next_action": "Return the question-level evidence packet to the originating department for a sufficiency decision." if contract_request and alpha_status != "QUALIFIED" else "Resume originating department objective." if alpha_status == "QUALIFIED" else "Investigate a specifically evidenced deficiency through targeted Research.", "status": "ANSWERED" if alpha_status == "QUALIFIED" else "PARTIAL", "result_artifact": result_ref, "alpha_validation_status": alpha_status, "downstream_destination": "department_resume"}
    follow_up = None
    if alpha_status != "QUALIFIED" and not contract_request:
        gap_items = [str(item) for item in pack.get("missing_evidence", []) if str(item).strip()]
        narrowed = [contract_question(f"Resolve the specific evidence gap: {gap}", "SOURCE_BACKED_FACT", "OFFICIAL_OR_PRIMARY_WHEN_AVAILABLE", f"Attributable evidence directly addresses: {gap}") for gap in gap_items[:6]]
        if not narrowed:
            narrowed = [contract_question(f"Cross-check a distinct source for: {request['question']}", "INDEPENDENT_CROSS_CHECK", "INDEPENDENT_PRIMARY_OR_REPUTABLE", "A source independent of prior evidence, or explicit NOT_FOUND")]
        follow_up = build_research_request(department=request["department"], objective_id=request.get("objective_id", ""), parent_goal_id=request.get("parent_goal_id", ""), work_order_id=request.get("work_order_id", ""), question=narrowed[0]["question"], knowledge_gap="Resolve only the listed evidence deficiencies from the preceding Research result.", reason_needed="Alpha found specific unresolved evidence gaps; this request narrows them and preserves the same originating goal.", desired_evidence=[q["question"] for q in narrowed], research_questions=narrowed, decision_unlocked_by_answers=request.get("decision_unlocked_by_answers", "Resume the same originating department goal with the verified answers."), parent_handoff_id=request.get("parent_handoff_id"), priority=request.get("priority", "P2_REVENUE"), freshness_requirement=request.get("freshness_requirement", "CURRENT"))
        existing = [r for r in persistence.read_records("research_requests") if r.get("return_to_goal_id") == follow_up.get("return_to_goal_id") and r.get("schema_version") == "nexus.department-research-request.v1"]
        same_questions = {tuple(sorted(q.get("question", "").lower() for q in r.get("research_questions", []))) for r in existing}
        if tuple(sorted(q["question"].lower() for q in narrowed)) in same_questions:
            follow_up = None
            updated["next_action"] = "DO_NOT_REPEAT_IDENTICAL_RESEARCH; request a new evidence class or proceed with explicit assumptions"
            updated["research_loop_dedupe"] = "IDENTICAL_QUESTION_SET_SUPPRESSED"
        else:
            persist_research_request(follow_up)
            updated["follow_up_request_id"] = follow_up["request_id"]
    persist_research_request(updated)
    evidence_packet = None
    if request.get("schema_version") == REQUEST_SCHEMA and request.get("research_questions"):
        question_results = []
        for item in request["research_questions"]:
            status = "ANSWERED" if len(request["research_questions"]) == 1 and alpha_status == "QUALIFIED" and evidence_rows else "PARTIAL" if evidence_rows else "NOT_FOUND"
            question_results.append({"question_id": item["question_id"], "status": status,
                "answer": "; ".join(str(e.get("content", {}).get("normalized_text_or_markdown", ""))[:500] for e in evidence_rows),
                "confidence": "MEDIUM" if evidence_rows else "UNKNOWN",
                "sources": [e["source"].get("original_reference") for e in evidence_rows],
                "facts": [str(e.get("content", {}).get("normalized_text_or_markdown", ""))[:500] for e in evidence_rows],
                "assumptions": [], "unknowns": [] if status == "ANSWERED" else [item["question"]], "contradictions": []})
        evidence_packet = build_evidence_packet(request, question_results,
            overall_summary="Alpha reviewed the available bounded evidence; question status reflects evidence sufficiency at this stage.",
            remaining_unknowns=[] if alpha_status == "QUALIFIED" else [item["question"] for item in request["research_questions"]],
            recommended_next_action=updated["next_action"])
    return {"request": updated, "alpha": alpha, "alpha_decision": alpha_status, "follow_up": follow_up,
            "evidence_packet": evidence_packet}


def resume_department(request: dict[str, Any], *, next_action: str) -> dict[str, Any]:
    if request.get("research_status") != "READY_TO_RESUME":
        raise ValueError("research-not-ready-to-resume")
    resumed = {**request, "research_status": "RESUMED", "status": "RETURNED", "department_resume": "RESUMED", "next_action": next_action, "resumed_at": _now()}
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
