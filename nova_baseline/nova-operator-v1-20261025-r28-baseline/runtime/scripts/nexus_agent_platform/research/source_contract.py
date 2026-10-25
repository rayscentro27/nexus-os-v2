"""Source/objective/result fidelity contract for Research."""
from __future__ import annotations

import json
import re
from typing import Any

TRADING = "TRADING_STRATEGY_RESEARCH"
FUNDING = "BUSINESS_FUNDING"
CREDIT = "CREDIT_APPROVAL_INTELLIGENCE"
SYSTEMS = "SYSTEMS_AI_TOOLS"
BUSINESS = "BUSINESS_OPPORTUNITY_DISCOVERY"
SEO = "SEO_GROWTH"
MARKETING = "MARKETING_CUSTOMER_DEMAND"
GITHUB = "GITHUB_OPEN_SOURCE"
OTHER = "OTHER"

SOURCE_CATEGORY_BY_ID = {
    "tradingview-editors-picks": TRADING,
    "tradingview-scripts": TRADING,
    "sba-loans": FUNDING,
    "sba-business-guide": FUNDING,
    "fed-sbcs": FUNDING,
    "cardright_user_cc_results": CREDIT,
    "openai/openai-cookbook": GITHUB,
    "needle": SYSTEMS,
    "jev": SYSTEMS,
}
SOURCE_CATEGORY_BY_DOMAIN = {
    "tradingview.com": TRADING, "sba.gov": FUNDING,
    "fedsmallbusiness.org": FUNDING, "cardright.com": CREDIT,
    "github.com": GITHUB, "youtube.com": OTHER, "youtu.be": OTHER,
}


def _host(url: Any) -> str:
    value = re.sub(r"^https?://", "", str(url or "").lower())
    return value.split("/", 1)[0].split(":", 1)[0].removeprefix("www.")


def source_category(item: dict[str, Any]) -> str:
    explicit = str(item.get("primary_category") or item.get("source_category") or "").upper()
    allowed = {TRADING, FUNDING, CREDIT, SYSTEMS, BUSINESS, SEO, MARKETING, GITHUB, OTHER}
    if explicit in allowed:
        return explicit
    source_id = str(item.get("source_id") or "").lower()
    if source_id in SOURCE_CATEGORY_BY_ID:
        return SOURCE_CATEGORY_BY_ID[source_id]
    host = _host(item.get("source_url") or item.get("url"))
    for domain, category in SOURCE_CATEGORY_BY_DOMAIN.items():
        if host == domain or host.endswith("." + domain):
            return category
    blob = " ".join(str(item.get(key) or "") for key in ("objective_id", "title", "question", "lane_id", "department_target")).lower()
    if any(x in blob for x in ("tradingview", "trading strategy", "indicator", "backtest")): return TRADING
    if any(x in blob for x in ("funding", "sba", "loan", "lender")): return FUNDING
    if any(x in blob for x in ("cardright", "credit approval")): return CREDIT
    if any(x in blob for x in ("needle", "jev", "systems capability", "systems")): return SYSTEMS
    if any(x in blob for x in ("business opportunity", "opportunity discovery")): return BUSINESS
    if "seo" in blob: return SEO
    if any(x in blob for x in ("demand", "customer", "marketing")): return MARKETING
    if "github" in blob or str(item.get("source_type") or "").upper().startswith("GITHUB"): return GITHUB
    return OTHER


def objective_category(item: dict[str, Any]) -> str:
    explicit = str(item.get("objective_category") or "").upper()
    if explicit: return explicit
    blob = " ".join(str(item.get(key) or "") for key in ("objective_id", "title", "question", "lane_id", "department_target", "category")).lower()
    if any(x in blob for x in ("trading", "tradingview", "indicator", "backtest")): return TRADING
    if any(x in blob for x in ("funding", "sba", "loan", "lender")): return FUNDING
    if any(x in blob for x in ("cardright", "credit approval")): return CREDIT
    if any(x in blob for x in ("needle", "jev", "systems capability", "systems")): return SYSTEMS
    if any(x in blob for x in ("business opportunity", "revenue opportunity")): return BUSINESS
    if "seo" in blob: return SEO
    if any(x in blob for x in ("demand", "customer", "marketing")): return MARKETING
    return OTHER


def validate_source_result(item: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    source = source_category(item)
    objective = objective_category(item)
    text = json.dumps(result, ensure_ascii=False, default=str).lower()[:200000]
    failed = str(result.get("final_status") or result.get("processing_status") or "").upper().startswith("FAILED") or bool(result.get("error"))
    if str(item.get("source_type") or "").upper() == "YOUTUBE_CHANNEL":
        return {"valid": not failed, "status": "SOURCE_REFRESH" if not failed else "SOURCE_FAILURE",
                "source_category": source, "objective_category": objective, "alpha_allowed": False}
    if str(result.get("processing_status") or "").upper() == "DUPLICATE_UNCHANGED":
        return {"valid": True, "status": "DUPLICATE_SKIPPED", "source_category": source,
                "objective_category": objective, "alpha_allowed": False}
    mismatch = None
    if source == TRADING or objective == TRADING:
        required = ("tradingview", "strategy", "indicator", "script", "backtest", "entry", "exit", "drawdown")
        unrelated = ("aurora ai agency", "xylo business automation", "business automation suite")
        if not failed and (source != TRADING or objective != TRADING or not any(x in text for x in required) or any(x in text for x in unrelated)):
            mismatch = "TRADING_SOURCE_RESULT_DOMAIN_MISMATCH"
    if source == FUNDING or objective == FUNDING:
        required = ("funding", "loan", "lender", "borrower", "credit", "sba", "capital", "grant")
        unrelated = ("immigration", "open models", "election fraud", "ai security incident")
        if not failed and (not any(x in text for x in required) or any(x in text for x in unrelated)):
            mismatch = "FUNDING_SOURCE_RESULT_DOMAIN_MISMATCH"
    if mismatch:
        return {"valid": False, "status": "CATEGORY_MISMATCH", "category_mismatch": mismatch,
                "source_category": source, "objective_category": objective, "alpha_allowed": False}
    return {"valid": True, "status": "SOURCE_FAILURE" if failed else "PASS",
            "source_category": source, "objective_category": objective, "alpha_allowed": not failed}


def source_registry_contract(*, source_id: str, name: str, source_type: str, url: str,
                             primary_category: str, purpose: str, destinations: list[str],
                             identity: str) -> dict[str, Any]:
    return {"source_id": source_id, "source_name": name, "source_type": source_type,
            "primary_category": primary_category, "source_url": url, "purpose": purpose,
            "allowed_output_types": ["SOURCE_METADATA", "TRANSCRIPT_REVIEW", "EVIDENCE_SUMMARY"],
            "allowed_destination_departments": destinations, "refresh_mode": "BOUNDED_REFRESH",
            "content_identity_strategy": identity, "enabled": True}
