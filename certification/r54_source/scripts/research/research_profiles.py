#!/usr/bin/env python3
"""Deterministic Research profiles for NotebookLM-backed source processing.

A profile is data, not a prompt-engineering experiment.  It fixes four things
before any NotebookLM call happens: which notebook pool the source lands in,
the exact extraction schema, the department destinations, and the deterministic
quality gate.  Classification is keyword/exact-match and runs in ordinary
Python so the same title always maps to the same profile.

Nothing here decides whether work continues.  The adapter and the existing
Research work queue own claim/retry/wait/complete/fail/handoff.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

EXTRACTION_JSON_INSTRUCTION = (
    "Return strict JSON only. No prose before or after the JSON object. "
    "Do not infer. If a field is not stated in the source, use null for scalars "
    "and an empty list for arrays. Never fill a field from general knowledge."
)

GROUNDING_FIELD = "verbatim_support_quotes"

GROUNDING_INSTRUCTION = (
    f'Include one extra key "{GROUNDING_FIELD}" whose value is an array of 3 to 6 short '
    "quotes copied word-for-word from the source that prove the extracted values. "
    "Quotes only. No paraphrase. No commentary about the quotes."
)

TRADING_PARENT_PROFILE = "trading"
TRADING_PROFILE_IDS = {"trading_general", "forex_strategy"}
TRADING_SUBTYPE_FIELDS: dict[str, dict[str, type]] = {
    "strategy": {k: list for k in ("market_instrument", "indicators", "indicator_settings", "entry_rules", "exit_rules", "trend_filters", "market_conditions", "discretionary_elements", "backtestable_rules", "repainting_lookahead_concerns", "performance_claims", "limitations")} | {"timeframe": str, "stop_loss": str, "profit_target": str, "risk_reward": str},
    "education": {k: list for k in ("concepts_explained", "key_lessons", "examples", "mistakes_misconceptions", "practical_implications", "risks_caveats", "claims_requiring_verification", "recommended_next_research")} | {"main_concept": str, "target_audience": str},
    "prop_firm_funding": {k: list for k in ("firms_platforms", "funding_model", "evaluation_challenge_structure", "fees_costs", "profit_split", "capital_allocation_model", "drawdown_rules", "daily_loss_rules", "payout_rules", "time_to_funding", "scaling_allocation_growth", "investor_access", "risk_engine_mechanics", "advantages", "disadvantages", "conflicts_of_interest_claimed", "affiliate_promotional_incentives", "claims_requiring_external_verification")} | {"creator_conclusion": str},
    "broker_platform": {k: list for k in ("supported_markets", "fees_spreads_commissions", "execution_features", "platform_tools", "risk_controls", "withdrawal_funding_model", "advantages", "disadvantages", "customer_complaints", "regulatory_verification_questions", "affiliate_promotional_incentives")} | {"broker_platform": str, "account_model": str},
    "risk_management": {k: list for k in ("position_sizing", "drawdown_rules", "daily_loss", "max_loss", "risk_per_trade", "exposure", "correlation", "stop_loss_logic", "risk_engine", "examples", "claimed_benefits", "limitations", "backtestable_rules")} | {"risk_framework": str},
    "market_analysis": {k: list for k in ("technical_evidence", "fundamental_evidence", "levels", "catalysts", "risks", "invalidation", "scenario_alternatives", "claims_requiring_verification")} | {"market_instrument": str, "directional_thesis": str, "time_horizon": str},
    "indicator_tool": {k: list for k in ("inputs_settings", "signals", "entry_exit_interpretation", "dependencies", "repainting_concerns", "source_code_availability", "backtestability", "limitations")} | {"indicator_tool_name": str, "purpose": str, "market_timeframe": str},
    "unknown_trading": {k: list for k in ("main_topics", "claims", "examples", "unknowns", "followup_research")} | {"content_summary": str},
}
TRADING_SUBTYPE_REQUIRED = {
    # Instrument may genuinely be omitted by a chart walkthrough; entry rules
    # are the meaningful strategy evidence required for acceptance.
    "strategy": ["entry_rules"], "education": ["main_concept"],
    "prop_firm_funding": ["firms_platforms", "funding_model"], "broker_platform": ["broker_platform"],
    "risk_management": ["risk_framework"], "market_analysis": ["market_instrument", "directional_thesis"],
    "indicator_tool": ["indicator_tool_name", "purpose"], "unknown_trading": ["content_summary"],
}
TRADING_SUBTYPE_DEPARTMENTS = ["MERCURY_TRADING"]


def trading_contract(subtype: str) -> dict[str, Any]:
    if subtype not in TRADING_SUBTYPE_FIELDS:
        raise KeyError(f"unknown trading subtype: {subtype}")
    fields = {**TRADING_SUBTYPE_FIELDS[subtype], GROUNDING_FIELD: list}
    return {
        "profile_id": f"trading:{subtype}",
        "extraction_schema": _schema(fields),
        "target_departments": list(TRADING_SUBTYPE_DEPARTMENTS),
        "quality_checks": {"min_non_empty_list_fields": [], "required_meaningful_fields": TRADING_SUBTYPE_REQUIRED[subtype],
                           "require_any_citation_marker": False, "max_empty_ratio": 1.0},
    }


def build_trading_subtype_prompt(*, subtype: str, video_title: str) -> str:
    contract = trading_contract(subtype)
    fields = contract["extraction_schema"]["properties"]
    skeleton = {name: ([] if spec["type"] == "array" else None) for name, spec in fields.items()}
    return (f"Extract this source using only the {subtype} Trading contract. Title: {video_title}\\n"
            f"Return strict JSON matching: {json.dumps(skeleton, sort_keys=True)}\\n"
            "For array fields use [\\\"NOT_STATED\\\"] when absent, [\\\"NOT_APPLICABLE\\\"] only when genuinely inapplicable, or [\\\"UNKNOWN\\\"] when unresolved. Use null for absent scalar fields. Do not infer or use outside knowledge. Keep source claims distinct from external verification. "
            f"{GROUNDING_INSTRUCTION} {EXTRACTION_JSON_INSTRUCTION}")


def build_trading_subtype_classification_prompt(*, video_title: str, video_description: str = "") -> str:
    return ("Classify the substantive content of the attached source into exactly one Trading subtype. "
            "Choose based on what the source teaches, not sponsorship/hashtags alone. Subtypes: "
            f"{json.dumps(sorted(TRADING_SUBTYPE_FIELDS))}. Use education_comparison for comparative explanatory content; otherwise concise content_mode. "
            "Return strict JSON keys trading_subtype, content_mode, secondary_signals, evidence_quotes. "
            "secondary_signals may contain affiliate_opportunity only when explicit affiliate link, discount/referral code, or commission promotion is present; this is a signal, not qualification. "
            f"Use source evidence quotes. Title: {video_title} Description: {video_description[:1500]}")


def _schema(fields: dict[str, type | tuple[type, ...]]) -> dict[str, Any]:
    return {
        "type": "object",
        "required": sorted(fields),
        "additionalProperties": False,
        "properties": {
            name: (
                {"type": "array", "items": {"type": "string"}}
                if kind is list
                else {"type": "number"} if kind in (int, float) or (isinstance(kind, tuple) and int in kind)
                else {"type": kind.__name__}
            )
            for name, kind in fields.items()
        },
    }


PROFILES: dict[str, dict[str, Any]] = {
    "forex_strategy": {
        "profile_id": "forex_strategy",
        "notebook_pool": "trading_forex",
        "priority": 10,
        "classification_rules": {
            "match": "all_any",
            "required_any": ["forex", "scalping", "pips", "currency pair", "pip target", "gbpusd", "eurusd",
                             "usdjpy", "audusd", "gbpjpy", "xauusd", "session open london", "day trading forex",
                             "1 minute forex", "forex strategy", "forex trading", "stochastic rsi"],
            "boost_any": ["1 minute", "one minute", "moving average", "stochastic rsi", "engulfing", "order block",
                          "risk to reward", "prop firm", "funded account"],
            "exclude_any": ["crypto only", "stock only"],
        },
        "extraction_schema": _schema({
            "timeframe": str,
            "market_pairs": list,
            "indicators": list,
            "indicator_settings": list,
            "entry_rules": list,
            "exit_rules": list,
            "target": str,
            "stop_loss": str,
            "risk_reward": str,
            "favorable_conditions": list,
            "unfavorable_conditions": list,
            "session_rules": list,
        }),
        "target_departments": ["MERCURY_TRADING", "ATLAS_OPPORTUNITY"],
        "quality_checks": {
            "min_non_empty_list_fields": ["indicators", "entry_rules"],
            "require_any_citation_marker": True,
            "max_empty_ratio": 0.6,
        },
    },
    "trading_general": {
        "profile_id": "trading_general",
        "notebook_pool": "trading_forex",
        "priority": 20,
        "classification_rules": {
            "match": "all_any",
            "required_any": ["trading", "trader", "indicator", "rsi", "macd", "backtest", "drawdown", "prop firm",
                             "funded", "chart", "signal", "position sizing", "psychology", "rules", "fibonacci",
                             "retracement", "candlestick", "support and resistance", "breakout", "swing trade",
                             "day trade", "scalp", "profit", "loss", "stop loss", "take profit"],
            "exclude_any": [],
        },
        "extraction_schema": _schema({
            "timeframe": str,
            "asset_classes": list,
            "indicators": list,
            "indicator_settings": list,
            "setup_description": str,
            "entry_rules": list,
            "exit_rules": list,
            "risk_management": list,
            "performance_claims": list,
            "platforms_mentioned": list,
        }),
        "target_departments": ["MERCURY_TRADING"],
        "quality_checks": {
            "min_non_empty_list_fields": ["indicators", "entry_rules"],
            "require_any_citation_marker": True,
            "max_empty_ratio": 0.6,
        },
    },
    "business_funding": {
        "profile_id": "business_funding",
        "notebook_pool": "business_funding",
        "priority": 30,
        "classification_rules": {
            "match": "all_any",
            "required_any": ["prop firm", "funded account", "funding", "lender", "sba", "loan", "underwriting",
                             "invoice financing", "working capital", "ftmo", "darwinex", "evaluation", "payout",
                             "cash flow", "asset class", "capital raise", "acquisition funding"],
            "exclude_any": [],
        },
        "extraction_schema": _schema({
            "program_names": list,
            "eligibility_rules": list,
            "fee_structure": list,
            "payout_rules": list,
            "drawdown_rules": list,
            "time_limits": list,
            "provider_claims": list,
            "applicant_requirements": list,
        }),
        "target_departments": ["ATLAS_OPPORTUNITY", "CLYDE_CREDIT"],
        "quality_checks": {
            "min_non_empty_list_fields": ["eligibility_rules"],
            "require_any_citation_marker": True,
            "max_empty_ratio": 0.55,
        },
    },
    "credit": {
        "profile_id": "credit",
        "notebook_pool": "credit",
        "priority": 30,
        "classification_rules": {
            "match": "all_any",
            "required_any": ["credit score", "fico", "credit utilization", "derogatory", "credit bureau", "dispute",
                             "credit repair", "credit report", "collections", "charge off",
                             "credit line", "credit denied", "bank denied", "credit card"],
            "boost_any": ["credit", "debt", "utilization", "lender", "loan"],
            "exclude_any": [],
        },
        "extraction_schema": _schema({
            "credit_factors": list,
            "score_ranges": list,
            "actions_taken": list,
            "timeframes": list,
            "costs": list,
            "risks_mentioned": list,
            "claims": list,
        }),
        "target_departments": ["CLYDE_CREDIT"],
        "quality_checks": {
            "min_non_empty_list_fields": ["credit_factors", "actions_taken"],
            "require_any_citation_marker": True,
            "max_empty_ratio": 0.55,
        },
    },
    "grants": {
        "profile_id": "grants",
        "notebook_pool": "grants",
        "priority": 30,
        "classification_rules": {
            "match": "all_any",
            "required_any": ["grant", "grantwriting", "nonprofit funding", "sba grant", "government funding",
                             "fellowship", "award application"],
            "exclude_any": [],
        },
        "extraction_schema": _schema({
            "programs_named": list,
            "eligibility_rules": list,
            "application_steps": list,
            "deadlines": list,
            "award_amounts": list,
            "requirements": list,
        }),
        "target_departments": ["GRANT_FUNDING"],
        "quality_checks": {
            "min_non_empty_list_fields": ["programs_named", "eligibility_rules"],
            "require_any_citation_marker": True,
            "max_empty_ratio": 0.55,
        },
    },
    "customer_needs": {
        "profile_id": "customer_needs",
        "notebook_pool": "customer_needs",
        "priority": 40,
        "classification_rules": {
            "match": "all_any",
            "required_any": ["customer", "audience", "pain point", "complaint", "how to grow", "small business owners",
                             "agency clients", "clients ask", "customer question", "marketplace",
                             "why buyers", "lost customers", "churn", "prospect", "offer validation"],
            "exclude_any": [],
        },
        "extraction_schema": _schema({
            "audience_described": str,
            "problems_stated": list,
            "questions_asked": list,
            "current_solutions": list,
            "willingness_to_pay_signals": list,
            "verbatims": list,
            "source_promises": list,
        }),
        "target_departments": ["SCOUT_INTELLIGENCE", "MIRA_MARKETING"],
        "quality_checks": {
            "min_non_empty_list_fields": ["problems_stated"],
            "require_any_citation_marker": False,
            "max_empty_ratio": 0.5,
        },
    },
    "marketing_seo": {
        "profile_id": "marketing_seo",
        "notebook_pool": "marketing_seo",
        "priority": 40,
        "classification_rules": {
            "match": "all_any",
            "required_any": ["seo", "keyword", "search intent", "google ads", "meta ads", "funnel", "affiliate",
                             "youtube channel growth", "thumbnail", "ranking", "backlinks", "email list"],
            "exclude_any": [],
        },
        "extraction_schema": _schema({
            "channels_named": list,
            "tactics_named": list,
            "steps_given": list,
            "tools_named": list,
            "metrics_mentioned": list,
            "costs_mentioned": list,
            "time_horizons": list,
        }),
        "target_departments": ["MIRA_MARKETING", "SCOUT_INTELLIGENCE"],
        "quality_checks": {
            "min_non_empty_list_fields": ["tactics_named", "steps_given"],
            "require_any_citation_marker": True,
            "max_empty_ratio": 0.55,
        },
    },
    "creative": {
        "profile_id": "creative",
        "notebook_pool": "creative",
        "priority": 50,
        "classification_rules": {
            "match": "all_any",
            "required_any": ["design", "brand", "logo", "color palette", "typography", "3d", "animation", "video editing",
                             "creative direction", "moodboard", "figma", "after effects"],
            "exclude_any": [],
        },
        "extraction_schema": _schema({
            "visual_direction": list,
            "tools_named": list,
            "techniques_named": list,
            "reference_works": list,
            "workflow_steps": list,
            "assets_produced": list,
        }),
        "target_departments": ["MIRA_MARKETING"],
        "quality_checks": {
            "min_non_empty_list_fields": ["visual_direction"],
            "require_any_citation_marker": False,
            "max_empty_ratio": 0.55,
        },
    },
    "ai_automation_systems": {
        "profile_id": "ai_automation_systems",
        "notebook_pool": "ai_systems",
        "priority": 40,
        "classification_rules": {
            "match": "all_any",
            "required_any": ["claude code", "cursor", "copilot", "ai agent", "llm", "automation", "workflow automate",
                             "mcp", "prompt engineering", "rag", "openai", "deepseek", "local model", "api"],
            "exclude_any": [],
        },
        "extraction_schema": _schema({
            "tools_named": list,
            "workflow_steps": list,
            "automation_targets": list,
            "setup_requirements": list,
            "costs_mentioned": list,
            "claimed_capabilities": list,
            "limitations_mentioned": list,
            "time_savings_claims": list,
        }),
        "target_departments": ["FORGE_SYSTEMS", "ATLAS_OPPORTUNITY"],
        "quality_checks": {
            "min_non_empty_list_fields": ["tools_named", "workflow_steps"],
            "require_any_citation_marker": True,
            "max_empty_ratio": 0.6,
        },
    },
    "general_business": {
        "profile_id": "general_business",
        "notebook_pool": "business_funding",
        "priority": 60,
        "classification_rules": {
            "match": "all_any",
            "required_any": ["business", "agency", "consulting", "offer", "pricing", "operations", "hiring",
                             "management", "revenue", "profit"],
            "exclude_any": [],
        },
        "extraction_schema": _schema({
            "business_models_named": list,
            "operational_advice": list,
            "financial_claims": list,
            "tools_named": list,
            "risks_mentioned": list,
            "action_items": list,
        }),
        "target_departments": ["ATLAS_OPPORTUNITY", "LEDGER_FINANCE"],
        "quality_checks": {
            "min_non_empty_list_fields": ["operational_advice"],
            "require_any_citation_marker": False,
            "max_empty_ratio": 0.5,
        },
    },
    "trend_signal": {
        "profile_id": "trend_signal",
        "notebook_pool": "emerging_trends",
        "priority": 80,
        "classification_rules": {"match": "all_any", "required_any": ["trend signal", "high attention", "emerging trend"], "exclude_any": []},
        "extraction_schema": _schema({
            "topic": str, "first_seen": str, "platforms_seen": list, "attention_signal": str,
            "engagement_velocity": str, "cross_platform_presence": list, "audience": str,
            "repeated_phrases": list, "pain_points": list, "desired_outcomes": list,
            "sentiment": str, "commercial_intent": str, "existing_products": list,
            "affiliate_availability": str, "merch_potential": str, "service_potential": str,
            "digital_product_potential": str, "seo_potential": str, "campaign_potential": str,
            "estimated_shelf_life": str, "competitive_density": str, "evidence_quality": str,
            "ip_or_trademark_risk": str, "platform_risk": str, "recommended_followup_research": list,
        }),
        "target_departments": ["SCOUT_INTELLIGENCE", "ATLAS_OPPORTUNITY"],
        "quality_checks": {"min_non_empty_list_fields": ["platforms_seen"], "required_meaningful_fields": ["topic", "attention_signal", "evidence_quality"],
                           "require_any_citation_marker": False, "max_empty_ratio": 0.75},
    },
    "triage_unknown": {
        "profile_id": "triage_unknown",
        "notebook_pool": "triage",
        "priority": 99,
        "classification_rules": {"match": "fallback", "required_any": [], "exclude_any": []},
        "extraction_schema": _schema({
            "topic_summary": str,
            "claims": list,
            "entities_named": list,
            "tools_named": list,
            "action_items": list,
            "unclear_points": list,
        }),
        "target_departments": ["ATLAS_OPPORTUNITY"],
        "quality_checks": {
            "min_non_empty_list_fields": ["claims"],
            "require_any_citation_marker": False,
            "max_empty_ratio": 0.5,
        },
    },
}

FALLBACK_PROFILE_ID = "triage_unknown"

NOTEBOOK_POOLS: dict[str, dict[str, Any]] = {
    "trading_forex": {"title": "Nexus Research - Trading and Forex", "max_sources": 30, "create_if_missing": True},
    "business_funding": {"title": "Nexus Research - Business and Funding", "max_sources": 30, "create_if_missing": True},
    "credit": {"title": "Nexus Research - Credit", "max_sources": 25, "create_if_missing": True},
    "grants": {"title": "Nexus Research - Grants", "max_sources": 25, "create_if_missing": True},
    "customer_needs": {"title": "Nexus Research - Customer Needs", "max_sources": 30, "create_if_missing": True},
    "marketing_seo": {"title": "Nexus Research - Marketing and SEO", "max_sources": 30, "create_if_missing": True},
    "creative": {"title": "Nexus Research - Creative", "max_sources": 25, "create_if_missing": True},
    "ai_systems": {"title": "Nexus Research - AI and Automation Systems", "max_sources": 30, "create_if_missing": True},
    "emerging_trends": {"title": "Nexus Research - Emerging Trends", "max_sources": 40, "create_if_missing": True},
    "triage": {"title": "Nexus Research - Triage", "max_sources": 40, "create_if_missing": True},
}

ALIASES: dict[str, str] = {
    "Nexus Research - Forex Scalping Canary": "trading_forex",
}


_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_NON_WORD = re.compile(r"[^a-z0-9]+")


def _normalize(text: str) -> str:
    """Lowercase and split camelCase / punctuation runs into word tokens.

    YouTube titles arrive with inconsistent casing ('TheMovingAverage',
    'SMMA-Strategy'), so token boundaries must be recovered before whole-token
    term matching can work at all.
    """
    spaced = _CAMEL.sub(" ", text or "")
    return _NON_WORD.sub(" ", spaced.lower()).strip()


def _haystack(title: str, description: str = "", channel: str = "") -> str:
    return " ".join(
        _normalize(part) for part in (title or "", description or "", channel or "")
    ).strip()


def _term_hits(haystack: str, term: str) -> int:
    """Count whole-token occurrences only.  Plain substring matching produced
    real false positives ('average' matched the 'rag' automation term)."""
    pattern = re.compile(r"(?<![a-z0-9])" + re.escape(_normalize(term)) + r"(?![a-z0-9])")
    return len(pattern.findall(haystack))


def score_profile(profile_id: str, haystack: str) -> tuple[int, bool]:
    """Return (score, excluded) for one profile against a lowercased haystack."""
    profile = PROFILES[profile_id]
    rules = profile["classification_rules"]
    if rules.get("match") == "fallback":
        return 0, False
    if any(_term_hits(haystack, term) for term in rules.get("exclude_any", [])):
        return 0, True
    required = rules.get("required_any", [])
    if not required:
        return 0, False
    hits = sum(1 for term in required if _term_hits(haystack, term))
    boost = sum(1 for term in rules.get("boost_any", []) if _term_hits(haystack, term))
    if hits == 0:
        return 0, False
    return hits + boost, False


def _score_all(haystack: str) -> tuple[dict[str, int], list[str]]:
    scores: dict[str, int] = {}
    excluded: list[str] = []
    for profile_id in PROFILES:
        value, blocked = score_profile(profile_id, haystack)
        if blocked:
            excluded.append(profile_id)
        if value:
            scores[profile_id] = value
    return scores, excluded


def classify_profile(*, title: str, description: str = "", channel: str = "",
                     override: str | None = None) -> dict[str, Any]:
    """Deterministically map a source to exactly one research profile.

    The title decides on its own first.  Description and channel are only
    consulted when the title matches nothing, because a channel name alone
    would otherwise force every upload onto one department ('Credit Plug' made
    every one of its videos score as credit research).
    """
    if override:
        if override not in PROFILES:
            raise KeyError(f"unknown research_profile_id: {override}")
        return {"profile_id": override, "reason": "explicit_override", "scores": {override: -1}, "confidence": "DECLARED"}

    scores, excluded = _score_all(_haystack(title))
    matched_on = "title"
    if not scores:
        scores, excluded = _score_all(_haystack(title, description, channel))
        matched_on = "title_description_channel"
    if not scores:
        return {"profile_id": FALLBACK_PROFILE_ID, "reason": "no_rule_matched", "scores": {}, "confidence": "FALLBACK",
                "matched_on": matched_on, "excluded_profiles": excluded}
    ranked = sorted(scores.items(), key=lambda row: (-row[1], PROFILES[row[0]]["priority"], row[0]))
    best_id, best_score = ranked[0]
    runner_up = ranked[1][1] if len(ranked) > 1 else 0
    if best_score == runner_up:
        return {"profile_id": best_id, "reason": "tie_broken_by_priority_then_id", "scores": scores,
                "confidence": "TIE_RESOLVED", "matched_on": matched_on, "excluded_profiles": excluded}
    margin = best_score - runner_up
    confidence = "HIGH" if margin >= 3 else "MEDIUM" if margin >= 1 else "LOW"
    return {"profile_id": best_id, "reason": "keyword_score", "scores": scores, "confidence": confidence,
            "margin": margin, "matched_on": matched_on, "excluded_profiles": excluded}


def get_profile(profile_id: str) -> dict[str, Any]:
    if profile_id not in PROFILES:
        raise KeyError(f"unknown research_profile_id: {profile_id}")
    return PROFILES[profile_id]


def pool_for(profile_id: str) -> dict[str, Any]:
    pool_id = get_profile(profile_id)["notebook_pool"]
    if pool_id not in NOTEBOOK_POOLS:
        raise KeyError(f"unknown notebook pool: {pool_id}")
    return {"pool_id": pool_id, **NOTEBOOK_POOLS[pool_id]}


def build_prompt(profile: dict[str, Any], *, video_title: str) -> str:
    """Deterministic question wrapper for one profile."""
    fields = profile["extraction_schema"]["properties"]
    skeleton = "{\n" + ",\n".join(f'  "{name}": {"[]" if field["type"] == "array" else "null"}'
                                  for name, field in sorted(fields.items())) + "\n}"
    departments = ", ".join(profile["target_departments"])
    return (
        f"Read only the single attached source and extract its factual content.\n\n"
        f"Source title: {video_title}\n\n"
        f"Return strict JSON matching this exact shape:\n{skeleton}\n\n"
        f"Rules:\n"
        f"1. Use only what this source states. Do not infer, do not add general knowledge.\n"
        f"2. Use null for a scalar that is not stated and [] for an array with no stated items.\n"
        f"3. Keep short quoted phrases verbatim; do not paraphrase numbers.\n"
        f"4. Every list item must be a self-contained statement, not a reference to another field.\n"
        f"5. Output raw JSON only: no markdown fence, no prose, no trailing commentary.\n"
        f"6. {GROUNDING_INSTRUCTION}\n\n"
        f"The extracted record will be routed to: {departments}.\n\n"
        f"{EXTRACTION_JSON_INSTRUCTION}\n"
    )


def build_profile_fit_prompt(candidate_profile_id: str, *, video_title: str) -> str:
    """Ask whether the source's substance belongs to one candidate profile.

    The profile catalog is derived from the shared contracts so this gate stays
    generic as profiles are added or edited.
    """
    if candidate_profile_id not in PROFILES:
        raise KeyError(f"unknown research_profile_id: {candidate_profile_id}")
    catalog = []
    for profile_id, profile in sorted(PROFILES.items()):
        rules = profile.get("classification_rules", {})
        catalog.append({
            "profile_id": profile_id,
            "departments": profile.get("target_departments", []),
            "topic_signals": rules.get("required_any", []),
            "extracts": sorted(profile.get("extraction_schema", {}).get("properties", {})),
        })
    candidate = next(row for row in catalog if row["profile_id"] == candidate_profile_id)
    return (
        "Inspect only the attached source and determine whether its substantive content, not a sponsor, "
        "hashtag, passing mention, or channel name, materially belongs to the candidate research profile.\n"
        f"Source title: {video_title}\n"
        f"Candidate profile: {json.dumps(candidate, sort_keys=True)}\n"
        f"Available profiles for reclassification: {json.dumps(catalog, sort_keys=True)}\n\n"
        "Return strict JSON only with keys: fit (YES or NO), candidate_profile_id (the exact candidate id), "
        "suggested_profile_id (null for YES; for NO choose the single best different available profile), "
        "reason (brief), and evidence_quotes (one or more short verbatim quotes from this source). "
        "Do not infer from general knowledge. Choose YES only when the source's main substantive material "
        "belongs to the candidate, not merely because the candidate appears in a sponsor or tag. If no domain "
        "profile fits, suggest triage_unknown. Do not answer the full extraction contract.\n"
    )


def profile_digest(profile: dict[str, Any] | None = None) -> str:
    """Stable digest for one profile, or the whole registry when omitted."""
    payload = PROFILES if profile is None else profile
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
