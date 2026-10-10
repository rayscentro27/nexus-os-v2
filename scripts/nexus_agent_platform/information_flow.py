"""Bidirectional Research/Alpha/department information flow.

Information delivery is separate from governed action authorization. This
module creates durable domain information and learning records without
granting spend, client, security, compliance, or external-write authority.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from nexus_agent_platform.governed import persistence
from nexus_agent_platform.research_work_queue import default_queue
from nexus_agent_platform.research_followup_contract import build_contract, question as contract_question, persist_contract


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _text(*values: Any) -> str:
    return " ".join(str(value or "") for value in values).lower()


def domain_department(item: dict[str, Any], result: dict[str, Any] | None = None) -> tuple[str | None, str]:
    text = _text(item.get("category"), item.get("lane_id"), item.get("objective_id"),
                 item.get("title"), item.get("source_type"), item.get("source_url"),
                 (result or {}).get("theme"), (result or {}).get("category"))
    if any(token in text for token in ("funding", "lender", "sba", "credit", "credit_repair")):
        return "CLYDE_FUNDING", "funding/credit domain"
    if any(token in text for token in ("trading", "tradingview", "strategy", "indicator", "forex")):
        return "TRADING", "trading domain"
    if any(token in text for token in ("github", "systems", "system", "repo", "runtime", "api", "model", "tool")):
        return "SYSTEMS", "systems/tooling domain"
    if any(token in text for token in ("marketing", "customer", "seo", "demand", "audience", "campaign")):
        return "MARKETING", "customer/acquisition domain"
    if any(token in text for token in ("finance", "cost", "budget", "afford")):
        return "FINANCE", "cost/affordability domain"
    if any(token in text for token in ("business", "opportunity", "affiliate", "monetiz")):
        return "BUSINESS_OPPORTUNITY", "business-opportunity domain"
    target = str(item.get("department_target") or "").upper().strip()
    return (target, "requesting department") if target else (None, "domain unresolved")


def route_information(*, item: dict[str, Any], result: dict[str, Any], alpha: dict[str, Any] | None = None) -> dict[str, Any]:
    department, reason = domain_department(item, result)
    research_id = str(item.get("objective_id") or item.get("parent_finding_id") or result.get("research_id") or item.get("work_id") or "")
    if not department or not research_id:
        return {"status": "UNRESOLVED", "department": department, "reason": reason}
    alpha = alpha or {}
    key = f"{research_id}:{department}"
    prior = next((row for row in persistence.read_records("department_information_items") if row.get("idempotency_key") == key), None)
    if prior:
        return {"status": "ALREADY_ROUTED", "department": department, "department_information_item_id": prior.get("department_information_item_id")}
    item_id = persistence.new_id("dept_info")
    record = {
        "schema_version": "nexus.department-information-item.v1", "department_information_item_id": item_id,
        "idempotency_key": key, "research_id": research_id, "canonical_finding_id": research_id, "work_id": item.get("work_id"),
        "objective_id": item.get("objective_id"), "department": department,
        "source": {"source_id": item.get("source_id"), "source_type": item.get("source_type"), "source_url": item.get("source_url"), "title": item.get("title")},
        "research_question": item.get("research_question") or item.get("title"),
        "finding": result.get("v2") or result, "claims": result.get("claims") or [],
        "evidence": result.get("evidence") or result.get("evidence_refs") or [],
        "contradictions": result.get("contradictions") or [], "unknowns": result.get("unknowns") or result.get("missing_evidence") or [],
        "confidence": result.get("confidence") or result.get("evidence_confidence") or "UNKNOWN",
        "research_opinion": result.get("ai_interpretation") or result.get("disposition"),
        "alpha_opinion": alpha.get("decision") or alpha.get("status") or "NOT_REVIEWED",
        "alpha_receipt_id": alpha.get("receipt_id"), "alpha_concerns": alpha.get("reason") or alpha.get("error"),
        "alpha_recommended_followup": alpha.get("followup_work_id"), "information_routing": "DELIVERED",
        "action_authorization": "UNAUTHORIZED_PENDING_DOMAIN_REVIEW", "external_action_allowed": False,
        "routing_reason": reason, "department_status": "INFORMATION_RECEIVED",
        "current_pipeline_stage": "DEPARTMENT_INFORMATION", "created_at": _now(),
    }
    persistence.append_record("department_information_items", record)
    return {"status": "DELIVERED", "department": department, "department_information_item_id": item_id,
            "action_authorization": record["action_authorization"]}


def record_department_result(*, department: str, research_id: str, alpha_receipt_id: str | None,
                             work_order_id: str, experiment: str, result: str, success_failure: str,
                             lesson: str, what_changed: str = "", next_decision_rule: str = "",
                             new_research_question: str = "") -> dict[str, Any]:
    learning_id = persistence.new_id("learning")
    persistence.append_record("organizational_learning", {
        "schema_version": "nexus.organizational-learning.v1", "learning_id": learning_id,
        "source_research_id": research_id, "alpha_receipt_id": alpha_receipt_id, "department": department,
        "work_order_id": work_order_id, "experiment": experiment, "result": result,
        "success_failure": success_failure, "lesson": lesson, "what_changed": what_changed,
        "next_decision_rule": next_decision_rule, "created_at": _now(),
    })
    persistence.append_record("alpha_outcomes", {
        "schema_version": "nexus.alpha-department-feedback.v1", "outcome_id": persistence.new_id("alpha_feedback"),
        "research_id": research_id, "alpha_receipt_id": alpha_receipt_id, "department": department,
        "work_order_id": work_order_id, "result": result, "success_failure": success_failure,
        "lesson": lesson, "status": "DEPARTMENT_FEEDBACK", "created_at": _now(),
    })
    followup = None
    if new_research_question:
        request_id = persistence.new_id("dept_research")
        contract = build_contract(requesting_department=department,
            reason=f"Department result {learning_id} identified an evidence question required for the next decision.",
            research_questions=[contract_question(new_research_question, "SOURCE_BACKED_FINDING", "OFFICIAL_OR_PRIMARY_WHEN_AVAILABLE", "Attributable source evidence or explicit NOT_FOUND")],
            overall_evidence_required=[new_research_question],
            decision_unlocked_by_answers=f"Resume department {department} work on research item {research_id} with the answer.",
            return_to_department=department, return_to_goal_id=research_id, parent_goal_id=research_id,
            requesting_worker="department_result_feedback", subject_type="RESEARCH_ITEM", subject_id=research_id,
            research_request_id=request_id)
        persist_contract(contract)
        persistence.append_record("department_research_requests", {
            "schema_version": "nexus.department-research-request.v1", "request_id": request_id,
            "research_request_id": request_id, "requesting_department": department,
            "question": new_research_question, "contract_payload": contract,
            "source_research_id": research_id, "learning_id": learning_id, "status": "QUEUED", "created_at": _now(),
        })
        followup = default_queue().enqueue(work_id=f"department-followup:{request_id}", work_class="ASSIGNED", priority=50,
                                           lane_id="DEPARTMENT_FOLLOWUP", source_type="WEB_PAGE", source_id=request_id,
                                           requested_by=department, parent_request_id=request_id, objective_id=research_id,
                                           title=new_research_question, selection_reason="department_learning_followup")
    return {"learning_id": learning_id, "followup": followup}
