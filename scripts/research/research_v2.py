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
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]

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


SOURCE_CLASS_BY_INTENT = {
    "PRODUCT_VERIFICATION": ("official_provider_source", "product_terms"),
    "REGULATORY_RESEARCH": ("regulator_or_statute", "current_rule"),
    "SOFTWARE_CAPABILITY": ("official_docs_or_source_code", "reproducible_test"),
    "BUSINESS_OPPORTUNITY": ("competitor_and_market_sources", "pricing_demand_regulation"),
    "BUSINESS_MODEL_RESEARCH": ("operator_and_competitor_sources", "model_economics"),
    "MARKETING_STRATEGY": ("funnel_examples_and_platform_docs", "method_benchmark"),
    "SEO_RESEARCH": ("search_and_content_sources", "demand_content_gap"),
}


def select_source_requirements(question: str, intent: str) -> dict[str, Any]:
    source_class, answer_type = SOURCE_CLASS_BY_INTENT.get(intent, ("authoritative_public_web", "factual_context"))
    query = re.sub(r"\s+", " ", f"{question} {answer_type}").strip()[:240]
    return {"question": question, "intent": intent, "what_information_is_missing": question, "source_class": source_class, "query": query, "bounded_max_sources": 3}


def persist_v2_records(records: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    """Append only new V2 identities to the existing governed JSONL store.

    V2 records are immutable projections, but scheduled source processing is
    intentionally repeatable.  Replaying an unchanged source must not inflate
    the question/investigation backlog with the same deterministic IDs.
    """
    scripts_root = str(REPO_ROOT / "scripts")
    if scripts_root not in sys.path:
        sys.path.insert(0, scripts_root)
    from nexus_agent_platform.governed.persistence import append_record, read_records
    identity_keys = {
        "sources": "source_id", "claims": "claim_id", "methods": "method_id",
        "opportunities": "opportunity_id", "questions": "question_id",
        "investigations": "investigation_id", "follow_ups": "follow_up_id",
        "alpha_reviews": "alpha_review_id", "plans": "plan_id",
        "reputations": "source_id", "handoffs": "handoff_id",
        "packages": "research_package_id",
    }
    counts = {}
    for kind, rows in records.items():
        collection = f"research_v2_{kind}"
        counts[kind] = 0
        identity_key = identity_keys.get(kind)
        existing = set()
        if identity_key:
            existing = {str(row.get(identity_key)) for row in read_records(collection) if row.get(identity_key) is not None}
        for row in rows:
            identity = str(row.get(identity_key)) if identity_key and row.get(identity_key) is not None else None
            if identity and identity in existing:
                continue
            append_record(collection, {"schema_version": "nexus.research-v2.1", "recorded_at": _now(), **row})
            if identity:
                existing.add(identity)
            counts[kind] += 1
    return counts


def research_package(*, source: dict[str, Any], claims: list[dict[str, Any]], evidence: list[dict[str, Any]], questions: list[dict[str, Any]], alpha_review: dict[str, Any] | None = None, opportunity: dict[str, Any] | None = None, strategy: dict[str, Any] | None = None) -> dict[str, Any]:
    unknowns = [q.get("question") for q in questions if q.get("status", "OPEN") != "RESOLVED"]
    package = {"research_package_id": _id("package", source.get("source_id")), "source": source, "claims": claims, "evidence": evidence, "questions": questions, "facts": [x.get("claim_text") for x in claims if x.get("verification_status") == "SUPPORTED"], "assumptions": ["observed source evidence may not represent market-wide demand"], "unknowns": unknowns or ["Nexus outcome data is not yet available"], "risks": ["pricing, demand, compliance, and operating constraints require bounded validation"], "opportunity_thesis": opportunity, "strategy_thesis": strategy, "alpha_review": alpha_review, "status": "MATERIAL_UNKNOWNS_REMAIN" if unknowns else "ENOUGH_FOR_PRELIMINARY_PLAN"}
    return package


def synthesize_plan(package: dict[str, Any], *, owner: str = "EXECUTIVE_PLANNING") -> dict[str, Any]:
    thesis = package.get("opportunity_thesis") or {}
    plan = {"plan_id": _id("plan", package.get("research_package_id")), "plan_type": "PRELIMINARY_RESEARCH_PLAN", "plan_status": "DRAFT_REVIEW_REQUIRED", "objective": package.get("source", {}).get("source_title", "Research subject"), "customer": thesis.get("customer", "UNKNOWN"), "offer": thesis.get("value_proposition", "UNKNOWN"), "revenue_model": thesis.get("revenue_model", "UNKNOWN"), "market_entry": "bounded no-spend validation", "go_to_market": "local search, referrals, and partnerships are hypotheses; performance UNKNOWN", "operating_model": "UNKNOWN_UNTIL_TESTED", "technology_requirements": "UNKNOWN", "automation_opportunities": ["lead intake and scheduling candidate"], "human_requirements": ["operator and customer support requirements UNKNOWN"], "regulatory_requirements": ["identify applicable local/state requirements before execution"], "estimated_costs": "UNKNOWN_UNTIL_VALIDATION", "estimated_revenue_mechanism": thesis.get("revenue_model", "UNKNOWN"), "validation_steps": thesis.get("validation_ideas", []), "key_assumptions": package.get("assumptions", []), "risks": package.get("risks", []), "success_criteria": ["qualified interest and measured unit-economics inputs"], "next_actions": ["resolve highest-value unknowns", "prepare internal validation brief"], "primary_owner": owner}
    plan["score"] = score_plan({"assumptions": plan["key_assumptions"], "market_demand": "UNKNOWN", "market_demand_basis": "no direct demand data", "market_demand_evidence": package.get("evidence", [])})
    return plan


def outcome_record(*, entity_id: str, outcome_type: str, metrics: dict[str, Any], evidence: list[Any] | None = None) -> dict[str, Any]:
    return {"outcome_id": _id("outcome", (entity_id, outcome_type, metrics)), "entity_id": entity_id, "outcome_type": outcome_type, "evidence_class": "NEXUS_OBSERVED_OUTCOME", "metrics": metrics, "evidence": evidence or [], "status": "OBSERVED"}


def compare_knowledge(*, new_item: dict[str, Any], prior_items: list[dict[str, Any]]) -> dict[str, Any]:
    """Create a qualitative comparison; never invents a novelty number."""
    prior_text = " ".join(str(x.get("text") or x.get("summary") or x.get("title") or "") for x in prior_items).lower()
    new_text = str(new_item.get("text") or new_item.get("summary") or new_item.get("title") or "")
    terms = [x for x in re.findall(r"[a-z][a-z0-9-]{4,}", new_text.lower()) if x not in {"about", "which", "there", "their", "these", "would", "could"}]
    shared = sorted(set(terms) & set(re.findall(r"[a-z][a-z0-9-]{4,}", prior_text)))[:20]
    status = "BASELINE_FIRST_OBSERVATION" if not prior_items else "ADDS_NEW_INFORMATION" if len(shared) < max(2, len(set(terms)) // 5) else "OVERLAPPING"
    return {"comparison_id": _id("comparison", (new_item.get("source_id"), [x.get("source_id") for x in prior_items])), "new_item": new_item.get("source_id") or new_item.get("title"), "prior_items": [x.get("source_id") or x.get("title") for x in prior_items], "shared_facts": shared, "new_facts": [x for x in terms if x not in shared][:20], "shared_methods": [], "new_methods": [], "contradictions": [], "different_assumptions": [], "source_quality_differences": [], "temporal_differences": [], "updated_understanding": "New source is compared qualitatively against retained Research text; numeric novelty is intentionally not assigned.", "novelty_status": status, "no_novelty_number": True}


def parent_links_for_item(item: dict[str, Any]) -> dict[str, list[str]]:
    """Resolve the current V2 objects that requested evidence for a source.

    Source processors remain unaware of this relationship.  The worker adds
    these exact links after choosing its concrete source, and the shared V2
    integration uses them for idempotent state progression.
    """
    source_id = str(item.get("source_id") or "")
    links = {"question_ids": [], "followup_ids": [], "investigation_ids": [], "thesis_ids": []}
    if not source_id:
        return links
    try:
        from nexus_agent_platform.governed.persistence import read_records
        for collection, key, output in (
            ("research_v2_questions", "question_id", "question_ids"),
            ("research_v2_follow_ups", "follow_up_id", "followup_ids"),
            ("research_v2_investigations", "investigation_id", "investigation_ids"),
            ("research_v2_opportunities", "opportunity_id", "thesis_ids"),
            ("research_v2_strategies", "strategy_id", "thesis_ids"),
        ):
            for row in read_records(collection):
                if str(row.get("source_id") or "") == source_id and row.get(key) is not None:
                    if str(row.get("status", "")).upper() not in {"COMPLETED", "RESOLVED", "ARCHIVED", "REJECTED"}:
                        value = str(row[key])
                        if value not in links[output]:
                            links[output].append(value)
    except Exception:
        # Missing optional governed state must not stop source acquisition.
        pass
    return links


def _append_progression_state(collection: str, identity_key: str, identity: str, package_id: str, payload: dict[str, Any]) -> bool:
    from nexus_agent_platform.governed.persistence import append_record, get_record
    latest = get_record(collection, identity, key=identity_key)
    if latest and latest.get("last_evidence_package_id") == package_id:
        return False
    append_record(collection, {"schema_version": "nexus.research-v2.1", "recorded_at": _now(), identity_key: identity, "last_evidence_package_id": package_id, **payload})
    return True


def progress_after_package(item: dict[str, Any], package: dict[str, Any], result: dict[str, Any], links: dict[str, list[str]]) -> dict[str, Any]:
    """Advance evidence-requesting objects after package storage.

    Updates are append-only projections and keyed by package ID, so retries
    cannot resolve, advance, or compare the same package twice.
    """
    from nexus_agent_platform.governed.persistence import append_record, get_record, read_records
    package_id = str(package["research_package_id"])
    status = str(result.get("processing_status", "FULLY_PROCESSED"))
    evidence_state = "MORE_RESEARCH_REQUIRED" if status == "FULLY_PROCESSED" else "INSUFFICIENT"
    changed = {"questions": 0, "follow_ups": 0, "investigations": 0, "theses": 0, "comparisons": 0}
    for question_id in links.get("question_ids", []):
        if _append_progression_state("research_v2_questions", "question_id", question_id, package_id, {"status": evidence_state, "source_id": item.get("source_id"), "evidence_found": bool(result.get("summary_created") or result.get("structured_data")), "sufficient_to_resolve": False, "next_action": "select independent authoritative evidence"}):
            changed["questions"] += 1
    for followup_id in links.get("followup_ids", []):
        if _append_progression_state("research_v2_follow_ups", "follow_up_id", followup_id, package_id, {"status": "MORE_RESEARCH_REQUIRED", "source_id": item.get("source_id"), "result": evidence_state, "remaining_unknowns": package.get("unknowns", [])}):
            changed["follow_ups"] += 1
    for investigation_id in links.get("investigation_ids", []):
        if _append_progression_state("research_v2_investigations", "investigation_id", investigation_id, package_id, {"status": "RESEARCH_MORE", "source_id": item.get("source_id"), "progression_event": "EVIDENCE_ATTACHED", "open_gaps_after": package.get("unknowns", []), "next_action": "select independent evidence for remaining gaps"}):
            changed["investigations"] += 1
    for thesis_id in links.get("thesis_ids", []):
        if _append_progression_state("research_v2_opportunities", "opportunity_id", thesis_id, package_id, {"status": "THESIS_ONLY_NO_EXECUTION", "source_id": item.get("source_id"), "progression_event": "EVIDENCE_ATTACHED", "next_action": "evaluate evidence against thesis gaps"}):
            changed["theses"] += 1
    # Compare against retained V2 source text when a real prior item exists.
    prior = [row for row in read_records("research_v2_sources") if str(row.get("source_id")) != str(item.get("source_id"))]
    if prior:
        comparison = compare_knowledge(new_item={"source_id": item.get("source_id"), "title": item.get("title"), "text": " ".join(str(x) for x in (result.get("key_findings") or result.get("executive_summary") or result.get("title") or "") if x)}, prior_items=prior[:20])
        if not get_record("research_v2_comparisons", comparison["comparison_id"], key="comparison_id"):
            append_record("research_v2_comparisons", {"schema_version": "nexus.research-v2.1", "recorded_at": _now(), **comparison, "evidence_package_id": package_id})
            changed["comparisons"] += 1
    return {"package_id": package_id, "linked": links, "state_changes": changed}


def integrate_scheduled_result(item: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """Project a completed source artifact into V2's governed records.

    The source processor remains authoritative for acquisition and artifact
    formats.  This projection is intentionally additive and skips shallow
    metadata-only results as substantive intelligence.
    """
    source = {"source_id": item.get("source_id"), "source_type": item.get("source_type"), "source_url": item.get("source_url"), "source_title": item.get("title") or result.get("title"), "source_author_or_channel": item.get("author") or result.get("channel"), "processing_status": result.get("processing_status"), "source_observation": True}
    substantive = result.get("transcript_acquired") or result.get("summary_created") or result.get("key_findings") or result.get("structured_data")
    evidence_text = " ".join(str(x) for x in (result.get("key_findings") or result.get("executive_summary") or result.get("title") or "") if x)
    source["source_observation"] = not bool(substantive)
    source["text"] = evidence_text
    claims = extract_claims(evidence_text, source) if substantive and len(evidence_text) >= 35 else []
    intent_text = f"{item.get('category', '')} {item.get('title', '')}"
    intents = classify_intents(intent_text, source_type=str(item.get("source_type", "")))
    questions = []
    for intent in intents[:3]:
        requirements = select_source_requirements("Which material claims or unknowns require additional evidence?", intent)
        questions.append({"question_id": _id("question", (source["source_id"], intent)), "source_id": source["source_id"], "question": requirements["question"], "intent": intent, "source_class": requirements["source_class"], "query": requirements["query"], "status": "OPEN"})
    investigation_id = str(item.get("objective_id") or _id("investigation", source["source_id"]))
    records = {"sources": [{**source, "research_intents": intents, "objective_id": item.get("objective_id"), "investigation_id": investigation_id}], "claims": claims, "questions": questions, "investigations": [{"investigation_id": investigation_id, "objective_id": item.get("objective_id"), "source_id": source["source_id"], "status": "ACTIVE" if substantive else "ENOUGH_FOR_KNOWLEDGE", "decision": "KNOWLEDGE_CAPTURE" if not substantive else "RESEARCH_MORE", "materiality": "MEDIUM" if substantive else "LOW", "last_activity": _now(), "next_action": "answer_source_requirements" if substantive else "retain_knowledge", "research_intents": intents, "source_requirements": [select_source_requirements(q["question"], q["intent"]) for q in questions], "research_continues": bool(substantive)}], "follow_ups": []}
    counts = persist_v2_records(records)
    package = research_package(source=source, claims=claims, evidence=[{"source_id": source.get("source_id"), "text": evidence_text, "status": result.get("processing_status")}], questions=questions)
    package["objective_id"] = item.get("objective_id")
    package["investigation_id"] = investigation_id
    persist_v2_records({"packages": [package]})
    links = item.get("v2_parent_links") or {"question_ids": [], "followup_ids": [], "investigation_ids": [investigation_id], "thesis_ids": []}
    progression = progress_after_package(item, package, result, links) if not bool(result.get("duplicate_unchanged")) else {"package_id": package["research_package_id"], "linked": links, "state_changes": {}}
    return {"v2_integrated": True, "substantive_intelligence": bool(substantive), "research_intents": intents, "claims_created": len(claims), "questions_created": len(questions), "record_counts": counts, "research_package_id": package["research_package_id"], "progression": progression, "comparison_created": progression["state_changes"].get("comparisons", 0)}
