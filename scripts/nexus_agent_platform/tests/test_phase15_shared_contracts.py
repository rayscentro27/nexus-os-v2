from nexus_agent_platform.phase15.keep_running import disposition
from nexus_agent_platform.phase15.research_decisions import build_research_decisions


def test_phase15_keep_running_policy_escalates_only_explicit_safety_states():
    assert disposition("NO_CHANGE") == "KEEP_RUNNING"
    assert disposition("DUPLICATE_ONLY") == "KEEP_RUNNING"
    assert disposition("AUTHORITY_VIOLATION") == "STOP_OR_ESCALATE"
    assert disposition("UNRECOGNIZED") == "REVIEW_REQUIRED"


def test_phase15_research_decisions_are_bounded_deterministic_and_deduplicated():
    batch = [
        {"candidate_id": "one", "title": "A", "source_url": "https://example.test/a", "evidence_classification": "VERIFIED", "freshness": "FRESH"},
        {"candidate_id": "two", "title": "A duplicate", "source_url": "https://example.test/a", "evidence_classification": "VERIFIED", "freshness": "FRESH"},
        {"candidate_id": "three", "title": "B", "source_url": "https://example.test/b", "evidence_classification": "INFERRED", "freshness": "FRESH"},
        {"candidate_id": "four", "title": "C", "source_url": "https://example.test/c", "evidence_classification": "VERIFIED", "freshness": "STALE"},
    ]
    result = build_research_decisions(batch, session={"session_id": "test"})
    assert [row["decision"] for row in result["decisions"]] == ["ACCEPT", "DUPLICATE", "WATCH", "STALE"]
    assert result["counts"] == {"accept": 1, "watch": 1, "reject": 0, "duplicate": 1, "needs_more_evidence": 0, "stale": 1}
    assert result["batch_hash"] == build_research_decisions(batch, session={"session_id": "test"})["batch_hash"]
