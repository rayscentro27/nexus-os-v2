"""Typed Marketing tools registered in the existing Nexus MCP.

Marketing owns its own logic; Nova only reads it. All calculation lives in the
authoritative Marketing engine (scripts.marketing.engine) backed by the single
Marketing SQLite authority. No raw SQL, shell, filesystem, credentials, or raw
tokens are exposed. Planning/measurement are bounded internal writes with no
external effect; paid spend and publishing stay Ray-gated as approval cards.
"""
from __future__ import annotations

import json
from typing import Any

from .auth import authorize_action, authorize_read

MARKETING_TOOL_NAMES = (
    "marketing_status", "marketing_connections", "marketing_campaign_status",
    "marketing_performance", "marketing_market_feedback", "marketing_creative_request",
    "marketing_nova_summary",
    "marketing_opportunity_intake", "marketing_record_performance", "marketing_record_feedback",
)


def _engine():
    from scripts.marketing import engine
    return engine


def register_marketing_tools(mcp: Any) -> None:
    @mcp.tool(name="marketing_status", description=(
        "Read-only Marketing engine status: campaign counts by lifecycle state and recommended next action, "
        "connection count, market-intelligence record count, mission (MONETIZE_NEXUS), and the organic-first policy."))
    def marketing_status() -> dict[str, Any]:
        authorize_read("marketing_status")
        return _engine().status()

    @mcp.tool(name="marketing_connections", description=(
        "Read-only Marketing outside-world connection registry. Each row names the revenue or market-intelligence "
        "workflow it enables, with read/write/publish/analytics availability, auth state, approval requirement, cost, "
        "and status. Nothing is claimed active until verified."))
    def marketing_connections() -> dict[str, Any]:
        authorize_read("marketing_connections")
        return _engine().connections()

    @mcp.tool(name="marketing_campaign_status", description=(
        "Read one Marketing campaign acquisition plan for an existing opportunity: audience, positioning, offer, "
        "channel selection, funnel, landing-page requirements, CTA, organic/paid strategy, attribution and measurement "
        "plans, approval requirements, and the recommended next action. Internal IDs suppressed unless diagnostics."))
    def marketing_campaign_status(opportunity_id: str = "", campaign_id: str = "",
                                  diagnostics: bool = False) -> dict[str, Any]:
        authorize_read("marketing_campaign_status")
        return _engine().get_campaign(opportunity_id=opportunity_id, campaign_id=campaign_id,
                                      include_internal_ids=diagnostics)

    @mcp.tool(name="marketing_performance", description=(
        "Read-only campaign performance for an existing opportunity: forecast (from the Business Opportunities handoff) "
        "vs actuals recorded by Marketing, the performance ledger size, and the current recommended next action. "
        "Unknowns remain UNKNOWN; Marketing never recomputes the commercial forecast."))
    def marketing_performance(opportunity_id: str = "", diagnostics: bool = False) -> dict[str, Any]:
        authorize_read("marketing_performance")
        return _engine().performance(opportunity_id, include_internal_ids=diagnostics)

    @mcp.tool(name="marketing_market_feedback", description=(
        "Read-only structured market-intelligence Marketing has observed (customer questions/objections, search terms, "
        "competitor campaigns, conversion behavior, winning hooks). Feeds future Research/Business Opportunities/Creative "
        "without dumping raw Marketing data across engines."))
    def marketing_market_feedback(opportunity_id: str = "", limit: int = 50,
                                  diagnostics: bool = False) -> dict[str, Any]:
        authorize_read("marketing_market_feedback")
        return _engine().market_feedback(opportunity_id=opportunity_id, limit=limit,
                                         include_internal_ids=diagnostics)

    @mcp.tool(name="marketing_creative_request", description=(
        "Read-only Marketing -> Creative request contract for an existing opportunity (audience, problem, emotional "
        "driver, positioning, offer, channel, format, hook, message, CTA, asset and landing-page requirements, objective, "
        "success metric). CREATIVE CREATES; MARKETING DEPLOYS, MEASURES, AND OPTIMIZES. Does not build Creative."))
    def marketing_creative_request(opportunity_id: str = "", campaign_id: str = "",
                                   diagnostics: bool = False) -> dict[str, Any]:
        authorize_read("marketing_creative_request")
        return _engine().creative_request(opportunity_id=opportunity_id, campaign_id=campaign_id,
                                          include_internal_ids=diagnostics)

    @mcp.tool(name="marketing_nova_summary", description=(
        "Read-only Nova-readable Marketing summary for an existing opportunity: what is being monetized, status, "
        "channels, approval items, creative/attribution/measurement readiness, forecast-vs-actual, and the recommended "
        "next action (SCALE/CONTINUE/MODIFY/HOLD/STOP). Marketing logic stays in Marketing, not Nova."))
    def marketing_nova_summary(opportunity_id: str = "", campaign_id: str = "",
                               diagnostics: bool = False) -> dict[str, Any]:
        authorize_read("marketing_nova_summary")
        return _engine().nova_summary(opportunity_id=opportunity_id, campaign_id=campaign_id,
                                      include_internal_ids=diagnostics)

    @mcp.tool(name="marketing_opportunity_intake", description=(
        "Consume the certified Business Opportunities -> Marketing handoff for an existing opportunity and produce a "
        "complete acquisition plan (audience, positioning, channel selection, funnel, landing-page requirements, CTA, "
        "organic-first + bounded-paid-test strategy, attribution plan, measurement plan, Creative request, approval "
        "requirements, and a recommended next action). Autonomous planning only: bounded internal write, no spend, no "
        "publishing, no external account activation. Idempotent per opportunity."))
    def marketing_opportunity_intake(opportunity_id: str) -> dict[str, Any]:
        authorize_action("marketing_opportunity_intake")
        try:
            return _engine().intake(opportunity_id)
        except (TypeError, ValueError, KeyError) as exc:
            return {"status": "REJECTED", "reason": str(exc)[:240]}

    @mcp.tool(name="marketing_record_performance", description=(
        "Record measured actuals for already-authorized campaign activity on an existing opportunity (impressions, "
        "clicks, leads, conversions, spend, revenue, ROAS, etc.) and refresh the recommended next action. Only supplied "
        "numeric fields are stored; nothing is fabricated. Does not spend money or publish."))
    def marketing_record_performance(opportunity_id: str, window: str = "LIVE",
                                     metrics_json: str = "", source: str = "") -> dict[str, Any]:
        authorize_action("marketing_record_performance")
        try:
            metrics = json.loads(metrics_json) if metrics_json else {}
            if not isinstance(metrics, dict) or len(metrics_json.encode("utf-8")) > 8000:
                raise ValueError("metrics_must_be_a_bounded_json_object")
            return _engine().record_performance(opportunity_id, window, metrics, source=source)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            return {"status": "REJECTED", "reason": str(exc)[:240]}

    @mcp.tool(name="marketing_record_feedback", description=(
        "Record one structured market-intelligence observation (customer question/objection, search term, competitor "
        "campaign, conversion behavior, winning hook) tied to an opportunity/campaign. Bounded internal write."))
    def marketing_record_feedback(intel_type: str, observation: str, opportunity_id: str = "",
                                  campaign_id: str = "", source: str = "",
                                  structured_json: str = "") -> dict[str, Any]:
        authorize_action("marketing_record_feedback")
        try:
            structured = json.loads(structured_json) if structured_json else {}
            if not isinstance(structured, dict) or len(structured_json.encode("utf-8")) > 8000:
                raise ValueError("structured_must_be_a_bounded_json_object")
            return _engine().record_feedback(intel_type, observation, opportunity_id=opportunity_id,
                                             campaign_id=campaign_id, structured=structured, source=source)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            return {"status": "REJECTED", "reason": str(exc)[:240]}
