from nexus_agent_platform.learning.engine import (
    NO_PROPOSAL,
    STRUCTURED_PROPOSAL_CANDIDATE,
    detect_deterministic_candidate,
    detect_duplicate_research_source,
    detect_low_value_loop,
    detect_retry_heavy_worker,
    run_detectors,
)


def _loop(loop_id="fixture", **overrides):
    row = {
        "loop_id": loop_id,
        "result_status": "success",
        "verifier_status": "pass",
        "ai_calls": 0,
        "value_events": 0,
        "successful_outputs": 1,
        "input_tokens": 0,
        "output_tokens": 0,
        "completed_at": "2026-08-18T00:00:00+00:00",
    }
    row.update(overrides)
    return row


def test_low_value_loop_returns_structured_approval_gated_candidate():
    result = detect_low_value_loop([_loop(), _loop()])
    assert result["result"] == STRUCTURED_PROPOSAL_CANDIDATE
    assert result["proposal"]["status"] == "PROPOSED"
    assert result["proposal"]["approval_required"] is True
    assert result["proposal"]["approval_id"] is None
    assert result["proposal"]["proposal_type"] == "LOOP_CADENCE_CHANGE"


def test_deterministic_candidate_does_not_need_ai():
    result = detect_deterministic_candidate([_loop(), _loop()])
    assert result["result"] == STRUCTURED_PROPOSAL_CANDIDATE
    assert result["observation"]["pattern_type"] == "DETERMINISTIC_CANDIDATE"
    assert result["observation"]["requires_ai_interpretation"] is False


def test_duplicate_and_retry_detectors_use_measured_thresholds():
    duplicate = detect_duplicate_research_source({
        "opportunity": {"id": "op-1"},
        "research": {"source_records_collected": 8, "duplicates_removed": 4},
    })
    assert duplicate["result"] == STRUCTURED_PROPOSAL_CANDIDATE
    assert duplicate["proposal"]["proposal_type"] == "DEDUPE_POLICY_CHANGE"

    retry = detect_retry_heavy_worker([
        {"worker_id": "a", "retry_count": 2, "status": "pass", "finished_at": "2026-08-18T00:00:00+00:00"},
        {"worker_id": "a", "retry_count": 2, "status": "pass", "finished_at": "2026-08-18T00:00:00+00:00"},
    ])
    assert retry["result"] == STRUCTURED_PROPOSAL_CANDIDATE
    assert retry["observation"]["pattern_type"] == "HIGH_RETRY_RATE"


def test_detectors_return_no_proposal_when_evidence_is_insufficient():
    result = run_detectors({"loop_rows": [], "builder_rows": [], "pilot": {}})
    assert len(result) == 9
    assert all(item["result"] == NO_PROPOSAL for item in result)


def test_proposals_are_not_executable_or_auto_promoted():
    result = detect_low_value_loop([_loop(), _loop()])
    proposal = result["proposal"]
    assert proposal["status"] == "PROPOSED"
    assert proposal["recommended_action"].startswith("Review and authorize")
    assert proposal["candidate_metrics"] == {}
