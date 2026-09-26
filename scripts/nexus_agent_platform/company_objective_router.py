"""Company-level objective planning over the canonical Nexus routes.

This is intentionally a planning/router layer: it chooses governed specialists,
orders handoffs, and records approval boundaries. It does not publish, spend,
submit financial applications, or place live trades.
"""
from __future__ import annotations

import re
import hashlib
from datetime import datetime, timezone
from typing import Any

from .department_router import classify_intent, resolve


def _contains(text: str, *terms: str) -> bool:
    value = text.lower()
    return any(term in value for term in terms)


def build_root_objective(text: str, *, conversation_message_id: str | int | None = None,
                         submitted_by: str = "RAY", submitted_at: str | None = None) -> dict[str, Any]:
    """Group an entire direct message as one root; headings are requirements."""
    clean = text.strip()
    stable = f"{conversation_message_id or ''}:{clean}".encode("utf-8")
    objective_id = "root_" + hashlib.sha256(stable).hexdigest()[:20]
    requirements: list[dict[str, str]] = []
    current = "General requirements"
    body: list[str] = []
    for raw in clean.splitlines():
        line = raw.strip().strip("#").strip()
        if not line:
            continue
        heading = re.match(r"^(?:\d+[.)]\s*)?([A-Z][A-Z _/&-]{2,})$", line)
        if heading:
            if body:
                requirements.append({"section": current, "text": " ".join(body)[:1000]})
                body = []
            current = heading.group(1).title()
        else:
            body.append(line)
    if body:
        requirements.append({"section": current, "text": " ".join(body)[:1000]})
    return {
        "objective_id": objective_id,
        "objective_source": "RAY",
        "objective_source_type": "DIRECT_MESSAGE",
        "submitted_by": submitted_by,
        "submitted_at": submitted_at or datetime.now(timezone.utc).isoformat(),
        "conversation_message_id": conversation_message_id,
        "explicit_intent": True,
        "parent_objective_id": None,
        "requirements": requirements or [{"section": "General requirements", "text": clean[:1000]}],
    }


def route_company_objective(text: str, *, conversation_message_id: str | int | None = None) -> dict[str, Any]:
    """Return a durable, context-preserving company work plan for one objective."""
    clean = re.sub(r"\s+", " ", text.strip())[:500]
    root_objective = build_root_objective(text, conversation_message_id=conversation_message_id)
    intent = classify_intent(clean)
    base = resolve(clean)
    steps: list[dict[str, Any]] = []
    approvals: list[str] = []

    if _contains(clean, "create a campaign", "campaign for", "make one version funny"):
        steps = [
            {"order": 1, "owner": "RESEARCH_ALPHA", "specialist": "ALPHA", "action": "reuse_current_audience_and_pattern_intelligence", "authority": "read_only"},
            {"order": 2, "owner": "MARKETING_CREATIVE", "specialist": "GROWTH", "action": "define_strategy_hooks_offer_and_cta", "authority": "draft_only"},
            {"order": 3, "owner": "MARKETING_CREATIVE", "specialist": "CREATIVE", "action": "generate_video_image_and_social_variations", "authority": "draft_only"},
            {"order": 4, "owner": "OPERATIONS", "specialist": "JAX", "action": "bind_landing_page_and_funnel_handoff", "authority": "internal_execution"},
            {"order": 5, "owner": "GOVERNANCE_REVIEW", "specialist": "NOVA", "action": "assemble_admin_review_package", "authority": "human_review"},
        ]
        approvals = ["Ray approval before publication, paid traffic, or external outreach."]
    elif intent == "OPPORTUNITY_INTAKE" or _contains(clean, "idea", "opportunity"):
        steps = [
            {"order": 1, "owner": "RESEARCH_ALPHA", "specialist": "ALPHA", "action": "research_and_challenge_opportunity", "authority": "read_only"},
            {"order": 2, "owner": "OPERATIONS", "specialist": "NOVA", "action": "create_company_objective_and_work_order", "authority": "internal_execution"},
            {"order": 3, "owner": "CREDIT_BUSINESS_FUNDING", "specialist": "ALPHA", "action": "model_economics_and_risk_if_relevant", "authority": "internal_review"},
            {"order": 4, "owner": "MARKETING_CREATIVE", "specialist": "GROWTH", "action": "prepare_draft_offer_and_campaign_if_test_warrants", "authority": "draft_only"},
            {"order": 5, "owner": "GOVERNANCE_REVIEW", "specialist": "NOVA", "action": "assemble_ray_review_package", "authority": "human_review"},
        ]
        approvals = ["Ray approval before external store, paid service, advertising, contract, or publication."]
    elif intent == "TRADING_PREMARKET" or _contains(clean, "market open", "premarket", "pre-market"):
        steps = [
            {"order": 1, "owner": "RESEARCH_ALPHA", "specialist": "TRADING_ENGINE", "action": "read_current_practice_market_data_and_prepare_watchlist", "authority": "read_only"},
            {"order": 2, "owner": "RESEARCH_ALPHA", "specialist": "ALPHA", "action": "challenge_setup_and_regime_assumptions", "authority": "advisory"},
            {"order": 3, "owner": "GOVERNANCE_REVIEW", "specialist": "NOVA", "action": "surface_waiting_signal_or_risk_rejection", "authority": "human_review"},
        ]
        approvals = ["No live order is permitted; paper execution only until a separate explicit standing authority exists."]
    elif intent == "RESEARCH" and _contains(clean, "low-cost", "low cost", "business opportunity"):
        steps = [
            {"order": 1, "owner": "RESEARCH_ALPHA", "specialist": "ALPHA", "action": "discover_and_verify_low_cost_opportunities", "authority": "read_only"},
            {"order": 2, "owner": "CREDIT_BUSINESS_FUNDING", "specialist": "ALPHA", "action": "compare_startup_cost_margin_and_risk", "authority": "internal_review"},
            {"order": 3, "owner": "OPERATIONS", "specialist": "NOVA", "action": "return_recommendation_and_next_bounded_test", "authority": "internal_execution"},
        ]
        approvals = ["Ray approval before external spend, account creation, or launch."]
    elif _contains(clean, "grant"):
        steps = [
            {"order": 1, "owner": "RESEARCH_ALPHA", "specialist": "ALPHA", "action": "discover_and_verify_current_grants", "authority": "read_only"},
            {"order": 2, "owner": "CREDIT_BUSINESS_FUNDING", "specialist": "CLYDE", "action": "match_requirements_to_client_evidence", "authority": "internal_review"},
            {"order": 3, "owner": "DOCUMENTS", "specialist": "CLYDE", "action": "prepare_document_checklist", "authority": "human_review"},
        ]
        approvals = ["Ray/client approval before any application submission or external communication."]
    elif _contains(clean, "client", "restaurant", "customer"):
        steps = [
            {"order": 1, "owner": "CLIENT_LIFECYCLE", "specialist": "CLYDE", "action": "recover_client_goal_stage_and_next_action", "authority": "human_authority_required"},
            {"order": 2, "owner": "CREDIT_BUSINESS_FUNDING", "specialist": "CLYDE", "action": "readiness_and_funding_gap_analysis", "authority": "internal_review"},
            {"order": 3, "owner": "DOCUMENTS", "specialist": "CLYDE", "action": "document_request_and_status_plan", "authority": "human_review"},
            {"order": 4, "owner": "GOVERNANCE_REVIEW", "specialist": "NOVA", "action": "human_handoff_and_approval_gate", "authority": "human_review"},
        ]
        approvals = ["Client-specific production mutation and external communications require separate authority."]
    else:
        steps = [{"order": 1, "owner": "GOVERNANCE_REVIEW", "specialist": "NOVA", "action": "clarify_or_queue_unresolved_objective", "authority": "human_review"}]
        approvals = ["Objective remains unresolved; no department execution is claimed."]

    return {
        "schema_version": "nexus.company-objective-plan.v1",
        "objective": clean,
        "root_objective": root_objective,
        "intent_class": intent,
        "canonical_route": base,
        "steps": steps,
        "handoff_order": [step["owner"] for step in steps],
        "approval_boundaries": approvals,
        "continuation": "Parent objective remains open until every step has a receipt or a governed blocker.",
        "outcome_integrity": "Plans and test results are not business outcomes; unknown metrics remain UNKNOWN.",
    }
