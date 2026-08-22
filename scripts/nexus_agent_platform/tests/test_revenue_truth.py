from datetime import datetime, timezone

import pytest

from nexus_agent_platform import revenue_truth as rt
from nexus_agent_platform.opportunities.engine import import_alpha_opportunity_candidate
from nexus_agent_platform.governed.action_registry import action_exists


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch, tmp_path):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path))


def observation(**overrides):
    values = {
        "metric_key": "actual_revenue",
        "value": 97,
        "unit": "usd",
        "truth_class": "ACTUAL",
        "source_system": "manual_verified_import",
        "source_record_ref": "row-1",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }
    values.update(overrides)
    return rt.build_revenue_observation(**values)


def test_no_source_is_unknown_not_zero_and_observed_zero_is_preserved():
    empty = rt.aggregate_metric("actual_revenue")
    assert empty["value"] is None
    assert empty["truth_class"] == "UNKNOWN"
    assert empty["source_status"] == "NOT_CONNECTED"
    assert rt.record_revenue_observation(observation(value=0, source_record_ref="zero"))["status"] == "RECORDED"
    zero = rt.aggregate_metric("actual_revenue")
    assert zero["value"] == 0
    assert zero["truth_class"] == "ACTUAL"
    assert zero["observed_zero"] is True


def test_truth_classes_required_and_test_synthetic_are_not_actual():
    with pytest.raises(ValueError):
        rt.build_revenue_observation(metric_key="actual_revenue", value="bad", unit="usd", truth_class="ACTUAL", source_system="x", source_record_ref="bad")
    assert rt.record_revenue_observation(observation(truth_class="TEST", source_record_ref="test-97"))["status"] == "RECORDED"
    assert rt.record_revenue_observation(observation(truth_class="SYNTHETIC", source_record_ref="synthetic-97"))["status"] == "RECORDED"
    actual = rt.build_revenue_snapshot()
    assert actual["metrics"]["actual_revenue"]["value"] is None
    assert actual["metrics"]["actual_revenue"]["truth_class"] == "UNKNOWN"
    assert actual["test_revenue"]["value"] == 97
    assert actual["test_revenue"]["truth_class"] == "TEST"
    assert actual["synthetic_revenue"]["value"] == 97
    assert actual["synthetic_revenue"]["truth_class"] == "SYNTHETIC"


def test_duplicate_observation_is_counted_once():
    row = observation(source_record_ref="event-1")
    assert rt.record_revenue_observation(row)["status"] == "RECORDED"
    assert rt.record_revenue_observation(row)["status"] == "DUPLICATE_SUPPRESSED"
    assert rt.aggregate_metric("actual_revenue")["value"] == 97


def test_snapshot_preserves_opportunity_pipeline_and_needs_ray():
    pack = {"schema_version": "nexus.alpha-research-pack.v1", "evidence_refs": ["ev-1"], "claims": [{"evidence_refs": ["ev-1"]}]}
    candidate = {"opportunity_title": "Readiness review campaign", "category": "direct offer", "business": "GoClear", "monetization_path": "review", "target_audience": "owners", "evidence_refs": ["ev-1"], "retrieved_at": datetime.now(timezone.utc).isoformat(), "scores": {"business_fit": 90}, "requires_ray_review": True}
    imported = import_alpha_opportunity_candidate(candidate, research_job_id="r1", research_pack_ref="p1", research_pack=pack)
    assert imported["status"] == "CREATED"
    snapshot = rt.refresh_revenue_snapshot()
    assert snapshot["opportunity_pipeline"]["count"] == 1
    assert snapshot["opportunity_pipeline"]["truth_class"] == "UNKNOWN"
    assert snapshot["needs_ray"][0]["truth_class"] == "OPPORTUNITY_ESTIMATE"
    assert snapshot["metrics"]["actual_revenue"]["value"] is None


def test_hermes_answers_are_truth_grounded():
    snapshot = rt.build_revenue_snapshot()
    actual = rt.answer_revenue_question("How much actual revenue do we have?", snapshot)
    pipeline = rt.answer_revenue_question("What is pipeline versus actual?", snapshot)
    focus = rt.answer_revenue_question("What should I focus on today?", snapshot)
    assert actual["truth_class"] == "UNKNOWN"
    assert "UNKNOWN" in actual["answer"]
    assert pipeline["truth_class"] in {"UNKNOWN", "OPPORTUNITY_ESTIMATE"}
    assert focus["source"] == "Revenue Truth Layer"


def test_financial_mutations_are_not_registered():
    for action in ("stripe.charge", "stripe.refund", "stripe.payout", "subscription.create", "affiliate.enroll", "funding.submit"):
        assert action_exists(action) is False
