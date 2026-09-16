#!/usr/bin/env python3
"""Research V2 intelligence contracts.

This is an additive, local-first layer over the proven source processors.  It
keeps discovery, claims, opportunities, plans, experiments, and outcomes as
different objects and gives Alpha an analytical (not veto) contract.  It does
not publish, spend, trade, create work orders, or write Supabase.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Iterable

KNOWLEDGE_MATURITIES = ("EARLY", "DEVELOPING", "MATURE")
INTENTS = (
    "KNOWLEDGE_ACQUISITION", "FACT_VERIFICATION", "PRODUCT_VERIFICATION",
    "BUSINESS_OPPORTUNITY", "BUSINESS_MODEL_RESEARCH", "MARKET_RESEARCH",
    "MARKETING_STRATEGY", "TECHNICAL_RESEARCH", "SOFTWARE_CAPABILITY",
    "COMPETITOR_RESEARCH", "REGULATORY_RESEARCH", "SEO_RESEARCH",
    "TRADING_STRATEGY", "GRANT_RESEARCH", "EXPERIMENT_DESIGN", "SCAM_RISK_REVIEW",
)
DISPOSITIONS = ("ARCHIVE", "MONITOR", "FOLLOW_UP_RESEARCH", "DEEP_RESEARCH", "HIGH_VALUE_REVIEW", "INSUFFICIENT_SOURCE", "STALE", "DUPLICATE")
CLAIM_TYPES = ("PRODUCT_TERM", "CURRENT_RATE", "UNDERWRITING_CLAIM", "REVENUE_CLAIM", "INCOME_CLAIM", "PERFORMANCE_CLAIM", "MARKETING_CLAIM", "TRAFFIC_CLAIM", "COMMUNITY_DATA", "REGULATORY_CLAIM", "TECHNICAL_CAPABILITY", "SOFTWARE_CLAIM", "MARKET_CLAIM", "STRATEGY_CLAIM", "TRADING_CLAIM", "GRANT_CLAIM", "CALCULATED_HYPOTHETICAL", "ANECDOTE", "OPINION")

EVIDENCE_REQUIREMENTS: dict[str, dict[str, Any]] = {
    "PRODUCT_TERM": {"primary_source_classes": ["official_provider_terms"], "secondary_source_classes": ["reputable_review"], "contrary_source_classes": ["regulator_or_user_report"], "recency_requirement": "current_terms", "independence_requirement": "one_primary_plus_contrary_check", "calculation_required": False, "experiment_required": False, "stop_condition": "official_term_or_explicit_unknown"},
    "REGULATORY_CLAIM": {"primary_source_classes": ["regulator", "statute", "authoritative_rule"], "secondary_source_classes": ["qualified_legal_analysis"], "contrary_source_classes": ["enforcement_or_advisory"], "recency_requirement": "current", "independence_requirement": "authoritative", "calculation_required": False, "experiment_required": False, "stop_condition": "authoritative_source_found"},
    "SOFTWARE_CAPABILITY": {"primary_source_classes": ["official_docs", "source_code", "real_local_test"], "secondary_source_classes": ["reputable_technical_report"], "contrary_source_classes": ["issue_or_test_failure"], "recency_requirement": "current_version", "independence_requirement": "implementation_or_test", "calculation_required": False, "experiment_required": True, "stop_condition": "capability_reproduced_or_bounded_failure"},
    "TRADING_CLAIM": {"primary_source_classes": ["historical_market_data", "replication"], "secondary_source_classes": ["research_paper"], "contrary_source_classes": ["out_of_sample_failure"], "recency_requirement": "data_window_declared", "independence_requirement": "chronological_holdout", "calculation_required": True, "experiment_required": True, "stop_condition": "paper_only_result_with_risk"},
    "REVENUE_CLAIM": {"primary_source_classes": ["records", "official_disclosure"], "secondary_source_classes": ["credible_independent_corroboration"], "contrary_source_classes": ["regulator_or_rebuttal"], "recency_requirement": "claim_date_required", "independence_requirement": "independent_corroboration", "calculation_required": True, "experiment_required": False, "stop_condition": "verified_or_explicitly_unverified"},
    "COMMUNITY_DATA": {"primary_source_classes": ["multiple_unrelated_observations"], "secondary_source_classes": ["community_archive"], "contrary_source_classes": ["independent_counterexamples"], "recency_requirement": "dated_observations", "independence_requirement": "multiple_unrelated_sources", "calculation_required": False, "experiment_required": False, "stop_condition": "pattern_or_insufficient_sample"},
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str, value: Any) -> str:
    return f"{prefix}_{hashlib.sha256(repr(value).encode()).hexdigest()[:20]}"


def classify_intents(text: str, *, source_type: str = "", explicit: Iterable[str] | None = None) -> list[str]:
    value = f"{source_type} {text}".lower()
    found = list(dict.fromkeys(x for x in (explicit or []) if x in INTENTS))
    rules = {
        "SCAM_RISK_REVIEW": ("scam", "fraud", "guaranteed returns", "warning"),
        "TRADING_STRATEGY": ("trading", "forex", "backtest", "market strategy"),
        "SEO_RESEARCH": ("seo", "keyword", "serp", "search intent"),
        "SOFTWARE_CAPABILITY": ("github", "software", "api", "library", "repository"),
        "REGULATORY_RESEARCH": ("regulation", "regulator", "compliance", "license"),
        "GRANT_RESEARCH": ("grant", "funding", "lender", "loan"),
        "MARKETING_STRATEGY": ("marketing", "funnel", "lead generation", "campaign"),
        "BUSINESS_MODEL_RESEARCH": ("business model", "subscription", "affiliate", "revenue"),
        "BUSINESS_OPPORTUNITY": ("opportunity", "new business", "customer problem", "monetize"),
        "FACT_VERIFICATION": ("verify", "is it true", "evidence", "claim"),
    }
    for intent, terms in rules.items():
        if any(term in value for term in terms) and intent not in found:
            found.append(intent)
    if not found:
        found.append("KNOWLEDGE_ACQUISITION")
    return found


def knowledge_maturity(prior_items: int, prior_outcomes: int = 0) -> dict[str, Any]:
    maturity = "EARLY" if prior_items == 0 else "DEVELOPING" if prior_outcomes == 0 or prior_items < 5 else "MATURE"
    return {"knowledge_maturity": maturity, "prior_knowledge": "NONE" if prior_items == 0 else "PRESENT", "novelty_status": "BASELINE_FIRST_OBSERVATION" if prior_items == 0 else "COMPARISON_AVAILABLE", "novelty_penalty": 0.0 if prior_items == 0 else None, "no_novelty_penalty": prior_items == 0}


def extract_claims(text: str, source: dict[str, Any]) -> list[dict[str, Any]]:
    sentences = [x.strip() for x in re.split(r"(?<=[.!?])\s+", text or "") if len(x.strip()) >= 35]
    rows = []
    for index, sentence in enumerate(sentences[:30]):
        lower = sentence.lower()
        if any(x in lower for x in ("i think", "in my opinion", "probably")):
            claim_type = "OPINION"
        elif any(x in lower for x in ("revenue", "profit", "made $", "per month")):
            claim_type = "REVENUE_CLAIM"
        elif any(x in lower for x in ("should", "step", "method", "strategy", "use ")):
            claim_type = "STRATEGY_CLAIM"
        elif any(x in lower for x in ("api", "software", "supports", "repository", "library")):
            claim_type = "SOFTWARE_CLAIM"
        elif any(x in lower for x in ("regulator", "legal", "license", "compliance")):
            claim_type = "REGULATORY_CLAIM"
        else:
            claim_type = "MARKET_CLAIM" if any(x in lower for x in ("market", "customer", "demand")) else "ANECDOTE"
        rows.append({"claim_id": _id("claim", (source.get("source_id"), index, sentence)), "claim_text": sentence, "claim_type": claim_type, "source": source.get("source_url"), "source_segment": {"segment_id": index, "excerpt": sentence[:700]}, "materiality": "HIGH" if claim_type in {"REVENUE_CLAIM", "REGULATORY_CLAIM", "PERFORMANCE_CLAIM"} else "MEDIUM", "verifiability": "HIGH" if claim_type in {"PRODUCT_TERM", "REGULATORY_CLAIM", "SOFTWARE_CLAIM"} else "MEDIUM", "related_method": claim_type == "STRATEGY_CLAIM", "related_opportunity": claim_type in {"REVENUE_CLAIM", "MARKET_CLAIM", "STRATEGY_CLAIM"}})
    return rows


def investigation_decision(*, kind: str, specificity: float = 0, materiality: float = 0, decision_relevance: float = 0, verifiability: float = 0, researchability: float = 0, testability: float = 0, upside: float = 0, fatal_constraint: bool = False, scam_risk: str = "NONE") -> dict[str, Any]:
    if scam_risk in {"HIGH", "CONFIRMED"}:
        return {"decision": "SCAM_RISK_REVIEW", "reason": "credible risk requires preservation, evidence review, and execution restriction", "eligible_for_research": True}
    if kind == "KNOWLEDGE":
        return {"decision": "KNOWLEDGE_CAPTURE", "reason": "knowledge acquisition does not require business qualification", "eligible_for_research": True}
    if kind == "OPPORTUNITY":
        viable_signal = sum((researchability, testability, upside, decision_relevance)) / 4
        decision = "RESEARCH_MORE" if fatal_constraint or viable_signal < 0.45 else "BUILD_OPPORTUNITY_THESIS"
    elif kind == "STRATEGY":
        decision = "RESEARCH_MORE" if researchability < 0.35 or testability < 0.35 else "BUILD_STRATEGY_THESIS"
    else:
        decision = "RESEARCH_MORE" if min(specificity, materiality, verifiability) < 0.35 else "KNOWLEDGE_CAPTURE"
    return {"decision": decision, "reason": "investigation routing is action-oriented; immature evidence remains durable", "eligible_for_research": True, "no_universal_rejection_threshold": True}


def opportunity_thesis(*, title: str, customer: str = "UNKNOWN", problem: str = "UNKNOWN", value_proposition: str = "UNKNOWN", revenue_model: str = "UNKNOWN", evidence: list[Any] | None = None) -> dict[str, Any]:
    return {"opportunity_thesis_id": _id("thesis", title), "title": title, "facts": evidence or [], "assumptions": ["customer demand is not yet observed"], "unknowns": ["pricing, CAC, conversion, and operating cost"], "risks": ["market demand and compliance require validation"], "customer": customer, "problem": problem, "value_proposition": value_proposition, "revenue_model": revenue_model, "validation_ideas": ["conduct a bounded no-spend interest test", "interview representative users", "measure qualified response before scaling"]}


def strategy_package(*, title: str, text: str) -> dict[str, Any]:
    return {"strategy_id": _id("strategy", title), "title": title, "required_inputs": [], "steps": [x.strip() for x in re.split(r"(?<=[.!?])\s+", text) if len(x.strip()) > 35][:8] or ["UNKNOWN"], "assumptions": ["source method is descriptive until tested"], "expected_output": "UNKNOWN_UNTIL_TESTED", "mechanism": "UNKNOWN_UNTIL_RESEARCHED", "risks": ["missing rules and selection bias"], "missing_rules": ["sample size, timing, costs, failure criteria"], "test_method": "bounded internal experiment with explicit success and failure criteria"}


def alpha_collaborative_analysis(package: dict[str, Any], *, proposed_action: str = "KNOWLEDGE_CAPTURE") -> dict[str, Any]:
    unknowns = package.get("unknowns") or package.get("material_unknowns") or []
    contradictions = package.get("contradictions") or []
    if package.get("scam_risk") in {"HIGH", "CONFIRMED"}:
        assessment = "SCAM_RISK_ESCALATION"
    elif contradictions:
        assessment = "MATERIAL_CONTRADICTION"
    elif proposed_action in {"KNOWLEDGE_CAPTURE", "LOW_COST_INTERNAL_TEST"}:
        assessment = "SUFFICIENT_FOR_KNOWLEDGE" if not unknowns else "SUFFICIENT_FOR_BOUNDED_TEST"
    elif unknowns:
        assessment = "MORE_RESEARCH_USEFUL"
    else:
        assessment = "SUFFICIENT_FOR_PRELIMINARY_PLAN"
    return {"alpha_assessment": assessment, "facts": package.get("facts", []), "assumptions": package.get("assumptions", []), "material_unknowns": unknowns, "contradictions": contradictions, "missing_information": unknowns, "research_requests": [{"question": x, "owner": "RESEARCH", "bounded": True} for x in unknowns], "proposed_next_action": proposed_action, "gatekeeper": False, "research_may_continue": True}


def action_sufficiency(action: str) -> dict[str, Any]:
    levels = {"KNOWLEDGE_CAPTURE": "LOW", "LOW_COST_INTERNAL_TEST": "MODERATE", "PRELIMINARY_BUSINESS_PLAN": "MEANINGFUL", "CUSTOMER_RECOMMENDATION": "STRONG", "PUBLIC_FACTUAL_CLAIM": "STRONG", "LARGE_CAPITAL_COMMITMENT": "HIGH", "REGULATED_ACTION": "AUTHORITATIVE"}
    return {"proposed_action": action, "required_evidence_level": levels.get(action, "MEANINGFUL"), "universal_threshold": False}


def score_plan(plan: dict[str, Any]) -> dict[str, Any]:
    dimensions = {}
    for key in ("market_demand", "revenue_potential", "margin_potential", "time_to_revenue", "scalability", "automation_potential", "testability"):
        value = plan.get(key, "UNKNOWN")
        dimensions[key] = {"value": value, "basis": plan.get(f"{key}_basis", "not supplied"), "evidence": plan.get(f"{key}_evidence", []), "assumptions": plan.get("assumptions", [])}
    return {"plan_scoring_status": "PARTIAL_UNTIL_OUTCOMES", "dimensions": dimensions, "not_a_raw_idea_score": True}


def source_reputation(source: dict[str, Any]) -> dict[str, Any]:
    false_count = int(source.get("false_or_contradicted_claims", 0) or 0)
    scam = str(source.get("scam_risk", "NONE")).upper()
    status = "QUARANTINED" if scam == "CONFIRMED" else "UNRELIABLE" if false_count >= 3 else "CAUTION" if scam in {"HIGH", "MEDIUM"} or false_count else "NORMAL"
    return {"source_id": source.get("source_id"), "source_type": source.get("source_type"), "channel_or_domain": source.get("channel_or_domain"), "items_processed": source.get("items_processed", 0), "claims_checked": source.get("claims_checked", 0), "supported_claims": source.get("supported_claims", 0), "partially_supported_claims": source.get("partially_supported_claims", 0), "false_or_contradicted_claims": false_count, "material_misrepresentations": source.get("material_misrepresentations", 0), "scam_risk_findings": source.get("scam_risk_findings", 0), "repeat_high_risk_pattern_count": source.get("repeat_high_risk_pattern_count", 0), "source_trust_status": status, "auto_discovery_use": "NO" if status in {"UNRELIABLE", "QUARANTINED"} else "YES", "auto_supporting_evidence_use": "NO" if status in {"UNRELIABLE", "QUARANTINED"} else "YES", "manual_reference_only": status in {"UNRELIABLE", "QUARANTINED"}}


def department_handoff(*, research_summary: Any, plan: Any, sources: Any, provenance: Any, facts: Any, assumptions: Any, unknowns: Any, risks: Any, scam_status: str, recommended_next_action: str, success_criteria: Any, primary_owner: str, secondary_owners: list[str] | None = None) -> dict[str, Any]:
    return {"handoff_id": _id("handoff", (research_summary, primary_owner)), "primary_owner": primary_owner, "secondary_owners": secondary_owners or [], "research_summary": research_summary, "plan": plan, "sources": sources, "provenance": provenance, "facts": facts, "assumptions": assumptions, "unknowns": unknowns, "risks": risks, "scam_status": scam_status, "recommended_next_action": recommended_next_action, "success_criteria": success_criteria, "external_action_allowed": False, "status": "DRAFT_REVIEW_REQUIRED"}


def productivity_metrics(items: list[dict[str, Any]]) -> dict[str, Any]:
    full = [x for x in items if x.get("processing_status") == "FULLY_PROCESSED" and x.get("substantive_findings")]
    return {"sources_discovered": len(items), "sources_acquired": sum(bool(x.get("acquired")) for x in items), "sources_fully_processed": len(full), "duplicates_skipped": sum(x.get("processing_status") == "DUPLICATE_UNCHANGED" for x in items), "summaries_created": sum(bool(x.get("summary_created")) for x in items), "structured_extractions_created": sum(bool(x.get("extraction_created")) for x in items), "substantive_findings_created": len(full), "follow_up_questions_created": sum(len(x.get("follow_up_questions", [])) for x in items), "deep_research_items_created": sum(x.get("disposition") == "DEEP_RESEARCH" for x in items), "processing_failures": sum(str(x.get("processing_status", "")).startswith("FAILED") for x in items), "useful_output_rate": round(len(full) / len(items), 3) if items else 0.0}

