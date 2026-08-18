from __future__ import annotations

import json

import pytest

from nexus_agent_platform.research.open_source_scout import (
    OPEN_SOURCE_SCOUT_CANDIDATES,
    build_compact_delta,
    build_open_source_scout_report,
    dedupe_source_records,
    normalize_source_record,
    run_open_source_scout,
    score_candidate,
)


def _candidate(repo: str):
    return next(item for item in OPEN_SOURCE_SCOUT_CANDIDATES if item["repository"] == repo)


def test_duplicate_research_item_causes_zero_ai_calls():
    report = run_open_source_scout()
    assert report["ai_executions"] == 0
    assert report["zero_token_research_executions"] == 1
    assert report["input_tokens"] == 0
    assert report["output_tokens"] == 0


def test_identical_content_under_different_url_dedupes_where_appropriate():
    candidate = dict(_candidate("microsoft/markitdown"))
    record_a = normalize_source_record(candidate)
    record_b = normalize_source_record(candidate)
    record_b["source_id"] = f"{record_b['candidate_id']}::https://example.com/mirror"
    deduped, duplicates = dedupe_source_records([record_a, record_b])
    assert len(deduped) == 1
    assert len(duplicates) == 1


def test_low_materiality_evidence_uses_zero_ai_calls():
    report = build_open_source_scout_report()
    assert report["metrics"]["ai_executions"] == 0
    assert report["metrics"]["tier1_calls"] == 0
    assert report["metrics"]["tier2_calls"] == 0
    assert report["metrics"]["tier3_calls"] == 0


def test_compact_delta_avoids_historical_corpus():
    candidate = normalize_source_record(dict(_candidate("unclecode/crawl4ai")))
    delta = build_compact_delta(candidate, {"last_candidate_hash": "abc", "last_recommendation": "old"})
    assert "history" not in delta
    assert "full_history" not in delta
    assert delta["previous_candidate_hash"] == "abc"
    assert len(json.dumps(delta)) < 2000


def test_t3_escalation_cannot_happen_without_explicit_condition():
    candidate = _candidate("unclecode/crawl4ai")
    score = score_candidate(candidate)
    assert score["ai_tier"] == "T2_STANDARD_AI"
    assert score["ai_tier_with_explicit_escalation"] == "T2_STANDARD_AI" or score["ai_tier_with_explicit_escalation"] == "T3_PREMIUM_AI"
    if score["base_score"] >= 85:
        assert score["ai_tier"] == "T2_STANDARD_AI"
        assert score["ai_tier_with_explicit_escalation"] == "T3_PREMIUM_AI"


def test_pii_isolation_holds():
    report = build_open_source_scout_report()
    text = json.dumps(report)
    assert "client_pii" not in text.lower()
    assert "ssn" not in text.lower()
    assert "dob" not in text.lower()
    assert "credential" not in text.lower()


def test_nexus_first_audit_happens_before_candidate_recommendation():
    report = build_open_source_scout_report()
    assert report["timeline"][0] == "nexus_audit"
    assert report["timeline"].index("nexus_audit") < report["timeline"].index("opportunity_engine_input")
    assert report["nexus_audit"][0]["candidate_id"] == "markitdown"


def test_canonical_opportunity_engine_receives_qualifying_evidence():
    report = build_open_source_scout_report()
    opportunity = report["opportunity_input"]
    assert opportunity["evidence"]
    assert opportunity["evidence"][0]["classification"] == "KNOWN"
    assert opportunity["source_type"] == "public_repo_intelligence"
    assert opportunity["id"] == "unclecode_crawl4ai"
    assert opportunity["base_score"] == opportunity["opportunity_score"]
