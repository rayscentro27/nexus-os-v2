from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from nexus_agent_platform.loops.runtime import (
    LoopRuntime,
    LoopStateStore,
    opportunity_discovery_loop_spec,
    run_opportunity_discovery_loop,
)
from nexus_agent_platform.opportunities.engine import (
    OpportunityStateTransitionError,
    build_opportunity_business_case,
    build_opportunity_discovery_packet,
    build_opportunity_evidence,
    canonicalize_opportunity_record,
    dedupe_opportunity_records,
    merge_ai_result,
    normalize_opportunity_status,
    recommended_ai_tier,
    score_opportunity_record,
    validate_opportunity_transition,
)
from nexus_agent_platform.loops.runtime import _cost_for_tier


def _runtime(tmp_path: Path) -> tuple[LoopRuntime, Path, Path]:
    state_path = tmp_path / "loop_state.json"
    ledger_path = tmp_path / "loop_ledger.jsonl"
    runtime = LoopRuntime(state_store=LoopStateStore(state_path), ledger_path=ledger_path)
    return runtime, state_path, ledger_path


def _fake_capability_factory(payloads: dict[str, dict]):
    def _fake(agent_id: str, capability: str, arguments=None, conversation_id: str = "", trace_id: str = ""):
        payload = payloads.get(capability)
        if payload is None:
            raise AssertionError(f"unexpected capability: {capability}")
        return payload

    return _fake


def test_duplicate_opportunity_does_not_create_second_record():
    opportunities_payload = {
        "status": "success",
        "source_type": "live_governed_read",
        "data": {
            "total": 2,
            "items": [
                {"id": "opp_1", "title": "Lead magnet", "status": "open", "revenue_potential": 500},
                {"id": "opp_1", "title": "Lead magnet", "status": "open", "revenue_potential": 500},
            ],
        },
    }
    research_payload = {
        "status": "success",
        "source_type": "live_governed_read",
        "data": {"runs": {"total": 0, "items": []}, "results": {"total": 0, "items": []}},
    }
    business_payload = {
        "status": "success",
        "source_type": "study_snapshot_artifact",
        "offers_count": 9,
        "offers": [],
    }

    packet = build_opportunity_discovery_packet(
        opportunities_payload=opportunities_payload,
        research_payload=research_payload,
        business_payload=business_payload,
    )
    assert len(packet["canonical_opportunities"]) == 1


def test_low_signal_opportunity_uses_zero_ai_calls(monkeypatch, tmp_path):
    runtime, _, ledger_path = _runtime(tmp_path)
    monkeypatch.setattr(
        "nexus_agent_platform.loops.runtime.execute_shared_capability",
        _fake_capability_factory(
            {
                "get_opportunities": {
                    "status": "success",
                    "source_type": "live_governed_read",
                    "data": {
                        "total": 1,
                        "items": [{"id": "opp_low", "title": "Low signal", "status": "closed", "revenue_potential": 0}],
                    },
                },
                "get_recent_research": {
                    "status": "success",
                    "source_type": "live_governed_read",
                    "data": {"runs": {"total": 0, "items": []}, "results": {"total": 0, "items": []}},
                },
                "get_business_model_summary": {
                    "status": "success",
                    "source_type": "study_snapshot_artifact",
                    "offers_count": 9,
                    "offers": [],
                },
            }
        ),
    )

    def _ai_call(payload):
        raise AssertionError("AI should not be called for low-signal input")

    result = runtime.run(opportunity_discovery_loop_spec, {"window": "today"}, ai_call=_ai_call)
    assert result.ai_calls == 0
    assert result.zero_token_execution is True
    ledger = json.loads(ledger_path.read_text(encoding="utf-8").splitlines()[-1])
    assert ledger["zero_token_execution"] is True


def test_deterministic_score_is_stable_and_reproducible():
    record = canonicalize_opportunity_record(
        {
            "id": "opp_score",
            "title": "Credit readiness checklist",
            "summary": "Capture leads before a paid review",
            "status": "open",
            "action_state": "active",
            "composite_score": 6.0,
            "priority": "medium",
            "updated_at": "2026-07-06T22:19:11.345379+00:00",
        },
        source="recommendations",
        source_type="public_recommendation_snapshot",
    )
    assert record["base_score"] == record["opportunity_score"]
    again = score_opportunity_record(record)
    assert again["base_score"] == record["base_score"]
    assert again["opportunity_score"] == record["opportunity_score"]


def test_ai_cannot_overwrite_deterministic_score_silently():
    reduced = {
        "status": "success",
        "canonical_record": {"id": "opp_1", "base_score": 47, "opportunity_score": 47, "status": "DISCOVERED"},
        "canonical_opportunities": [{"id": "opp_1", "base_score": 47, "opportunity_score": 47}],
    }
    merged = merge_ai_result(reduced, {"base_score": 99, "opportunity_score": 1, "ai_summary": "strong"})
    assert merged["canonical_record"]["base_score"] == 47
    assert merged["canonical_record"]["opportunity_score"] == 47
    assert merged["ai_proposed_base_score"] == 99
    assert merged["ai_proposed_opportunity_score"] == 1


def test_evidence_provenance_is_required():
    with pytest.raises(ValueError):
        build_opportunity_evidence(source_id="", source_type="live_governed_read", classification="KNOWN", summary="x")
    with pytest.raises(ValueError):
        build_opportunity_evidence(source_id="x", source_type="", classification="KNOWN", summary="x")

    evidence = build_opportunity_evidence(
        source_id="rec_1",
        source_type="public_recommendation_snapshot",
        classification="KNOWN",
        summary="Lead magnet",
        provenance={"source": "recommendations"},
    )
    assert evidence["provenance"]["source"] == "recommendations"


def test_known_inferred_unverified_preserved():
    known = build_opportunity_evidence(
        source_id="rec_1",
        source_type="public_recommendation_snapshot",
        classification="KNOWN",
        summary="Known evidence",
    )
    inferred = build_opportunity_evidence(
        source_id="rec_2",
        source_type="public_recommendation_snapshot",
        classification="INFERRED",
        summary="Inferred evidence",
    )
    unverified = build_opportunity_evidence(
        source_id="rec_3",
        source_type="public_recommendation_snapshot",
        classification="UNVERIFIED",
        summary="Unverified evidence",
    )
    assert known["classification"] == "KNOWN"
    assert inferred["classification"] == "INFERRED"
    assert unverified["classification"] == "UNVERIFIED"


def test_invalid_state_transition_rejected():
    with pytest.raises(OpportunityStateTransitionError):
        validate_opportunity_transition("REJECTED", "LAUNCHED")
    assert validate_opportunity_transition("DISCOVERED", "RESEARCHING") is True
    assert normalize_opportunity_status("open", "active") == "BUILDING"


def test_t3_escalation_requires_explicit_condition():
    assert recommended_ai_tier(85) == "T2_STANDARD_AI"
    assert recommended_ai_tier(85, explicit_premium_escalation=True) == "T3_PREMIUM_AI"


def test_no_full_history_replay(monkeypatch, tmp_path):
    runtime, _, _ = _runtime(tmp_path)
    monkeypatch.setattr(
        "nexus_agent_platform.loops.runtime.execute_shared_capability",
        _fake_capability_factory(
            {
                    "get_opportunities": {
                        "status": "success",
                        "source_type": "live_governed_read",
                        "data": {
                            "total": 1,
                            "items": [{
                                "id": "opp_10",
                                "title": "High value",
                                "status": "open",
                                "revenue_potential": 6000,
                                "composite_score": 9.0,
                                "priority": "high",
                                "updated_at": "2026-08-17T00:00:00+00:00",
                            }],
                        },
                    },
                "get_recent_research": {
                    "status": "success",
                    "source_type": "live_governed_read",
                    "data": {"runs": {"total": 1, "items": [{"id": "r1"}]}, "results": {"total": 1, "items": [{"id": "r1"}]}},
                },
                "get_business_model_summary": {
                    "status": "success",
                    "source_type": "study_snapshot_artifact",
                    "offers_count": 9,
                    "offers": [],
                },
            }
        ),
    )

    def _ai_call(payload):
        ctx = payload["input_context"]
        assert "history" not in ctx
        assert "full_history" not in ctx
        assert len(json.dumps(ctx)) < 5000
        return {"status": "success", "ai_summary": "short synthesis", "candidate_ids": ["opp_10"]}

    result = runtime.run(opportunity_discovery_loop_spec, {"window": "today"}, ai_call=_ai_call)
    assert result.ai_used is True


def test_opportunity_loop_writes_canonical_record(monkeypatch, tmp_path):
    runtime, state_path, _ = _runtime(tmp_path)
    monkeypatch.setattr(
        "nexus_agent_platform.loops.runtime.execute_shared_capability",
        _fake_capability_factory(
            {
                "get_opportunities": {
                    "status": "success",
                    "source_type": "live_governed_read",
                    "data": {
                        "total": 1,
                        "items": [{"id": "opp_11", "title": "Checklist lead magnet", "status": "open", "revenue_potential": 500}],
                    },
                },
                "get_recent_research": {
                    "status": "success",
                    "source_type": "live_governed_read",
                    "data": {"runs": {"total": 0, "items": []}, "results": {"total": 0, "items": []}},
                },
                "get_business_model_summary": {
                    "status": "success",
                    "source_type": "study_snapshot_artifact",
                    "offers_count": 9,
                    "offers": [],
                },
            }
        ),
    )

    result = runtime.run(opportunity_discovery_loop_spec, {"window": "today"})
    assert result.memory_record["canonical_record"]["id"] == "opp_11"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["loops"]["opportunity_discovery_loop"]["last_run"]["canonical_record"]["id"] == "opp_11"


def test_cost_calculation_unit_is_verified():
    assert _cost_for_tier("T1_CHEAP_AI", 163, 270) == 0.2165


def test_canonical_business_case_skeleton():
    record = canonicalize_opportunity_record(
        {
            "id": "opp_case",
            "title": "Free checklist lead magnet",
            "summary": "Capture emails and validate demand",
            "status": "open",
            "composite_score": 6.0,
        },
        source="recommendations",
        source_type="public_recommendation_snapshot",
    )
    case = build_opportunity_business_case(record)
    assert case["validation_plan"]
    assert case["recommended_next_action"]
