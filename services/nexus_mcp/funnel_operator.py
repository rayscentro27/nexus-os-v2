"""Typed Funnel / Landing-Page execution tools registered in the existing Nexus MCP.

The execution layer owns page assembly only. All calculation/strategy lives
upstream (Marketing) and assets upstream (Creative). No raw SQL, shell,
unrestricted filesystem/browser automation, credentials, or raw tokens are
exposed. Building/QA are bounded internal writes with no external effect; preview
and production deploys stay Ray-gated (no auto-publish, no spend).
"""
from __future__ import annotations

from typing import Any

from .auth import authorize_action, authorize_read

FUNNEL_TOOL_NAMES = (
    "funnel_status", "funnel_page", "funnel_qa", "funnel_nova_summary",
    "funnel_build_page",
)


def _engine():
    from scripts.funnel import engine
    return engine


def register_funnel_tools(mcp: Any) -> None:
    @mcp.tool(name="funnel_status", description=(
        "Read-only Funnel/Landing-Page execution-layer status: page counts by status and funnel type, how many passed "
        "QA, supported funnel types, and the Marketing/Creative/Execution ownership split. The execution layer builds "
        "pages; Marketing designs the funnel; Creative creates assets."))
    def funnel_status() -> dict[str, Any]:
        authorize_read("funnel_status")
        return _engine().status()

    @mcp.tool(name="funnel_page", description=(
        "Read one generated landing page for an existing opportunity: page type/route/objective, section structure, "
        "copy and Creative assets used, CTA, form and tracking status, attribution keys, A/B spec, QA result, preview "
        "location, deploy status (preview prepared, Ray-gated), and next action. Internal IDs suppressed unless diagnostics."))
    def funnel_page(opportunity_id: str = "", page_id: str = "", page_type: str = "",
                    diagnostics: bool = False) -> dict[str, Any]:
        authorize_read("funnel_page")
        return _engine().get_page(opportunity_id=opportunity_id, page_id=page_id, page_type=page_type,
                                  include_internal_ids=diagnostics)

    @mcp.tool(name="funnel_qa", description=(
        "Read-only QA result for a generated page: deterministic static checks (page loads, mobile layout, CTA/form "
        "wired, tracking params present, affiliate links resolve, no broken assets/console blockers, basic "
        "accessibility, funnel sequence) plus the prepared Playwright spec + preview index paths for live browser QA."))
    def funnel_qa(opportunity_id: str = "", page_id: str = "", diagnostics: bool = False) -> dict[str, Any]:
        authorize_read("funnel_qa")
        return _engine().qa(opportunity_id=opportunity_id, page_id=page_id, include_internal_ids=diagnostics)

    @mcp.tool(name="funnel_nova_summary", description=(
        "Read-only Nova-readable summary for a generated page: page type/route, build + QA status, form/tracking "
        "status, deploy status, A/B test state, approval requirement, and the recommended next action. Execution-layer "
        "logic stays in the execution layer, not Nova."))
    def funnel_nova_summary(opportunity_id: str = "", page_id: str = "", diagnostics: bool = False) -> dict[str, Any]:
        authorize_read("funnel_nova_summary")
        return _engine().nova_summary(opportunity_id=opportunity_id, page_id=page_id, include_internal_ids=diagnostics)

    @mcp.tool(name="funnel_build_page", description=(
        "Assemble a landing page for an existing opportunity from the frozen Marketing funnel specification and the "
        "frozen Creative assets: select a v1 funnel type (AFFILIATE_REVIEW_PAGE, PRODUCT_COMPARISON_PAGE, "
        "LEAD_CAPTURE_PAGE, SERVICE_OFFER_PAGE, SIMPLE_SALES_PAGE), build responsive page structure, wire CTA/form and "
        "attribution (UTM + opportunity/campaign/creative/landing-page/offer IDs), prepare an A/B variant spec, run "
        "deterministic QA, write a local preview build, and prepare (not execute) the Netlify preview deploy command. "
        "Autonomous build only: no publish, no deploy, no spend. Never changes the offer/model/strategy. Idempotent "
        "per opportunity + page type."))
    def funnel_build_page(opportunity_id: str, funnel_type: str = "") -> dict[str, Any]:
        authorize_action("funnel_build_page")
        try:
            return _engine().build_page(opportunity_id, funnel_type=funnel_type)
        except (TypeError, ValueError, KeyError) as exc:
            return {"status": "REJECTED", "reason": str(exc)[:240]}
