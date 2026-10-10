"""Question-first evidence quality and explainable signal receipts.

Execution receipts remain independent from the strength of research conclusions.
Raw discovery is not automatically a supported finding.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RAW_SIGNALS = ROOT / "data/governed/research_raw_signals.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def source_class(url: str, declared: str = "") -> str:
    if declared:
        declared = declared.upper()
        # Keep provider labels in raw receipts, but use canonical policy labels
        # for source-fit comparisons.
        aliases = {"WEB_SEARCH_RESULT": "WEB_SEARCH", "DUCKDUCKGO_HTML": "WEB_SEARCH",
                   "BING_HTML": "WEB_SEARCH", "CUSTOMER_NEEDS_COMPLAINTS": "CUSTOMER_DISCUSSIONS",
                   "DESIGNATED_YOUTUBE": "YOUTUBE", "AFFILIATE_PROGRAM_DISCOVERY": "AFFILIATE_DIRECTORY",
                   "GITHUB_TECHNOLOGY_DISCOVERY": "GITHUB"}
        return aliases.get(declared, declared)
    host = (url or "").lower().split("/")[2] if "://" in (url or "") else ""
    if "tradingview.com" in host: return "TRADINGVIEW_PUBLIC_SCRIPTS"
    if "github.com" in host: return "GITHUB"
    if host.endswith((".gov", ".gov.uk", ".gov.au")): return "OFFICIAL_GOVERNMENT"
    if any(x in host for x in ("reddit.com", "quora.com", "community.")): return "CUSTOMER_DISCUSSIONS"
    if any(x in host for x in ("amazon.", "trustpilot.", "g2.com", "capterra.")): return "PRODUCT_REVIEWS"
    return "WEB_SEARCH_RESULT"


def assess_run(objective: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    records = list(result.get("records") or [])
    used = sorted({source_class(str(row.get("url") or ""), str(row.get("source_class") or "")) for row in records})
    expected = list(objective.get("best_source_classes") or [])
    fit_count = sum(1 for cls in used if cls in expected)
    source_fit = "GOOD" if fit_count and used else "POOR" if not used or (expected and not fit_count) else "PARTIAL"
    # A source class does not make evidence firsthand by itself. Count only
    # records explicitly marked as firsthand, and require independent classes
    # as well as domains before calling evidence cross-source confirmed.
    first_hand = sum(1 for row in records if str(row.get("firsthand_or_secondary", "")).upper().startswith("FIRSTHAND"))
    independent = {(source_class(str(row.get("url") or ""), str(row.get("source_class") or "")),
                    str(row.get("domain") or "").lower()) for row in records if row.get("domain")}
    cross_source = len({domain for _, domain in independent}) >= 2 and len({cls for cls, _ in independent}) >= 2
    execution = "PASS" if result.get("status") in {"COMPLETED", "PASS"} and not result.get("failed_queries") else "PARTIAL" if records else "FAIL"
    # Acquisition cases/source rows are not research findings. Only the explicit
    # evidence evaluator may establish a supported finding count.
    qualified = int(result.get("evidence_supported_finding_count", 0) or 0)
    # Current deterministic discovery cannot establish falsification coverage.
    coverage_sufficient = bool(result.get("coverage_sufficient_for_negative_conclusion"))
    conclusion = "FINDING_SUPPORTED" if qualified else "HYPOTHESIS_NOT_SUPPORTED" if coverage_sufficient and source_fit == "GOOD" and cross_source else "RESEARCH_INCONCLUSIVE"
    if conclusion != "FINDING_SUPPORTED":
        next_action = "CHANGE_SOURCE_STRATEGY" if source_fit == "POOR" else "CROSS_CHECK" if not cross_source else "REFINE_QUERY"
    else:
        next_action = "ROUTE_SUPPORTED_FINDING"
    return {
        "execution_status": execution,
        "research_question_quality": "QUESTION_FIRST" if objective.get("research_question") else "MISSING_QUESTION",
        "research_question": objective.get("research_question"),
        "evidence_needed": objective.get("evidence_needed"),
        "best_source_classes": expected,
        "source_classes_planned": expected,
        "why_these_sources": objective.get("why_these_sources"),
        "source_fit": source_fit,
        "evidence_quality": "QUALIFIED_FINDING_PRESENT" if qualified else "RAW_DISCOVERY_ONLY",
        "evidence_diversity": len(used), "firsthand_evidence_count": first_hand,
        "cross_source_confirmation": cross_source, "novelty": "RECORDED_BY_SOURCE_IDENTITY_DEDUPE",
        "decision_usefulness": "ACTIONABLE" if qualified else "INSUFFICIENT_TO_DECIDE",
        "research_conclusion": conclusion, "next_research_action": next_action,
        "searches_run": len(result.get("queries") or []), "sources_opened": len(records),
        "search_results_returned": int(result.get("search_results_returned", len(records)) or 0),
        "search_results_screened_out": len(result.get("screened_out_results") or []),
        "qualified_findings": qualified, "source_classes_used": used,
        "coverage_sufficient_for_negative_conclusion": coverage_sufficient,
    }


def persist_raw_signals(objective: dict[str, Any], result: dict[str, Any], quality: dict[str, Any]) -> list[str]:
    records = list(result.get("records") or []) + [
        {**row, "screened_out": True, "screening_reason": row.get("query_source_fit") or "QUERY_RELEVANCE_BELOW_MINIMUM"}
        for row in (result.get("screened_out_results") or [])]
    RAW_SIGNALS.parent.mkdir(parents=True, exist_ok=True)
    ids: list[str] = []
    with RAW_SIGNALS.open("a", encoding="utf-8") as f:
        for row in records:
            url = str(row.get("url") or "")
            title = str(row.get("title") or "")
            snippet = str(row.get("snippet") or row.get("description") or "")
            source = source_class(url, str(row.get("source_class") or ""))
            score = min(1.0, (0.2 if title else 0) + (0.2 if snippet else 0) + (0.2 if url else 0)
                        + (0.2 if source in set(objective.get("best_source_classes") or []) else 0)
                        + (0.2 if row.get("firsthand_or_secondary") == "FIRSTHAND" else 0))
            sid = "sig_" + hashlib.sha256((url or title + snippet).encode()).hexdigest()[:24]
            failed = []
            if not snippet: failed.append("NO_EXTRACTED_EVIDENCE_SNIPPET")
            if source not in set(objective.get("best_source_classes") or []): failed.append("SOURCE_CLASS_MISMATCH")
            if not row.get("published_at"): failed.append("SOURCE_DATE_UNKNOWN")
            if row.get("screened_out"): failed.append(str(row.get("screening_reason") or "SEARCH_RESULT_SCREENED_OUT"))
            for criterion, value in (row.get("qualification_criteria") or {}).items():
                if not value: failed.append(f"{criterion}_NOT_ESTABLISHED")
            if row.get("persistence_disposition") == "DUPLICATE": failed.append("DURABLE_SOURCE_ALREADY_EXISTS")
            record = {
                "signal_id": sid, "recorded_at": _now(), "objective_family": objective.get("objective_family"),
                "research_question": objective.get("research_question"), "query": row.get("query"),
                "source_class": source, "source_url": url, "source_title": title,
                "source_date": row.get("published_at") or row.get("updated_at"), "evidence_snippet": snippet,
                "firsthand_or_secondary": row.get("firsthand_or_secondary") or "UNKNOWN",
                "detected_need_or_signal": row.get("detected_need_or_signal") or title,
                "why_relevant": objective.get("business_reason"), "evidence_quality": "RAW_UNVERIFIED",
                "source_fit": "MATCH" if source in set(objective.get("best_source_classes") or []) else "MISMATCH",
                "qualification_score": round(score, 3), "qualification_threshold": 0.7,
                "qualification_criteria": row.get("qualification_criteria", {}),
                "failed_criteria": failed, "more_research_could_rescue": True,
                "missing_evidence": failed, "potential_routing_if_qualified": "TRADING" if objective.get("objective_family") == "TRADING_INTELLIGENCE" else "OPPORTUNITIES",
                "qualification_status": "SEARCH_RESULT_SCREENED_OUT" if row.get("screened_out") else "UNQUALIFIED_RAW_SIGNAL", "execution_status": quality.get("execution_status"),
                "research_conclusion": quality.get("research_conclusion"),
            }
            f.write(json.dumps(record, sort_keys=True) + "\n")
            ids.append(sid)
    return ids


def build_market_cluster(topic: str, evidence: list[dict[str, Any]]) -> dict[str, Any]:
    sources = {str(x.get("source_url") or x.get("url") or "") for x in evidence
               if x.get("source_url") or x.get("url")}
    classes = {source_class(str(x.get("source_url") or x.get("url") or ""), str(x.get("source_class") or "")) for x in evidence
               if x.get("source_url") or x.get("url")}
    sufficient = len(sources) >= 3 and len(classes) >= 2
    def signals(*labels: str) -> list[dict[str, Any]]:
        wanted = {label.upper() for label in labels}
        return [{"url": x.get("source_url") or x.get("url"),
                 "source_class": source_class(str(x.get("source_url") or x.get("url") or ""), str(x.get("source_class") or "")),
                 "evidence": x.get("extracted_evidence") or x.get("evidence_snippet") or x.get("snippet"),
                 "firsthand_or_secondary": x.get("firsthand_or_secondary", "UNKNOWN")}
                for x in evidence
                if source_class(str(x.get("source_url") or x.get("url") or ""), str(x.get("source_class") or "")).upper() in wanted]
    return {"topic": topic, "customer": None, "customer_segment": None, "problem_or_desire": None,
            "first_seen": min((x.get("source_date") or x.get("published_at") or "" for x in evidence), default=None),
            "last_seen": _now(), "trend_direction": "UNKNOWN", "customer_evidence": [],
            "product_evidence": [], "affiliate_evidence": [], "merch_evidence": [], "search_demand": [],
            "video_social_signal": [], "competition": [], "current_alternatives": [],
            "monetization_options": [], "build_vs_affiliate_vs_service": None,
            "confidence": "LOW" if not sufficient else "REQUIRES_REVIEW", "evidence_sources": sorted(sources),
            "source_classes": sorted(classes), "more_research_needed": not sufficient,
            "firsthand_signals": signals("CUSTOMER_DISCUSSIONS", "DISCUSSION", "REVIEW"),
            "product_signals": signals("PRODUCT_MARKETPLACE", "PRODUCT_REVIEWS", "MARKETPLACE"),
            "affiliate_signals": signals("AFFILIATE", "AFFILIATE_DIRECTORY"),
            "merch_signals": signals("MERCH_MARKETPLACE", "PUBLIC_CAMPAIGNS"),
            "search_signals": signals("WEB_SEARCH", "SEARCH_DEMAND"),
            "social_signals": signals("YOUTUBE", "VIDEO_SOCIAL", "PUBLIC_SOCIAL"),
            "competitor_signals": signals("COMPETITOR", "OFFICIAL_PRODUCT_DOCS"),
            "source_count": len(sources), "source_diversity": len(classes),
            "evidence_strength": "LOW" if not sufficient else "REQUIRES_EVIDENCE_REVIEW",
            "next_research_action": "CHANGE_SOURCE_STRATEGY" if not sufficient else "CROSS_CHECK_BEFORE_OPPORTUNITY_REVIEW",
            "cluster_eligibility": "ELIGIBLE_FOR_REVIEW" if sufficient else "INSUFFICIENT_SINGLE_OR_WEAK_SOURCE"}
