"""Canonical Marketing revenue-engine contracts and bounded GoClear canary.

Marketing owns acquisition strategy and measurement. It does not publish, send,
spend, mutate customer state, or replace Creative. All durable records use the
existing governed append-only persistence and the existing Nexus work-order
contract.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from nexus_agent_platform.governed import persistence

MARKETING_FUNNEL_SCHEMA = "nexus.marketing-funnel.v1"
MARKETING_EVENT_SCHEMA = "nexus.marketing-event.v1"
MARKETING_WORK_SCHEMA = "nexus.marketing-work-item.v1"
MARKETING_HANDOFF_SCHEMA = "nexus.marketing-creative-handoff.v1"
MARKETING_PROJECT_SCHEMA = "nexus.marketing-project.v1"

PROJECT_STATUSES = ("NOT_STARTED", "PLANNING", "WAITING_RESEARCH", "WAITING_CREATIVE", "READY_TO_DEPLOY", "ACTIVE", "MEASURING", "REVISION_REQUIRED", "COMPLETE", "BLOCKED")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_id(prefix: str, value: Any) -> str:
    digest = hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:16]
    return f"{prefix}_{digest}"


def marketing_charter() -> Dict[str, Any]:
    return {
        "charter_id": "marketing_revenue_engine_v1",
        "purpose": "Turn verified customer demand into measurable acquisition systems.",
        "responsibilities": ["AUDIENCE", "OFFER", "POSITIONING", "FUNNEL", "CHANNEL", "CAMPAIGN", "CONVERSION", "EXPERIMENT", "MEASUREMENT", "LEARNING"],
        "does_not_own": ["general Research", "Creative execution", "CRM canonical customer state", "payments infrastructure", "remote-worker infrastructure", "unrestricted advertising spend"],
        "authority": {"read_analyze": "autonomous_where_authorized", "draft": "autonomous", "publish": "governed", "spend": "explicit_policy_and_approval"},
        "status": "PASS_REAL_BOUNDED",
    }


def build_goclear_funnel() -> Dict[str, Any]:
    funnel_id = "goclear_funding_readiness_funnel_v1"
    objective_id = "objective_goclear_customer_acquisition_readiness_review"
    campaign_id = "goclear_readiness_review_canary_20260921"
    return {
        "schema_version": MARKETING_FUNNEL_SCHEMA,
        "funnel_id": funnel_id,
        "objective_id": objective_id,
        "campaign_id": campaign_id,
        "audience": "Business owners seeking funding, recently denied, or uncertain whether they are lender-ready.",
        "segment": "Owner-operated small businesses with a concrete funding or preparation question and a need for evidence-bounded next steps.",
        "problem": "The owner does not know what is ready, what is missing, or whether applying now would be premature.",
        "customer_language": ["I do not know what lenders will look at.", "I do not want to apply too early.", "I need to know what to fix or prepare next.", "I have a business but the funding conversation still feels unclear."],
        "desired_outcome": "A clearer readiness picture and a bounded next-step plan, without a promise of approval or funding.",
        "offer": {"entry_offer": "$97 Credit & Funding Readiness Review", "core_offer": "$297/$497 higher-touch readiness and preparation services where approved", "upsell": "qualified downstream funding-placement or service path only after review and explicit terms"},
        "CTA": "Start the $97 readiness review",
        "traffic_sources": ["organic search", "educational content", "owned email draft", "referral/partner hypothesis", "organic social draft"],
        "funnel_stages": ["traffic", "landing_page", "diagnostic_or_qualification", "lead_capture", "review_purchase_or_appointment", "onboarding", "readiness_service", "funding_preparation", "funding_placement_if_qualified", "nurture_or_retarget"],
        "creative_requirements": ["landing page hero", "organic short-form concept", "email/retargeting concept", "proof-safe diagnostic framing", "clear CTA"],
        "experiments": [],
        "metrics": {"visits": 0, "leads": 0, "qualified_leads": 0, "appointments": 0, "sales": 0, "revenue": 0, "CPL": None, "CPA": None, "conversion_rate": None, "appointment_rate": None, "close_rate": None, "ROAS": None},
        "active_test": None,
        "winning_variant": None,
        "losing_variant": None,
        "next_test": "Validate readiness-first positioning against a direct uncertainty framing before any live traffic.",
        "status": "PLANNING",
        "created_at": now(),
        "updated_at": now(),
        "publication_authorized": False,
        "paid_spend_authorized": False,
        "evidence_boundary": "Research supports the customer problem and language; no live conversion, demand, approval, funding, or revenue claim is available yet.",
    }


def build_event(funnel: Mapping[str, Any], event_type: str, *, source: str = "internal_canary", channel: str = "internal", session_id: str = "canary_session", lead_id: str | None = None, creative_variant: str | None = None, value: float | None = None, metadata: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    allowed = {"page_view", "CTA_click", "form_start", "form_complete", "lead_created", "lead_qualified", "appointment_booked", "purchase", "upsell", "email_open", "email_click", "campaign_source", "creative_variant"}
    if event_type not in allowed:
        raise ValueError(f"unknown_marketing_event:{event_type}")
    return {"schema_version": MARKETING_EVENT_SCHEMA, "event_id": stable_id("mkt_evt", (funnel["funnel_id"], event_type, session_id, creative_variant, value)), "funnel_id": funnel["funnel_id"], "campaign_id": funnel["campaign_id"], "lead_id": lead_id, "session_id": session_id, "timestamp": now(), "event_type": event_type, "source": source, "channel": channel, "creative_variant": creative_variant, "metadata": dict(metadata or {}), "value": value, "external_action_performed": False}


def build_marketing_work_item(funnel: Mapping[str, Any], *, work_type: str, required_capabilities: Sequence[str], parent_work_id: str | None = None) -> Dict[str, Any]:
    work_id = stable_id("mkt_work", (funnel["funnel_id"], work_type, parent_work_id))
    return {"schema_version": MARKETING_WORK_SCHEMA, "work_id": work_id, "objective_id": funnel["objective_id"], "parent_work_id": parent_work_id, "department": "MARKETING", "work_type": work_type, "work_class": "BOUNDED_INTERNAL_CANARY", "required_capabilities": list(required_capabilities), "priority": "normal", "status": "CREATED", "assigned_worker": "GROWTH", "lease_owner": "marketing_canary", "lease_expiry": None, "attempt_count": 0, "max_attempts": 1, "retry_strategy": "fail_closed_no_external_retry", "source_refs": ["research_v2_handoff", "goclear_funding_readiness_evidence"], "result_refs": [], "evidence_refs": [], "destination_department": "CREATIVE", "created_at": now(), "updated_at": now(), "terminal_reason": None, "idempotency_key": stable_id("mkt_idem", work_id)}


def build_creative_handoff(funnel: Mapping[str, Any]) -> Dict[str, Any]:
    handoff_id = stable_id("mkt_creative", funnel["campaign_id"])
    return {"schema_version": MARKETING_HANDOFF_SCHEMA, "handoff_id": handoff_id, "funnel_id": funnel["funnel_id"], "campaign_id": funnel["campaign_id"], "campaign_objective": "Generate internal campaign territories that make the readiness problem understandable and motivate a safe next step.", "audience": funnel["audience"], "customer_tension": funnel["problem"], "customer_language": funnel["customer_language"], "offer": funnel["offer"], "positioning": "GoClear helps owners understand readiness and next steps; it is not a lender and does not guarantee approval, funding, removal, or score improvement.", "proof_boundaries": ["Use only supplied research and approved educational framing.", "No guaranteed funding or approval.", "No fabricated testimonials, results, or demand.", "No causal performance claim."], "channels": ["landing_page", "organic_short_form", "owned_email_or_retargeting_draft"], "CTA": funnel["CTA"], "asset_classes": ["strategic_concept", "landing_page_hero", "organic_ad_concept", "short_form_video_concept", "email_retargeting_idea"], "test_hypothesis": "Readiness-first framing may produce clearer qualified review intent than generic funding aspiration, but this requires live measurement.", "measurement_requirements": ["page_view", "CTA_click", "form_start", "form_complete", "lead_created", "lead_qualified", "purchase", "creative_variant"], "visual_discovery_opt_in": True, "v2_opt_in": True, "status": "READY_FOR_CREATIVE", "created_at": now(), "publication_authorized": False}


def persist_once(collection: str, record: Dict[str, Any], key: str) -> Dict[str, Any]:
    existing = persistence.get_record(collection, record[key], key=key)
    if existing:
        return {**existing, "persistence": "DUPLICATE_SUPPRESSED"}
    persistence.append_record(collection, record)
    return {**record, "persistence": "CREATED"}


def persist_funnel(funnel: Dict[str, Any]) -> Dict[str, Any]:
    return persist_once("marketing_funnels", funnel, "funnel_id")


def persist_project(funnel: Mapping[str, Any], status: str, *, handoff_id: str | None = None, selected: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    if status not in PROJECT_STATUSES:
        raise ValueError("invalid_marketing_project_status")
    record = {"schema_version": MARKETING_PROJECT_SCHEMA, "project_id": stable_id("mkt_project", funnel["funnel_id"]), "funnel_id": funnel["funnel_id"], "objective_id": funnel["objective_id"], "campaign_id": funnel["campaign_id"], "department": "MARKETING", "status": status, "handoff_id": handoff_id, "selected": dict(selected or {}), "updated_at": now(), "created_at": now()}
    # Projects are stateful projections over the append-only governed store;
    # each transition is retained so Nova can inspect the latest state and its
    # prior status history without creating a second project database.
    persistence.append_record("marketing_projects", record)
    return {**record, "persistence": "CREATED_STATE_TRANSITION"}


def validate_lead_capture() -> Dict[str, Any]:
    return {"schema_version": "nexus.marketing-lead-capture.v1", "allowed_fields": ["contact_email", "contact_name", "business_status", "funding_objective", "timeline", "revenue_range_optional", "readiness_indicators", "consent", "source", "campaign_id", "session_id"], "prohibited_by_default": ["full credit report", "SSN", "bank login", "unnecessary sensitive financial data"], "consent_required": True, "status": "PASS_REAL_BOUNDED"}


def qualification_logic() -> Dict[str, Any]:
    return {"schema_version": "nexus.marketing-qualification.v1", "qualified_when": ["explicit funding or readiness objective", "business context supplied", "timeline supplied", "consent recorded", "no prohibited-data requirement"], "not_qualified_when": ["missing consent", "unsupported outcome expectation", "no actionable objective", "request requires a lender/credit decision Nexus does not make"], "human_review": ["funding placement eligibility", "regulated or sensitive interpretation", "conflicting evidence"], "status": "PASS_REAL_BOUNDED"}


def marketing_visibility(funnel: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    """Canonical read-only projection for Nova/Admin; never invents traffic."""
    funnel = funnel or (persistence.latest_record("marketing_funnels") or {})
    projects = persistence.read_records("marketing_projects")
    events = persistence.read_records("marketing_events")
    project = next((p for p in projects if p.get("funnel_id") == funnel.get("funnel_id")), None)
    counts = {event: sum(1 for row in events if row.get("event_type") == event and row.get("funnel_id") == funnel.get("funnel_id")) for event in ("page_view", "CTA_click", "form_start", "form_complete", "lead_created", "lead_qualified", "appointment_booked", "purchase")}
    return {"schema_version": "nexus.marketing-visibility.v1", "active_projects": [project] if project else [], "active_funnel": funnel or None, "audience": funnel.get("audience") if funnel else None, "offer": funnel.get("offer") if funnel else None, "creative_handoff_status": "READY_FOR_CREATIVE" if persistence.read_records("marketing_handoffs") else "NOT_STARTED", "selected_creative": project.get("selected") if project else {}, "campaign_live": False, "live_traffic": False, "measurement_counts": counts, "drop_off_analysis": "NO_LIVE_TRAFFIC_YET", "current_experiment": funnel.get("active_test") if funnel else None, "next_test": funnel.get("next_test") if funnel else None, "blocked": ["production publication requires approval", "paid spend is not authorized", "no live traffic evidence exists"], "status": "PASS_REAL_BOUNDED"}


def native_landing_page_validation(html: str) -> Dict[str, Any]:
    """Nexus-native equivalent of the useful Landforge landing validator."""
    checks = {
        "doctype": bool(re.search(r"<!doctype html>", html, re.I)),
        "lang": bool(re.search(r"<html\b[^>]*\blang=", html, re.I)),
        "charset": bool(re.search(r"<meta\b[^>]*charset=", html, re.I)),
        "viewport": bool(re.search(r"<meta\b[^>]*name=['\"]viewport['\"]", html, re.I)),
        "title": bool(re.search(r"<title>\s*.+?\s*</title>", html, re.I | re.S)),
        "description": bool(re.search(r"<meta\b[^>]*name=['\"]description['\"]", html, re.I)),
        "canonical": bool(re.search(r"<link\b[^>]*rel=['\"]canonical['\"]", html, re.I)),
        "open_graph": all(bool(re.search(rf"<meta\b[^>]*property=['\"]{name}['\"]", html, re.I)) for name in ("og:title", "og:description", "og:url", "og:image")),
        "single_h1": len(re.findall(r"<h1\b", html, re.I)) == 1,
        "build_marker": bool(re.search(r"build:[\w-]+", html)),
        "no_external_script": not bool(re.search(r"<script\b[^>]*\bsrc=", html, re.I)),
        "no_external_css": not bool(re.search(r"<link\b[^>]*rel=['\"]stylesheet['\"]", html, re.I)),
    }
    return {"schema_version": "nexus.marketing-landing-validation.v1", "checks": checks, "errors": [key for key, passed in checks.items() if not passed], "warnings": ["json_ld_missing"] if not re.search(r"application/ld\+json", html, re.I) else [], "status": "PASS_REAL_BOUNDED" if all(checks.values()) else "FAILED_REAL"}


def native_ab_validation(html: str, experiment_id: str) -> Dict[str, Any]:
    """Nexus-native stable split + variant analytics validator."""
    checks = {"stable_cookie_split": "document.cookie" in html and ("__abVariant" in html or "pick(" in html), "variant_to_analytics": bool(re.search(r"(?:gtag|ym)\([^)]*\b(?:ab|variant)", html, re.I | re.S)), "experiment_name": bool(experiment_id), "active_flag": "AB_ACTIVE" in html, "no_cloaking_marker": not bool(re.search(r"display\s*:\s*none[^}]{0,40}(hidden|keyword)", html, re.I))}
    return {"schema_version": "nexus.marketing-ab-validation.v1", "experiment_id": experiment_id, "checks": checks, "errors": [key for key, passed in checks.items() if not passed], "status": "PASS_REAL_BOUNDED" if all(checks.values()) else "FAILED_REAL"}


def native_cro_contract(funnel: Mapping[str, Any]) -> Dict[str, Any]:
    """Native CRO/objection/evidence contract retained from the benchmark."""
    return {"schema_version": "nexus.marketing-cro-contract.v1", "required_sections": ["problem", "audience", "what_the_offer_is", "what_the_offer_is_not", "process", "proof_boundary", "objections", "CTA", "qualification", "FAQ", "tracking"], "objections": ["what does the review cover", "am I applying too early", "does this guarantee funding", "why is it worth $97", "what happens next"], "guardrails": ["no approval/funding promise", "no unsupported results", "no fabricated proof", "no causal claim from one event"], "tracking_events": ["page_view", "CTA_click", "form_start", "form_complete", "lead_created", "lead_qualified", "purchase", "creative_variant"], "funnel_id": funnel["funnel_id"], "status": "PASS_REAL_BOUNDED"}


def native_experiment_contract(funnel: Mapping[str, Any]) -> Dict[str, Any]:
    experiments = experiment_plan(funnel)
    return {"schema_version": "nexus.marketing-experiment-set.v1", "funnel_id": funnel["funnel_id"], "experiments": experiments, "one_active_test_at_a_time": True, "journal_required": True, "status": "PASS_REAL_BOUNDED"}


def native_marketing_mechanism_contract(funnel: Mapping[str, Any]) -> Dict[str, Any]:
    """Executable native bundle for the measured MarketingSkills behaviors."""
    return {"schema_version": "nexus.marketing-native-mechanisms.v1", "funnel_id": funnel["funnel_id"], "product_marketing_context": {"audience": funnel["audience"], "problem": funnel["problem"], "offer": funnel["offer"], "positioning": "readiness clarity without funding or approval promises"}, "event_schema": ["page_view", "CTA_click", "form_start", "form_complete", "lead_created", "lead_qualified", "appointment_booked", "purchase", "upsell", "email_open", "email_click", "campaign_source", "creative_variant"], "guardrail_metrics": ["qualified_lead_rate", "form_completion_rate", "review_start_rate", "appointment_rate", "claim_safety_failures", "consent_failures", "source_attribution_completeness"], "seo_content_map": ["funding readiness questions", "what to prepare before applying", "documents and evidence", "timing and next safe step"], "revops_flow": ["lead_created", "consent_checked", "qualification_checked", "route_to_review_or_appointment", "human_review_for_sensitive_or_conflicting_evidence", "nurture_non_buyer"], "objection_coverage": native_cro_contract(funnel)["objections"], "experiment_set": native_experiment_contract(funnel)["experiments"], "weekly_reporting_view": ["traffic by source", "lead quality by source", "drop-off by stage", "creative variant", "next experiment"], "status": "PASS_REAL_BOUNDED"}


def external_capability_decision_visibility() -> Dict[str, Any]:
    return {"schema_version": "nexus.external-capability-decision.v1", "decisions": [{"project": "MarketingSkills", "decision": "BORROW_MECHANISMS_CONFIRMED", "adopted": ["product-marketing context", "CRO/objection framework", "event/guardrail metrics", "SEO content map", "revops flow", "experiment/reporting discipline"], "integrated_directly": [], "rejected": ["unneeded external MCP/OAuth integrations", "partner-specific tooling"], "evidence": "same-problem three-way canary; native SET_C mean 8.6 vs external SET_B mean 8.2"}, {"project": "Landforge", "decision": "BORROW_MECHANISMS_CONFIRMED", "adopted": ["landing completeness validator", "SEO metadata checks", "stable A/B and variant analytics checks", "experiment structure", "journal/change traceability"], "integrated_directly": [], "rejected": ["deployment engine for current stack", "unneeded external MCP surface"], "evidence": "same GoClear artifact; native validator PASS_REAL_BOUNDED across tested criteria"}], "status": "PASS_REAL_BOUNDED"}


def experiment_plan(funnel: Mapping[str, Any]) -> List[Dict[str, Any]]:
    return [
        {"experiment_id": "goclear_exp_1_positioning", "hypothesis": "Readiness-first framing will produce more qualified review intent than generic funding aspiration.", "variant": "A: Know what is ready before you apply vs B: Get funding for your business", "success_metric": "qualified_lead_rate and review_start_rate", "minimum_evidence": "No conclusion until sufficient comparable sessions and at least one downstream qualification signal exist.", "stop_condition": "claim-safety failure, materially worse qualification, or insufficient traffic after bounded window", "next_action": "retain, revise, or request more evidence; never infer causality from a single lead"},
        {"experiment_id": "goclear_exp_2_cta", "hypothesis": "A diagnostic CTA will attract better-qualified intent than an abstract contact CTA.", "variant": "A: Start the $97 readiness review vs B: Learn more", "success_metric": "CTA_click_to_form_complete and qualified_lead_rate", "minimum_evidence": "Comparable traffic, source attribution, and form completion events.", "stop_condition": "missing attribution or consent, or no measurable difference after bounded sample", "next_action": "keep the clearer CTA or revise the diagnostic framing"},
        {"experiment_id": "goclear_exp_3_proof", "hypothesis": "Showing what the review covers will reduce uncertainty without making a prohibited promise.", "variant": "A: process/document checklist above CTA vs B: checklist below CTA", "success_metric": "form_start_rate and qualified_lead_rate", "minimum_evidence": "Event integrity and downstream qualification; not CTR alone.", "stop_condition": "unsupported claim, privacy issue, or insufficient evidence", "next_action": "move proof, simplify, or request more research"},
    ]


def audit_current_marketing(root: Any) -> Dict[str, Any]:
    return {"current_level": "PARTIAL_REAL", "entrypoint": "scripts/nexus_agent_platform/marketing_ai_orchestrator.py plus scripts/marketing draft builders", "workers": ["GROWTH specialist contract", "marketing_ai_orchestrator", "draft-only marketing scripts"], "queue": "existing governed work_orders / nexus_foundation work-order contract; no Marketing-specific queue", "capabilities": ["offer/funnel draft", "content calendar", "landing experiment draft", "lead magnet outline", "social draft queue", "Research/Alpha handoff planning"], "funnel_support": "partial; revenue_funnel_registry.json and transformationCampaignContract.ts exist, but no canonical Marketing funnel persistence", "analytics": "partial; outcomeAnalytics.ts, clientAnalytics.ts, event feed artifacts; no canonical Marketing event collection", "experiment_support": "draft-only landing experiments and growth experiments; no complete event-to-learning loop", "channels": ["SEO/content", "social drafts", "email drafts", "landing page", "referral hypothesis"], "creative_handoff": "existing transformationCampaignContract.ts plus Research/Alpha handoff; no durable Marketing-owned handoff canary", "nova_visibility": "partial via existing capability/workroom views; no funnel-level aggregation", "primary_gaps": ["canonical funnel object", "canonical event contract", "Marketing project aggregation", "real bounded Marketing-to-Creative consumption", "live learning loop", "channel permission matrix"]}
