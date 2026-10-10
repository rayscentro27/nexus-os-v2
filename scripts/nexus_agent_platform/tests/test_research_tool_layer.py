import json
from pathlib import Path

from nexus_agent_platform.research_tool_layer import (
    TOOL_REGISTRY,
    classify_source,
    execute_research_question,
    full_source_evidence_guard,
    plan_source_strategy,
    single_primary_engine_guard,
)
from types import SimpleNamespace
from nexus_agent_platform.proactive_discovery import HERMES_PRIMARY_PROACTIVE_LANES, classify_customer_candidates, generate_seed_queries, should_apply_lane_followup
from research.proactive_research_memory import query_family, query_guard
from datetime import datetime, timezone


def test_customer_question_plans_firsthand_sources_and_extraction():
    plan = plan_source_strategy(
        "What recurring problems are small-business owners reporting when trying to obtain funding?"
    )
    assert plan["firsthand_evidence_preferred"] is True
    assert "CUSTOMER_DISCUSSIONS" in plan["source_classes_planned"]
    assert "public_web_retrieval" in plan["tools_planned"]
    assert plan["cross_check_required"] is True


def test_source_classifier_distinguishes_official_discussion_review_and_news():
    assert classify_source("https://trai.gov.in/faqcategory/x")["source_class"] == "OFFICIAL_SOURCE"
    assert classify_source("https://www.reddit.com/r/smallbusiness/comments/1/x")["source_class"] == "DISCUSSION"
    assert classify_source("https://www.trustpilot.com/review/example.com")["source_class"] == "REVIEW"
    assert classify_source("https://www.bnnbloomberg.ca/story")["source_class"] == "NEWS"


def test_search_snippet_is_not_evidence_without_page_extraction():
    assert not full_source_evidence_guard({"snippet": "Some search result summary"})
    assert not full_source_evidence_guard({"extraction_status": "FAILED", "extracted_text": "x" * 500})
    assert full_source_evidence_guard({"extraction_status": "EXTRACTED", "extracted_text": "x" * 120})


def test_registry_keeps_general_tools_separate_from_specialized_sources():
    by_id = {row["tool_id"]: row for row in TOOL_REGISTRY}
    assert by_id["you-search"]["capability"] == "GENERAL_SEARCH"
    assert by_id["public_web_retrieval"]["capability"] == "DEEP_EXTRACT"
    assert by_id["tradingview_public_source"]["source_class"] == "TRADINGVIEW"
    assert by_id["youtube_channel_registry"]["source_class"] == "YOUTUBE"
    registry = json.loads(Path("config/research/research_tool_registry.json").read_text())
    assert registry["guardrails"][:2] == ["SEARCH_RESULT_IS_CANDIDATE_NOT_EVIDENCE", "EXTRACT_SOURCE_BEFORE_FINDING"]


def test_customer_discovery_classifies_broad_results_without_claiming_firsthand():
    rows = classify_customer_candidates([
        {"url": "https://www.reddit.com/r/smallbusiness/comments/x", "title": "owner asks about fees", "snippet": "..."},
        {"url": "https://www.trustpilot.com/review/lender.example", "title": "reviews", "snippet": "..."},
    ])
    assert [row["source_class"] for row in rows] == ["DISCUSSION", "REVIEW"]
    assert all(row["firsthand_or_secondary"] == "UNKNOWN" for row in rows)
    assert all(row["extraction_status"] == "CANDIDATE_NOT_EXTRACTED" for row in rows)


def test_customer_research_question_is_not_degraded_by_canned_query_suffix():
    question = "What recurring problems are owners reporting when seeking funding?"
    assert generate_seed_queries(question, "CUSTOMER_NEEDS_COMPLAINTS", max_queries=4) == [question]


def test_explicit_customer_question_is_not_replaced_by_stale_lane_memory():
    question = "What recurring problems are owners reporting when seeking funding?"
    assert should_apply_lane_followup(question, "CUSTOMER_NEEDS_COMPLAINTS", True) is False
    assert should_apply_lane_followup("funding customer complaints", "CUSTOMER_NEEDS_COMPLAINTS", True) is True


def test_material_customer_source_strategy_change_allows_one_bounded_recheck():
    question = "What recurring problems are small-business owners reporting when trying to obtain business funding?"
    now = datetime.now(timezone.utc).isoformat()
    prior = [{"query": question + " how do I", "query_family": query_family(question + " how do I"),
              "run_at": now, "source_strategy_id": None}]
    changed = query_guard(question, history=prior, source_strategy_id="customer-needs-broad-discovery-v2")
    assert changed["allowed"] is True
    assert changed["reason"] == "SOURCE_STRATEGY_CHANGED"
    same_strategy = [{"query": question, "query_family": query_family(question),
                      "run_at": now, "source_strategy_id": "customer-needs-broad-discovery-v2"}]
    repeated = query_guard(question, history=same_strategy, source_strategy_id="customer-needs-broad-discovery-v2")
    assert repeated["allowed"] is False


def test_live_primary_engine_guard_allows_only_recorded_provider_fallback():
    assert single_primary_engine_guard("HERMES_TOOL_LAYER") is True
    assert single_primary_engine_guard("LOCAL_HTML_FALLBACK", True, "PROVIDER_TIMEOUT") is True
    assert single_primary_engine_guard("LOCAL_HTML_FALLBACK", True, "UNCLASSIFIED") is False
    assert single_primary_engine_guard("LOCAL_HTML_FALLBACK") is False
    assert {"CUSTOMER_NEEDS_COMPLAINTS", "WEB_SEARCH", "COMPETITOR_DISCOVERY",
            "FUNDING_GRANTS", "AFFILIATE_PROGRAM_DISCOVERY"} <= HERMES_PRIMARY_PROACTIVE_LANES


def test_executor_rejects_placeholder_page_as_evidence(tmp_path, monkeypatch):
    import nexus_agent_platform.research_tool_layer as layer
    monkeypatch.setattr(layer, "RUNS_PATH", tmp_path / "runs.jsonl")
    body = {
        "execution_status": "PASS",
        "searches": [{"query": "customer needs", "tool": "you-search", "results": [
            {"title": "Complaint article", "url": "https://example.com/complaints"}]}],
        "sources": [{"url": "https://example.com/complaints", "title": "Complaint article",
                     "extraction_status": "EXTRACTED", "extracted_evidence": "Customer complaints " * 20,
                     "evidence_role": "FIRSTHAND"}],
        "conclusion": "FINDING_SUPPORTED", "assessment": {"source_fit": "GOOD"},
    }
    response = SimpleNamespace(response=json.dumps(body), status="SUCCEEDED", error=None, latency_ms=1)
    result = execute_research_question("What do customers need?", hermes_runner=lambda *a, **k: response)
    assert result["records"] == []
    assert result["execution_status"] == "PROVIDER_FAILURE"
    assert result["research_conclusion"] == "RESEARCH_INCONCLUSIVE"
    assert result["rejected_sources"][0]["url_verification"] == "PLACEHOLDER_DOMAIN"
    assert layer.RUNS_PATH.exists()
