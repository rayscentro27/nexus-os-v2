"""Typed Creative tools registered in the existing Nexus MCP.

Creative owns its own logic; Nova only reads it. All generation/quality/compliance
lives in the authoritative Creative engine (scripts.creative.creative_engine) backed
by the single Creative SQLite authority. No raw SQL, shell, filesystem, credentials,
or raw tokens are exposed. Intake/feedback are bounded internal writes that generate
copy/script/direction only — no publishing, no spend, no paid-provider calls.
External media generation stops at an approval boundary.
"""
from __future__ import annotations

from typing import Any

from .auth import authorize_action, authorize_read

CREATIVE_TOOL_NAMES = (
    "creative_status", "creative_assets", "creative_marketing_handoff",
    "creative_nova_summary", "creative_feedback",
    "creative_intake", "creative_record_feedback",
)


def _engine():
    from scripts.creative import creative_engine
    return creative_engine


def register_creative_tools(mcp: Any) -> None:
    @mcp.tool(name="creative_status", description=(
        "Read-only Creative engine status: creative-request and asset counts, assets by status, how many are "
        "ready for Marketing, how many are approval-gated media, and feedback-record count. Purpose: make Marketing "
        "strategy executable through high-quality assets."))
    def creative_status() -> dict[str, Any]:
        authorize_read("creative_status")
        return _engine().status()

    @mcp.tool(name="creative_assets", description=(
        "Read one Creative request and its generated assets for an existing opportunity: per-asset type, channel, "
        "format, hook/message/CTA, copy/script, visual/audio/voice/brand direction, status, quality and compliance "
        "checks, approval requirement, and Marketing-handoff readiness. Internal IDs suppressed unless diagnostics."))
    def creative_assets(opportunity_id: str = "", creative_request_id: str = "",
                        diagnostics: bool = False) -> dict[str, Any]:
        authorize_read("creative_assets")
        return _engine().get_creative(opportunity_id=opportunity_id, creative_request_id=creative_request_id,
                                      include_internal_ids=diagnostics)

    @mcp.tool(name="creative_marketing_handoff", description=(
        "Read-only Creative -> Marketing handoff for an existing opportunity: the assets ready for Marketing "
        "(zero-cost copy/script/direction produced inline) plus the media assets still pending Ray approval for "
        "generation. CREATIVE CREATES; MARKETING DEPLOYS, MEASURES, AND OPTIMIZES."))
    def creative_marketing_handoff(opportunity_id: str = "", creative_request_id: str = "",
                                   diagnostics: bool = False) -> dict[str, Any]:
        authorize_read("creative_marketing_handoff")
        return _engine().marketing_handoff(opportunity_id=opportunity_id, creative_request_id=creative_request_id,
                                           include_internal_ids=diagnostics)

    @mcp.tool(name="creative_nova_summary", description=(
        "Read-only Nova-readable Creative summary for an existing opportunity: channel, status, asset counts, what is "
        "ready for Marketing, what is waiting for approval, what needs revision, and the recommended next action. "
        "Creative logic stays in Creative, not Nova."))
    def creative_nova_summary(opportunity_id: str = "", creative_request_id: str = "",
                              diagnostics: bool = False) -> dict[str, Any]:
        authorize_read("creative_nova_summary")
        return _engine().nova_summary(opportunity_id=opportunity_id, creative_request_id=creative_request_id,
                                      include_internal_ids=diagnostics)

    @mcp.tool(name="creative_feedback", description=(
        "Read-only durable creative lessons learned from Marketing performance (winning hook/format/creative, CTR, "
        "conversion, what worked/failed). Creative learns from Marketing without changing Marketing strategy."))
    def creative_feedback(opportunity_id: str = "", limit: int = 50, diagnostics: bool = False) -> dict[str, Any]:
        authorize_read("creative_feedback")
        return _engine().feedback(opportunity_id=opportunity_id, limit=limit, include_internal_ids=diagnostics)

    @mcp.tool(name="creative_intake", description=(
        "Consume the certified Marketing -> Creative request for an existing opportunity and produce a structured "
        "asset plan: channel-aware asset set with generated copy/script and visual/audio/voice/brand direction, plus "
        "quality and compliance checks, status, and approval gating. Autonomous: generates text/direction only — no "
        "publishing, no spend, no paid-provider calls. Media generation is marked APPROVAL_REQUIRED. Idempotent per "
        "opportunity. Does not reinvent Marketing strategy or redo Research."))
    def creative_intake(opportunity_id: str) -> dict[str, Any]:
        authorize_action("creative_intake")
        try:
            return _engine().intake(opportunity_id)
        except (TypeError, ValueError, KeyError) as exc:
            return {"status": "REJECTED", "reason": str(exc)[:240]}

    @mcp.tool(name="creative_record_feedback", description=(
        "Record one Marketing performance-feedback observation for an opportunity (winning hook/format/creative, CTR, "
        "conversion rate, revenue attribution, what worked/failed, lessons) so Creative preserves durable lessons for "
        "future assets. Bounded internal write; does not change Marketing strategy."))
    def creative_record_feedback(opportunity_id: str, winning_hook: str = "", winning_format: str = "",
                                 winning_creative: str = "", ctr: float | None = None,
                                 conversion_rate: float | None = None, revenue_attribution: float | None = None,
                                 customer_response: str = "", what_worked: str = "", what_failed: str = "",
                                 lessons_learned: str = "", asset_id: str = "", campaign_id: str = "") -> dict[str, Any]:
        authorize_action("creative_record_feedback")
        try:
            return _engine().record_feedback(
                opportunity_id, winning_hook=winning_hook, winning_format=winning_format,
                winning_creative=winning_creative, ctr=ctr, conversion_rate=conversion_rate,
                revenue_attribution=revenue_attribution, customer_response=customer_response,
                what_worked=what_worked, what_failed=what_failed, lessons_learned=lessons_learned,
                asset_id=asset_id, campaign_id=campaign_id)
        except (TypeError, ValueError) as exc:
            return {"status": "REJECTED", "reason": str(exc)[:240]}
