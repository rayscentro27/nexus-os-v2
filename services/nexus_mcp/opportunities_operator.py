"""Typed Business Opportunities tools registered in the existing Nexus MCP."""
from __future__ import annotations

import json
from typing import Any, Literal

from .auth import authorize_action, authorize_read

OpportunityType = Literal[
    "AFFILIATE", "CONSULTING", "SERVICE", "DIGITAL_PRODUCT", "SAAS", "LEAD_GENERATION",
    "PROCUREMENT", "ECOMMERCE", "CONTENT_MONETIZATION", "PARTNERSHIP", "LICENSING_API",
    "SPONSORSHIP", "MARKETPLACE", "OTHER",
]
DeliveryModel = Literal[
    "ONLINE_ONLY", "LOCAL_SERVICE", "MOBILE_SERVICE", "HYBRID", "PHYSICAL_LOCATION",
    "REMOTE_SERVICE", "MARKETPLACE", "PARTNER_FULFILLED",
]
SourceType = Literal[
    "RESEARCH_R10", "NOVA_MANUAL", "RAY_MANUAL", "OPENAFFILIATE", "GITHUB",
    "PROCUREMENT", "SOCIAL_DISCOVERY", "SEO_DEMAND", "OTHER",
]
VerificationState = Literal["VERIFIED", "PARTIAL", "UNVERIFIED", "CONFLICTING"]
ClaimType = Literal[
    "COMMISSION_RATE", "COOKIE_DURATION", "MARKET_DEMAND", "ESTIMATED_MARGIN", "STARTUP_COST",
    "CUSTOMER_NEED", "COMPETITION", "APPROVAL_REQUIREMENTS", "PAYMENT_TERMS", "LEGAL_RESTRICTION",
    "TRAFFIC_REQUIREMENT", "EXPECTED_CONVERSION", "LAB_PARTNER_REQUIREMENT",
    "REFERRAL_PARTNER_REQUIREMENT", "LOCAL_DEMAND", "REGULATORY_REQUIREMENT",
]
OPPORTUNITIES_TOOL_NAMES = (
    "opportunities_health", "opportunities_status", "opportunities_list", "opportunities_get",
    "opportunities_search", "opportunities_top", "opportunities_latest", "opportunities_scorecard",
    "opportunities_evidence", "opportunities_needs_research", "opportunities_history",
    "opportunities_submit", "opportunities_evaluate", "opportunities_score",
    "opportunities_update_state", "opportunities_attach_evidence", "opportunities_request_research",
    "opportunities_accept_research_handoff",
    "opportunities_commercial_synthesis", "opportunities_marketing_handoff",
)


def _engine():
    from scripts.opportunities import engine
    return engine


def _public(value: Any, *, diagnostics: bool = False) -> Any:
    return _engine()._public(value, include_internal_ids=diagnostics)


def _resolve(opportunity_id: str, title: str) -> str | None:
    return _engine().resolve_reference(opportunity_id, title)


def _parse_object(text: str, *, allowed: set[str], max_bytes: int = 8000) -> dict[str, Any]:
    if not text:
        return {}
    if len(text.encode("utf-8")) > max_bytes:
        raise ValueError("structured_input_exceeds_bound")
    value = json.loads(text)
    if not isinstance(value, dict) or set(value) - allowed:
        raise ValueError("structured_input_contains_unrecognized_fields")
    return value


def register_opportunities_tools(mcp: Any) -> None:
    @mcp.tool(name="opportunities_health", description=(
        "Read-only production health for the Nexus Business Opportunities engine: SQLite integrity/schema/count, "
        "OpenAffiliate query availability, current Research R10 interface health, and registered Nexus MCP exposure."))
    def opportunities_health() -> dict[str, Any]:
        authorize_read("opportunities_health")
        return _public(_engine().health())

    @mcp.tool(name="opportunities_status", description="Read-only opportunity lifecycle counts, types, schema and latest evaluation time.")
    def opportunities_status() -> dict[str, Any]:
        authorize_read("opportunities_status")
        return _public(_engine().status())

    @mcp.tool(name="opportunities_list", description="List current opportunities with optional status/type/delivery filters. Internal record identifiers are suppressed.")
    def opportunities_list(status: str = "", opportunity_type: str = "", delivery_model: str = "",
                           limit: int = 20, diagnostics: bool = False) -> dict[str, Any]:
        authorize_read("opportunities_list")
        return {"status": "OK", "items": _public(_engine().list_opportunities(
            status=status, opportunity_type=opportunity_type, delivery_model=delivery_model,
            limit=limit), diagnostics=diagnostics)}

    @mcp.tool(name="opportunities_get", description="Read one opportunity by exact title or internal diagnostic reference. Normal output hides all internal IDs.")
    def opportunities_get(opportunity_id: str = "", title: str = "", diagnostics: bool = False) -> dict[str, Any]:
        authorize_read("opportunities_get")
        result = _engine().get(opportunity_id, title, include_internal_ids=diagnostics)
        return {"status": "OK" if result else "NOT_FOUND", "opportunity": result}

    @mcp.tool(name="opportunities_search", description=(
        "Search the Nexus Opportunity Library, or query a small bounded set of OpenAffiliate candidates using its public read-only REST API. "
        "OpenAffiliate records are candidates only; no program is joined or activated."))
    def opportunities_search(query: str = "", opportunity_type: str = "", delivery_model: str = "",
                             geographic_scope: str = "", source: Literal["LIBRARY", "OPENAFFILIATE"] = "LIBRARY",
                             source_category: str = "", limit: int = 10) -> dict[str, Any]:
        authorize_read("opportunities_search")
        if source == "OPENAFFILIATE":
            from scripts.opportunities.source_adapters.openaffiliate import search as oa_search
            result = oa_search(keyword=query, category=source_category or opportunity_type, limit=limit)
            candidates = []
            for item in result["programs"]:
                candidate = {**item, "program_ref": item.get("source_external_id")}
                candidates.append(_public(candidate))
            return {"status": "OK", "source": "OpenAffiliate", "items": candidates,
                    "count": len(candidates), "note": "Unjoined candidate records; verify terms before action."}
        if source != "LIBRARY":
            return {"status": "REJECTED", "reason": "UNSUPPORTED_SEARCH_SOURCE"}
        return {"status": "OK", "items": _engine().search(
            query, opportunity_type=opportunity_type, delivery_model=delivery_model,
            geographic_scope=geographic_scope, limit=limit)}

    @mcp.tool(name="opportunities_top", description="Read the highest-scored active Nexus opportunities; score and confidence are shown without internal IDs.")
    def opportunities_top(limit: int = 5) -> dict[str, Any]:
        authorize_read("opportunities_top")
        items = _engine().top(limit)
        return {"status": "OK", "items": items, "count": len(items)}

    @mcp.tool(name="opportunities_latest", description="Read the most recently updated opportunity, with internal identifiers suppressed.")
    def opportunities_latest() -> dict[str, Any]:
        authorize_read("opportunities_latest")
        item = _engine().latest()
        return {"status": "OK" if item else "EMPTY", "opportunity": item}

    @mcp.tool(name="opportunities_scorecard", description="Read the latest stored commercial scorecard and documented assumptions for one opportunity.")
    def opportunities_scorecard(opportunity_id: str = "", title: str = "") -> dict[str, Any]:
        authorize_read("opportunities_scorecard")
        oid = _resolve(opportunity_id, title)
        if not oid:
            return {"status": "NOT_FOUND"}
        card = _engine().scorecard(oid)
        return {"status": "OK" if card else "NOT_SCORED", "scorecard": card}

    @mcp.tool(name="opportunities_evidence", description="Read source-linked evidence, verification quality, and conflicts for one opportunity.")
    def opportunities_evidence(opportunity_id: str = "", title: str = "") -> dict[str, Any]:
        authorize_read("opportunities_evidence")
        oid = _resolve(opportunity_id, title)
        if not oid:
            return {"status": "NOT_FOUND"}
        return {"status": "OK", "evidence": _public(_engine().evidence(oid))}

    @mcp.tool(name="opportunities_needs_research", description="List opportunities with missing evidence or an existing Research request.")
    def opportunities_needs_research(limit: int = 20) -> dict[str, Any]:
        authorize_read("opportunities_needs_research")
        return {"status": "OK", "items": _engine().needs_research(limit)}

    @mcp.tool(name="opportunities_history", description="Read lifecycle and evidence history for one opportunity; internal event IDs are suppressed.")
    def opportunities_history(opportunity_id: str = "", title: str = "", limit: int = 50) -> dict[str, Any]:
        authorize_read("opportunities_history")
        oid = _resolve(opportunity_id, title)
        if not oid:
            return {"status": "NOT_FOUND"}
        return {"status": "OK", "events": _public(_engine().history(oid, limit))}

    @mcp.tool(name="opportunities_submit", description=(
        "Submit one commercial opportunity candidate from a supported source. Normalizes type/delivery, deduplicates using business identity, "
        "type, source/program ID, domain and geography, attaches provenance, and records history. Never spends, joins programs, signs, publishes, or bids."))
    def opportunities_submit(
        title: str,
        opportunity_type: OpportunityType,
        summary: str,
        source_type: SourceType,
        subcategory: str = "",
        candidate_name: str = "",
        target_customer: str = "",
        revenue_model: str = "",
        revenue_details_json: str = "",
        startup_cost_estimate: float | None = None,
        time_to_first_revenue_days: int | None = None,
        capability_fit: str = "",
        audience_fit: str = "",
        automation_potential: str = "",
        delivery_model: DeliveryModel | None = None,
        online_offline_mix: str = "",
        geographic_scope: str = "",
        physical_presence_required: bool | None = None,
        customer_interaction_mode: str = "",
        inventory_required: str = "",
        equipment_required: str = "",
        licensed_partner_required: bool | None = None,
        partner_type: str = "",
        facility_required: bool | None = None,
        vehicle_required: bool | None = None,
        local_marketing_dependency: str = "",
        referral_partner_dependency: str = "",
        regulatory_complexity: str = "",
        scalability_model: str = "",
        asset_light_score: float | None = None,
        partner_fulfilled: bool | None = None,
        source_name: str = "",
        source_reference: str = "",
        source_external_id: str = "",
        source_summary: str = "",
        verification_state: VerificationState = "UNVERIFIED",
        website: str = "",
        partner_program_id: str = "",
        risks_json: str = "",
        diagnostics: bool = False,
    ) -> dict[str, Any]:
        authorize_action("opportunities_submit")
        try:
            revenue = _parse_object(revenue_details_json, allowed={"commission", "payout", "unit_cost",
                "pricing_model", "one_time", "recurring", "currency"})
            risks = json.loads(risks_json) if risks_json else []
            if not isinstance(risks, list) or len(risks) > 20 or any(
                    not isinstance(risk, dict) or set(risk) - {"risk_type", "severity", "description", "mitigation", "requires_ray_approval"}
                    for risk in risks):
                raise ValueError("risk_entries_must_use_the_bounded_risk_schema")
            result = _engine().submit({
                "title": title, "opportunity_type": opportunity_type, "summary": summary,
                "source_type": source_type, "subcategory": subcategory, "candidate_name": candidate_name,
                "target_customer": target_customer, "revenue_model": revenue_model, "revenue_details": revenue,
                "startup_cost_estimate": startup_cost_estimate, "time_to_first_revenue_days": time_to_first_revenue_days,
                "capability_fit": capability_fit, "audience_fit": audience_fit,
                "automation_potential": automation_potential, "delivery_model": delivery_model,
                "online_offline_mix": online_offline_mix, "geographic_scope": geographic_scope,
                "physical_presence_required": physical_presence_required,
                "customer_interaction_mode": customer_interaction_mode, "inventory_required": inventory_required,
                "equipment_required": equipment_required, "licensed_partner_required": licensed_partner_required,
                "partner_type": partner_type, "facility_required": facility_required, "vehicle_required": vehicle_required,
                "local_marketing_dependency": local_marketing_dependency,
                "referral_partner_dependency": referral_partner_dependency,
                "regulatory_complexity": regulatory_complexity, "scalability_model": scalability_model,
                "asset_light_score": asset_light_score, "partner_fulfilled": partner_fulfilled,
                "source_name": source_name, "source_reference": source_reference,
                "source_external_id": source_external_id, "source_summary": source_summary,
                "verification_state": verification_state, "website": website,
                "partner_program_id": partner_program_id, "risks": risks,
            })
            return _public(result, diagnostics=diagnostics)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            return {"status": "REJECTED", "reason": str(exc)[:240]}

    @mcp.tool(name="opportunities_evaluate", description="Evaluate evidence sufficiency, risks, and source gaps. Missing facts remain unknown; output includes evidence-aware 30/60/90-day plans without invented revenue projections.")
    def opportunities_evaluate(opportunity_id: str = "", title: str = "", diagnostics: bool = False) -> dict[str, Any]:
        authorize_action("opportunities_evaluate")
        oid = _resolve(opportunity_id, title)
        if not oid:
            return {"status": "NOT_FOUND"}
        return _public(_engine().evaluate(oid), diagnostics=diagnostics)

    @mcp.tool(name="opportunities_score", description="Append one weighted 100-point commercial score to immutable score history. Unknown dimensions stay excluded and asset-light bonus is a separate capped tie-breaker.")
    def opportunities_score(
        opportunity_id: str = "",
        title: str = "",
        revenue_potential_score: float | None = None,
        monetization_probability_score: float | None = None,
        time_to_revenue_score: float | None = None,
        capability_fit_score: float | None = None,
        audience_fit_score: float | None = None,
        startup_cost_efficiency_score: float | None = None,
        automation_potential_score: float | None = None,
        competitive_barrier_score: float | None = None,
        evidence_quality_score: float | None = None,
        asset_light_bonus: float | None = None,
        confidence: Literal["LOW", "MEDIUM", "HIGH"] = "LOW",
        assumptions_json: str = "",
    ) -> dict[str, Any]:
        authorize_action("opportunities_score")
        oid = _resolve(opportunity_id, title)
        if not oid:
            return {"status": "NOT_FOUND"}
        try:
            assumptions = _parse_object(assumptions_json, allowed={"assumptions", "unknown_dimensions",
                "evidence_references", "notes"})
            return _public(_engine().score(oid, {
                "revenue_potential_score": revenue_potential_score,
                "monetization_probability_score": monetization_probability_score,
                "time_to_revenue_score": time_to_revenue_score,
                "capability_fit_score": capability_fit_score, "audience_fit_score": audience_fit_score,
                "startup_cost_efficiency_score": startup_cost_efficiency_score,
                "automation_potential_score": automation_potential_score,
                "competitive_barrier_score": competitive_barrier_score,
                "evidence_quality_score": evidence_quality_score, "asset_light_bonus": asset_light_bonus,
            }, confidence=confidence, assumptions=assumptions))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            return {"status": "REJECTED", "reason": str(exc)[:240]}

    @mcp.tool(name="opportunities_update_state", description="Change one opportunity lifecycle state with a recorded reason; this does not authorize external business actions.")
    def opportunities_update_state(
        new_state: Literal["DISCOVERED", "NORMALIZED", "NEEDS_RESEARCH", "RESEARCH_PENDING",
            "READY_TO_SCORE", "SCORED", "UNDER_REVIEW", "EXPERIMENT_PENDING", "ACTIVE",
            "COMPLETED", "ARCHIVED", "REJECTED"],
        reason: str,
        opportunity_id: str = "",
        title: str = "",
        recommendation: Literal["", "REJECT", "WATCH", "RESEARCH_MORE", "VALIDATE", "TEST",
            "BUILD", "APPLY", "LAUNCH", "SCALE"] = "",
    ) -> dict[str, Any]:
        authorize_action("opportunities_update_state")
        oid = _resolve(opportunity_id, title)
        if not oid:
            return {"status": "NOT_FOUND"}
        return _public(_engine().update_state(oid, new_state, reason, recommendation=recommendation))

    @mcp.tool(name="opportunities_attach_evidence", description="Attach typed source-linked evidence or an explicit unknown/conflict to one opportunity; preserves provenance and history.")
    def opportunities_attach_evidence(
        claim_type: ClaimType,
        claim: str,
        evidence_value: str = "",
        evidence_quality: Literal["HIGH", "MEDIUM", "LOW", "UNKNOWN"] = "UNKNOWN",
        opportunity_id: str = "",
        title: str = "",
        source_type: SourceType = "OTHER",
        source_name: str = "",
        source_reference: str = "",
        source_external_id: str = "",
        verification_state: VerificationState = "UNVERIFIED",
        verified_by: str = "",
        conflict_state: str = "",
    ) -> dict[str, Any]:
        authorize_action("opportunities_attach_evidence")
        oid = _resolve(opportunity_id, title)
        if not oid:
            return {"status": "NOT_FOUND"}
        return _public(_engine().attach_evidence(oid, {
            "claim_type": claim_type, "claim": claim, "evidence_value": evidence_value,
            "evidence_quality": evidence_quality, "source_type": source_type, "source_name": source_name,
            "source_reference": source_reference, "source_external_id": source_external_id,
            "verification_state": verification_state, "verified_by": verified_by,
            "conflict_state": conflict_state,
        }))

    @mcp.tool(name="opportunities_request_research", description=(
        "Request bounded source research for named missing evidence using the existing Nexus Research assignment interface. "
        "Preserves the same opportunity, is idempotent for the same requested claims, and never writes to Research databases directly."))
    def opportunities_request_research(
        missing_evidence: list[str],
        opportunity_id: str = "",
        title: str = "",
    ) -> dict[str, Any]:
        authorize_action("opportunities_request_research")
        oid = _resolve(opportunity_id, title)
        if not oid:
            return {"status": "NOT_FOUND"}
        return _public(_engine().request_research(oid, missing_evidence))

    @mcp.tool(name="opportunities_accept_research_handoff", description=(
        "Submit one condensed Research package to the existing Business Opportunities receiver gate. "
        "Validates every active Research Deliverable Contract field, records ACCEPTED or exact missing requirements "
        "on the existing opportunity history, and never writes raw evidence to Supabase."))
    def opportunities_accept_research_handoff(opportunity_id: str, handoff_json: str,
                                                research_work_id: str = "") -> dict[str, Any]:
        authorize_action("opportunities_accept_research_handoff")
        allowed = {"from_engine", "to_engine", "case_id", "research_status", "executive_summary",
            "deliverables", "recommended_business_models", "alternative_business_models",
            "target_customers", "customer_need_summary", "market_demand_summary",
            "local_demand_summary", "competition_summary", "competitor_pricing_summary",
            "pricing_inputs_summary", "startup_cost_summary", "operating_cost_summary",
            "partners_summary", "regulatory_summary", "legal_restriction_summary",
            "customer_acquisition_summary", "referral_summary", "technology_summary",
            "open_source_github_summary", "automation_summary", "key_risks",
            "external_boundaries", "unresolved_questions", "source_confidence",
            "evidence_quality", "local_detail_pointer", "evidence_count", "summary_version",
            "generated_at"}
        try:
            handoff = _parse_object(handoff_json, allowed=allowed, max_bytes=24000)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            return {"status": "REJECTED", "reason": str(exc)[:180]}
        return _public(_engine().accept_research_handoff(
            opportunity_id, handoff, research_work_id=research_work_id))

    @mcp.tool(name="opportunities_commercial_synthesis", description=(
        "Read-only consolidated commercial synthesis for one existing opportunity, computed by the authoritative "
        "Business Opportunities engine: monetization model, unit economics, break-even model, downside/base/upside "
        "scenarios, 30/60/90-day revenue scenarios, estimated time to launch, estimated time to first revenue, "
        "low-capital test, commercial recommendation, named missing inputs, and external boundaries. Unknowns stay "
        "UNKNOWN, missing evidence stays named, and no number is fabricated. Internal identifiers are suppressed."))
    def opportunities_commercial_synthesis(opportunity_id: str = "", title: str = "",
                                           diagnostics: bool = False) -> dict[str, Any]:
        authorize_read("opportunities_commercial_synthesis")
        oid = _resolve(opportunity_id, title)
        if not oid:
            return {"status": "NOT_FOUND"}
        return {"status": "OK", "commercial_synthesis": _engine().commercial_synthesis(
            oid, include_internal_ids=diagnostics)}

    @mcp.tool(name="opportunities_marketing_handoff", description=(
        "Read-only condensed Business Opportunities -> Marketing handoff package for one existing opportunity, built "
        "by the authoritative engine so Marketing can consume a finished commercial case without direct SQLite access. "
        "Local SQLite stays authoritative; Supabase is only a coordination layer and no raw Research evidence is "
        "included. Unknowns stay UNKNOWN and missing inputs stay named. Internal identifiers are suppressed unless "
        "an authorized caller requests diagnostics."))
    def opportunities_marketing_handoff(opportunity_id: str = "", title: str = "",
                                        diagnostics: bool = False) -> dict[str, Any]:
        authorize_read("opportunities_marketing_handoff")
        oid = _resolve(opportunity_id, title)
        if not oid:
            return {"status": "NOT_FOUND"}
        return {"status": "OK", "marketing_handoff": _engine().marketing_handoff(
            oid, include_internal_ids=diagnostics)}

