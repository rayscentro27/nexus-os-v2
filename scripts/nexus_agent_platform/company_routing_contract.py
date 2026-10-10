"""Work-first department routing and safe business-review helpers."""
from __future__ import annotations
import re
from typing import Any, Mapping

ROUTES = (
    ("TRADING", re.compile(r"\b(trading|strategy|indicator|entry signal|exit signal|backtest|market setup)\b", re.I)),
    ("LABS", re.compile(r"\b(technology|capability|experiment|benchmark|prototype|model evaluation)\b", re.I)),
    ("SYSTEMS", re.compile(r"\b(incident|repair service|restore|operational capability|production health)\b", re.I)),
    ("COMPLIANCE", re.compile(r"\b(claim|disclosure|compliance|guaranteed|eligibility wording)\b", re.I)),
    ("FINANCE", re.compile(r"\b(economics|unit economics|commission|payout|break-even|gross margin|acquisition cost)\b", re.I)),
    ("CREATIVE", re.compile(r"\b(asset production|produce asset|image|video asset|typography|visual execution)\b", re.I)),
    ("MARKETING", re.compile(r"\b(campaign strategy|audience segmentation|positioning|channel strategy|funnel|content plan)\b", re.I)),
    ("OPPORTUNITIES", re.compile(r"\b(commercial opportunity|business opportunity|affiliate opportunity|revenue model|customer need|customer problem)\b", re.I)),
    ("RESEARCH", re.compile(r"\b(research|verify|source evidence|trend evidence|competitor evidence|audience evidence)\b", re.I)),
)

def route_required_work(*, work_required: str, department_mission: str = "", current_goal: str = "", handoff_evidence: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Pick the owner of the requested decision, using goal/evidence to disambiguate."""
    text = " ".join((work_required, department_mission, current_goal, str(dict(handoff_evidence or {}))))
    matches = [department for department, pattern in ROUTES if pattern.search(text)]
    # Research is the owner of evidence gaps; commercial evaluation stays with Opportunities.
    if any(term in text.lower() for term in ("missing evidence", "unanswered question", "verify source", "research follow-up")):
        department = "RESEARCH"
    elif any(term in text.lower() for term in ("commercial opportunity", "business opportunity", "affiliate opportunity", "revenue model")):
        department = "OPPORTUNITIES"
    else:
        department = matches[0] if matches else "UNRESOLVED"
    return {"owner_department": department, "matched_domains": matches, "basis": {"work_required": work_required, "department_mission": department_mission, "current_goal": current_goal, "evidence_present": bool(handoff_evidence)}, "next_action": f"{department}_EVALUATE_REQUIRED_WORK" if department != "UNRESOLVED" else "CLARIFY_WORK_REQUIRED"}

def review_opportunity_economics(packet: Mapping[str, Any]) -> dict[str, Any]:
    from nexus_agent_platform.research_followup_contract import build_contract, question as make_question
    required = ("revenue_model", "payout_or_price", "recurring_revenue", "operating_costs", "acquisition_assumptions")
    missing = [key for key in required if packet.get(key) in (None, "", [])]
    if missing:
        context = packet.get("research_context") if isinstance(packet.get("research_context"), Mapping) else {}
        goal_id = str(context.get("return_to_goal_id") or packet.get("goal_id") or "")
        if not goal_id:
            raise ValueError("MORE_ECONOMIC_RESEARCH_REQUIRED requires originating return_to_goal_id and parent_handoff_id context")
        questions = [make_question(f"Find source-backed evidence for missing Finance input: {field}", "ECONOMIC_INPUT", "OFFICIAL_OR_INTERNAL_SOURCE", f"A dated attributable source or explicit NOT_FOUND is required for {field}.") for field in missing]
        contract = build_contract(requesting_department="FINANCE", reason="Required economic inputs are absent or unverified.",
            research_questions=questions, overall_evidence_required=missing,
            decision_unlocked_by_answers="Finance resumes the same opportunity goal and chooses an evidence-based economic decision.",
            return_to_department="FINANCE", return_to_goal_id=goal_id, parent_goal_id=goal_id,
            parent_handoff_id=context.get("parent_handoff_id"), requesting_worker="company_routing_contract",
            subject_type="OPPORTUNITY", subject_id=str(packet.get("opportunity_id") or goal_id), priority="P1",
            due_or_freshness_requirement="CURRENT")
        return {"decision": "MORE_ECONOMIC_RESEARCH_REQUIRED", "missing_evidence": missing, "assumptions": packet.get("assumptions", []), "next_action": "RESEARCH_OR_FINANCE_FILL_MISSING_ECONOMIC_EVIDENCE", "research_followup_contract": contract}
    # Never infer profitability from incomplete arithmetic or unlabelled assumptions.
    if packet.get("evidence_status") != "VERIFIED":
        context = packet.get("research_context") if isinstance(packet.get("research_context"), Mapping) else {}
        goal_id = str(context.get("return_to_goal_id") or packet.get("goal_id") or "")
        if not goal_id:
            raise ValueError("MORE_ECONOMIC_RESEARCH_REQUIRED requires originating return_to_goal_id and parent_handoff_id context")
        gap = "verified source for economic inputs"
        contract = build_contract(requesting_department="FINANCE", reason="Economic values are present but lack verified provenance.",
            research_questions=[make_question("Verify the source and period for each economic input used in the opportunity model.", "VERIFIED_ECONOMIC_PROVENANCE", "OFFICIAL_OR_INTERNAL_SOURCE", "Each material input must link to an attributable, dated source.")],
            overall_evidence_required=[gap], decision_unlocked_by_answers="Finance resumes the same opportunity goal with verified input provenance.",
            return_to_department="FINANCE", return_to_goal_id=goal_id, parent_goal_id=goal_id,
            parent_handoff_id=context.get("parent_handoff_id"), requesting_worker="company_routing_contract",
            subject_type="OPPORTUNITY", subject_id=str(packet.get("opportunity_id") or goal_id), priority="P1", due_or_freshness_requirement="CURRENT")
        return {"decision": "MORE_ECONOMIC_RESEARCH_REQUIRED", "missing_evidence": [gap], "next_action": "VERIFY_ECONOMIC_INPUTS_BEFORE_MARKETING_PLAN", "research_followup_contract": contract}
    return {"decision": "ECONOMICS_SUPPORTED" if packet.get("break_even_supported") is True else "ECONOMICS_NOT_SUPPORTED", "missing_evidence": [], "next_action": "ROUTE_TO_MARKETING" if packet.get("break_even_supported") is True else "REVISE_MODEL_OR_RESEARCH_ALTERNATIVES"}

def repair_claim_preserving_process(phrase: str, *, supported_process_facts: list[str]) -> dict[str, Any]:
    normalized = phrase
    if re.search(r"guaranteed\s+funding", phrase, re.I):
        normalized = "Funding readiness starts with a business-profile review, organized documentation, and lender matching. No funding outcome is guaranteed."
    elif re.search(r"guaranteed", phrase, re.I):
        normalized = re.sub(r"\bguaranteed\b", "designed to support", phrase, flags=re.I)
    return {"original_phrase": phrase, "decision": "REVISE_WORDING_CONTINUE_CAMPAIGN" if normalized != phrase else "NO_REPAIR_NEEDED", "repaired_wording": normalized, "preserved_supported_facts": list(supported_process_facts), "campaign_status": "ACTIVE", "next_action": "CLAIM_REVIEW_REPAIRED_COPY"}

def route_out_of_scope_issue(*, detecting_department: str, issue: str) -> dict[str, Any]:
    routed=route_required_work(work_required=issue,department_mission="",current_goal="",handoff_evidence={})
    return {"detected_by":detecting_department,"issue":issue,"decision_owner":routed["owner_department"],"flag_only":True,"non_dependent_work_continues":True,"next_action":routed["next_action"]}
