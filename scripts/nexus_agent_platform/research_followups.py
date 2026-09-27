"""Durable contract for Alpha RESEARCH_MORE follow-up acquisition."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from nexus_agent_platform.governed import persistence
from nexus_agent_platform.research_work_queue import default_queue

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

def route_for(*, finding_id: str, question: str = "", package: dict[str, Any] | None = None) -> dict[str, Any]:
    blob = f"{finding_id} {question} {package or {}}".lower()
    if any(x in blob for x in ("needle", "jev", "systems", "compatibility", "github")):
        return {"owner": "RESEARCH", "department": "SYSTEMS", "mission": "Systems capability intelligence", "lane_id": "GITHUB_TECHNOLOGY", "return_target": "ALPHA", "source_classes": ["OFFICIAL_REPOSITORY", "OFFICIAL_DOCS", "RELEASE_NOTES", "ISSUES", "BENCHMARKS"], "preferred_sources": ["official repository/docs", "release notes", "requirements", "issues"], "fallback_sources": ["GitHub API/public repository pages", "public compatibility reports", "isolated local benchmark"]}
    if "trading" in blob or "tradingview" in blob:
        return {"owner": "RESEARCH", "department": "TRADING", "mission": "Trading strategy and tool intelligence", "lane_id": "TRADING_MARKETS", "return_target": "ALPHA", "source_classes": ["TRADINGVIEW_PUBLIC", "PUBLIC_STRATEGY_REPOSITORY", "MARKET_DATA", "BACKTEST_REFERENCE"], "preferred_sources": ["TradingView Editor's Picks", "TradingView public script page"], "fallback_sources": ["TradingView public search", "GitHub strategy repository", "bounded market-data documentation"]}
    if any(x in blob for x in ("funding", "goclear", "lender", "credit")):
        return {"owner": "RESEARCH", "department": "CLYDE_CREDIT", "mission": "GoClear funding and customer intelligence", "lane_id": "FUNDING_LENDER", "return_target": "ALPHA", "source_classes": ["LENDER_OFFICIAL", "ISSUER_TERMS", "SBA_PROGRAM", "MARKET_OBSERVATION", "CUSTOMER_NEED"], "preferred_sources": ["official lender/issuer pages", "SBA program pages"], "fallback_sources": ["Federal Reserve Small Business Credit Survey", "credit union pages", "reputable market summaries", "bounded customer discussions"]}
    return {"owner": "RESEARCH", "department": "REVENUE_OPPORTUNITY_DISCOVERY", "mission": "Revenue opportunity discovery toward verified net revenue", "lane_id": "AFFILIATE_REVENUE", "return_target": "ALPHA", "source_classes": ["MARKETPLACE", "CUSTOMER_DISCUSSION", "SEARCH_DEMAND", "SUPPLIER_PRICING", "COMPETITOR"], "preferred_sources": ["public marketplace/product pages", "customer discussions", "search demand"], "fallback_sources": ["Reddit/community evidence", "YouTube audience signals", "supplier public pricing", "competitor public offers"]}

def build_followup(*, finding_id: str, alpha_receipt_id: str, alpha_request_id: str, missing_evidence: list[str], question: str, package: dict[str, Any] | None = None, parent_handoff_id: str | None = None, parent_goal: str = "", project_id: str | None = None, work_order_id: str | None = None, source_candidates: list[dict[str, Any]] | None = None, work_id: str | None = None) -> dict[str, Any]:
    route = route_for(finding_id=finding_id, question=question, package=package)
    candidates = list(source_candidates or [])
    if not candidates:
        defaults = {
            "SYSTEMS": [("https://github.com/search?q=needle+jev&type=repositories", "public repository search"), ("https://github.com/search?q=needle+jev&type=issues", "public issue search")],
            "TRADING": [("https://www.tradingview.com/scripts/editors-picks/", "TradingView Editor's Picks"), ("https://www.tradingview.com/scripts/", "TradingView public scripts"), ("https://github.com/search?q=tradingview+strategy&type=repositories", "public strategy repositories")],
            "CLYDE_CREDIT": [("https://www.fedsmallbusiness.org/survey", "Federal Reserve Small Business Credit Survey"), ("https://www.sba.gov/loans", "SBA loan guidance"), ("https://www.bankofamerica.com/smallbusiness/business-financing/", "Bank of America small business financing")],
            "REVENUE_OPPORTUNITY_DISCOVERY": [("https://www.reddit.com/r/smallbusiness/", "small business customer discussion"), ("https://www.indiehackers.com/", "public founder opportunity discussion"), ("https://www.youtube.com/results?search_query=small+business+product+ideas", "bounded YouTube demand signals")],
        }
        candidates = [{"source_type":"WEB_PAGE", "source_id":f"fallback-{i}", "source_url":url, "title":title} for i,(url,title) in enumerate(defaults.get(route["department"], []))]
    created = now()
    request_id = f"research_followup:{alpha_receipt_id}"
    return {"schema_version": "nexus.research-more-followup.v1", "research_request_id": request_id, "request_id": request_id,
        "work_id": work_id or f"research-followup:{alpha_receipt_id}", "parent_finding_id": finding_id, "parent_alpha_receipt_id": alpha_receipt_id, "parent_alpha_request_id": alpha_request_id,
        "parent_handoff_id": parent_handoff_id, "business_or_nexus": "GOCLEAR" if route["department"] == "CLYDE_CREDIT" else "NEXUS",
        "department": route["department"], "mission": route["mission"], "project_id": project_id, "objective_id": project_id or finding_id,
        "work_order_id": work_order_id, "question": question, "WHY_THIS_RESEARCH": f"Alpha identified a material evidence gap: {question}",
        "why_this_research": f"Alpha identified a material evidence gap: {question}", "missing_evidence": list(missing_evidence),
        "source_classes": route["source_classes"], "preferred_sources": route["preferred_sources"], "fallback_sources": route["fallback_sources"],
        "source_candidates": candidates, "owner": route["owner"], "state": "OWNED", "status": "OWNED",
        "attempt_count": 0, "last_attempt": None, "next_action": "Acquire bounded evidence from the preferred source classes; fall back without closing the question.",
        "return_target": route["return_target"], "lane_id": route["lane_id"], "alpha_followup_required": True,
        "research_mode": "REQUESTED_RESEARCH" if route["department"] == "CLYDE_CREDIT" else "NEXUS_DEPARTMENTAL_PROACTIVE",
        "created_at": created, "updated_at": created, "external_action_allowed": False}

def persist_followup(followup: dict[str, Any]) -> dict[str, Any]:
    persistence.append_record("research_requests", followup)
    default_queue().upsert({**followup, "status": "QUEUED", "work_class": "ASSIGNED", "source_type": "RESEARCH_OBJECTIVE", "source_id": followup["parent_finding_id"], "title": followup["question"], "selection_reason": "alpha_research_more_followup", "lifecycle": "ONE_TIME", "alpha_eligible": True, "alpha_review_required": True})
    return followup
