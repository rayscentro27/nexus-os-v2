"""Shared parent-case completion and Ray decision contracts.

Department tasks can add evidence, but only the company case contract can make
a proposal decision-ready. This module intentionally adds no second datastore.
"""
from __future__ import annotations

from typing import Any

CONTRACTS: dict[str, dict[str, Any]] = {
    "TRADING_INTELLIGENCE": {"ready_status": "READY_FOR_RAY_TOURNAMENT_REVIEW", "required_fields": [
        "explicit_deterministic_rules", "source_supported_rules", "nexus_assumptions", "no_lookahead_assessment",
        "markets", "timeframes", "risk_model", "backtest_results", "sample_assessment", "robustness_results",
        "failure_regimes", "drawdown", "expectancy", "profit_factor", "remaining_assumptions", "final_recommendation"]},
    "BUSINESS_OPPORTUNITIES": {"ready_status": "READY_FOR_RAY_BUSINESS_REVIEW", "required_fields": [
        "customer_problem", "market_evidence", "demand_evidence", "competitor_evidence", "business_model",
        "business_plan", "offer", "mvp", "operating_model", "startup_cost", "monthly_operating_cost",
        "revenue_assumptions", "economic_model", "target_customer", "positioning", "acquisition_channels",
        "measurement_plan", "creative_plan", "technical_feasibility", "risks", "final_recommendation"]},
    "TECHNOLOGY_FOR_NEXUS": {"ready_status": "READY_FOR_RAY_UPGRADE_REVIEW", "required_fields": [
        "nexus_problem", "research_evidence", "systems_compatibility", "security_review", "labs_result",
        "finance_analysis", "expected_nexus_benefit", "integration_risk", "rollback_plan", "final_recommendation"]},
    "SYSTEMS": {"ready_status": "READY_FOR_RAY_SYSTEMS_REVIEW", "required_fields": [
        "failure_problem", "reliability_evidence", "technical_plan", "security_review", "rollback_plan", "final_recommendation"]},
    "OTHER": {"ready_status": "READY_FOR_RAY_REVIEW", "required_fields": ["objective", "success_criteria", "final_recommendation"]},
}

RAY_DECISION_STATES = {"READY_FOR_RAY_REVIEW", "AWAITING_RAY_INFORMATION", "APPROVED", "DENIED", "CHANGES_REQUESTED"}


def completion_gaps(case: dict[str, Any]) -> list[str]:
    family = str(case.get("objective_family") or "OTHER").upper()
    contract = CONTRACTS.get(family, CONTRACTS["OTHER"])
    gaps = [field for field in ["objective", "success_criteria", *contract["required_fields"]]
            if case.get(field) in (None, "", [], {})]
    gaps.extend("open_questions" for question in case.get("open_questions") or []
                if str(question.get("answer_status") or "OPEN").upper() == "OPEN")
    criteria = list(case.get("success_criteria") or [])
    results = {str(row.get("criterion") or ""): row for row in case.get("success_criteria_results") or []}
    if criteria and any(str(results.get(str(item), {}).get("status") or "OPEN").upper() != "SATISFIED"
                        for item in criteria):
        gaps.append("success_criteria_not_satisfied")
    if not case.get("final_recommendation") and not case.get("recommendations"):
        gaps.append("final_recommendation")
    recommendation = str(case.get("final_recommendation") or
        ((case.get("recommendations") or [{}])[-1].get("recommendation") or "")).upper()
    if recommendation == "GET_MORE_EVIDENCE":
        gaps.append("recommendation_still_requires_more_evidence")
    return sorted(set(gaps))


def decision_packet(case: dict[str, Any]) -> dict[str, Any]:
    gaps = completion_gaps(case)
    return {
        "case_id": case.get("case_id"), "case_type": case.get("objective_family"),
        "title": case.get("title") or case.get("objective"), "objective": case.get("objective"),
        "executive_summary": case.get("executive_summary"), "why_nexus_reviewed_this": case.get("case_selection_reason"),
        "problem": case.get("customer_problem") or case.get("nexus_problem"),
        "key_evidence": case.get("evidence") or case.get("findings") or [],
        "work_completed_by_department": case.get("department_results") or [],
        "research_summary": case.get("research_summary"), "financial_analysis": case.get("financial_analysis"),
        "test_results": case.get("experiment_results") or [], "marketing_plan": case.get("marketing_plan"),
        "creative_plan": case.get("creative_plan"), "technical_plan": case.get("technical_plan"),
        "risks": case.get("risk_analysis") or [], "unresolved_assumptions": case.get("open_questions") or [],
        "expected_cost": {"initial": case.get("expected_initial_cost"), "operating": case.get("expected_operating_cost")},
        "expected_value": case.get("expected_revenue_or_value"), "what_happens_if_approved": case.get("approval_plan"),
        "what_happens_if_not_approved": case.get("decline_plan"),
        "nexus_recommendation": case.get("final_recommendation") or (case.get("recommendations") or [{}])[-1].get("recommendation"),
        "recommendation_reason": case.get("recommendation_reason") or (case.get("recommendations") or [{}])[-1].get("recommendation_reason"),
        "recommendation_confidence": case.get("recommendation_confidence") or (case.get("recommendations") or [{}])[-1].get("confidence"),
        "completion_gaps": gaps, "ray_decision_status": "READY_FOR_RAY_REVIEW" if not gaps else "NOT_READY",
    }
