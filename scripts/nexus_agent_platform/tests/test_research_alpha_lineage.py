import json
from datetime import datetime, timezone

from nexus_agent_platform import research_alpha_lineage as lineage
from nexus_agent_platform.grounded_response import ground_response, requires_current_evidence


def _write(path, rows):
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def _fixture(tmp_path):
    governed = tmp_path / "governed"
    governed.mkdir()
    _write(governed / "alpha_content.jsonl", [
        {"content_id": "content-qualified", "title": "Qualified signal", "canonical_url": "https://example.test/q", "first_seen_at": "2026-09-05T08:00:00+00:00", "status": "DISCOVERED"},
        {"content_id": "content-rejected", "title": "Rejected signal", "canonical_url": "https://example.test/r", "first_seen_at": "2026-09-05T08:10:00+00:00", "status": "DISCOVERED"},
        {"content_id": "content-unscored", "title": "Awaiting Alpha", "canonical_url": "https://example.test/u", "first_seen_at": "2026-09-05T08:20:00+00:00", "status": "DISCOVERED"},
        {"content_id": "content-old", "title": "Old signal", "canonical_url": "https://example.test/o", "first_seen_at": "2026-09-04T23:00:00+00:00", "status": "DISCOVERED"},
    ])
    _write(governed / "alpha_claims.jsonl", [
        {"claim_id": "claim-q", "content_id": "content-qualified", "claim": "A supported bounded opportunity.", "verification_status": "PARTIAL", "evidence_score": .82},
        {"claim_id": "claim-r", "content_id": "content-rejected", "claim": "A weak promotional claim.", "verification_status": "UNVERIFIED", "evidence_score": .12},
        {"claim_id": "claim-u", "content_id": "content-unscored", "claim": "A pending observation.", "verification_status": "UNVERIFIED"},
    ])
    _write(governed / "alpha_research.jsonl", [
        {"research_id": "research-q", "claims": ["claim-q"], "question": "Test qualified", "status": "CHALLENGED", "created_at": "2026-09-05T08:01:00+00:00"},
        {"research_id": "research-r", "claims": ["claim-r"], "question": "Test rejected", "status": "CHALLENGED", "created_at": "2026-09-05T08:11:00+00:00"},
    ])
    _write(governed / "alpha_outcomes.jsonl", [
        {"outcome_id": "route-q", "research_id": "research-q", "route": "MARKETING", "status": "QUALIFIED", "created_at": "2026-09-05T08:30:00+00:00"},
        {"outcome_id": "route-r", "research_id": "research-r", "route": "NONE", "status": "REJECTED", "created_at": "2026-09-05T08:31:00+00:00"},
    ])
    _write(governed / "alpha_discovery_queue.jsonl", [])
    _write(governed / "alpha_evaluations.jsonl", [
        {"evaluation_id": "eval-q", "research_id": "research-q", "score": 82, "decision": "QUALIFIED", "reasoning": "Evidence is bounded and testable.", "evaluated_at": "2026-09-05T08:29:00+00:00"},
        {"evaluation_id": "eval-r", "research_id": "research-r", "score": 41, "decision": "REJECTED", "reasoning": "Evidence is promotional and unverified.", "evaluated_at": "2026-09-05T08:29:30+00:00"},
    ])
    return governed


def test_lineage_joins_outputs_evaluations_routes_and_filters_time(tmp_path, monkeypatch):
    monkeypatch.setattr(lineage, "GOVERNED", _fixture(tmp_path))
    result = lineage.query_lineage(
        since=datetime(2026, 9, 5, 7, 0, tzinfo=timezone.utc),
        until=datetime(2026, 9, 5, 9, 0, tzinfo=timezone.utc),
    )
    assert result["research_output_count"] == 3
    assert result["alpha_evaluation_count"] == 2
    assert result["unscored_count"] == 1
    qualified = next(row for row in result["research_outputs"] if row["artifact_id"] == "content-qualified")
    rejected = next(row for row in result["research_outputs"] if row["artifact_id"] == "content-rejected")
    pending = next(row for row in result["research_outputs"] if row["artifact_id"] == "content-unscored")
    assert qualified["alpha_evaluation"]["score"] == 82
    assert qualified["routing"]["destination"] == "MARKETING"
    assert rejected["alpha_evaluation"]["decision"] == "REJECTED"
    assert pending["alpha_evaluation"]["evaluated"] is False


def test_empty_result_is_explicit_and_never_uses_telemetry(monkeypatch, tmp_path):
    governed = tmp_path / "governed"
    governed.mkdir()
    for name in ("alpha_content", "alpha_claims", "alpha_research", "alpha_outcomes", "alpha_discovery_queue"):
        _write(governed / f"{name}.jsonl", [])
    monkeypatch.setattr(lineage, "GOVERNED", governed)
    result = lineage.query_lineage(since=datetime(2026, 9, 5, 7, 0, tzinfo=timezone.utc), until=datetime(2026, 9, 5, 9, 0, tzinfo=timezone.utc))
    assert result["research_output_count"] == 0
    assert result["alpha_evaluation_count"] == 0
    assert "heartbeat" not in json.dumps(result).lower()


def test_nova_lineage_query_has_priority_over_research_telemetry(monkeypatch):
    monkeypatch.setattr(lineage, "query_lineage", lambda: {
        "research_output_count": 1, "unscored_count": 0,
        "research_outputs": [{"title": "A real finding", "finding": "A persisted result", "sources": ["https://example.test"], "artifact_id": "content-1", "research_id": "research-1", "verification_status": "VERIFIED", "confidence": "HIGH", "alpha_evaluation": {"evaluated": True, "score": 91, "decision": "QUALIFIED", "reasoning": "Strong evidence"}, "routing": {"destination": "TRADING", "status": "QUEUED"}, "current_status": "QUEUED"}],
    })
    request = "What did Research produce and what did Alpha score today?"
    assert requires_current_evidence(request) is True
    response, evidence = ground_response("Research heartbeat: ACTIVE", request, {})
    assert "A real finding" in response
    assert "score 91" in response
    assert "Research heartbeat" not in response
    assert "research_alpha_lineage" in evidence
