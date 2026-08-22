import os
from datetime import datetime, timedelta, timezone

import pytest

from nexus_agent_platform import growth_operations as growth


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path))


def make(**kwargs):
    return growth.build_growth_experiment(
        title=kwargs.pop("title", "Funding readiness content gap"),
        topic=kwargs.pop("topic", "business funding readiness"),
        intent=kwargs.pop("intent", "INFORMATIONAL"),
        primary_metric=kwargs.pop("primary_metric", "readiness_review_leads"),
        evidence_refs=kwargs.pop("evidence_refs", ["ev-public-1"]),
        **kwargs,
    )


def test_contract_and_lifecycle():
    row = make()
    assert growth.validate_growth_experiment(row)["valid"]
    assert growth.persist_growth_experiment(row)["status"] == "CREATED"
    assert growth.transition_growth(row["growth_id"], "NEEDS_RAY_REVIEW")["status"] == "NEEDS_RAY_REVIEW"
    with pytest.raises(ValueError): growth.transition_growth(row["growth_id"], "PUBLISHED")


def test_invalid_schema_and_deduplication():
    row = make()
    assert growth.validate_growth_experiment({"title": "bad"})["valid"] is False
    assert growth.persist_growth_experiment(row)["status"] == "CREATED"
    duplicate = make()
    duplicate["growth_id"] = "different"
    assert growth.persist_growth_experiment(duplicate)["status"] == "DUPLICATE_SUPPRESSED"


def test_keyword_truth_and_gap_brief():
    keyword = growth.keyword_record({"keyword": "business funding readiness", "cpc_estimate": "8.00"})
    assert keyword["truth_class"] == "MANUAL_REVIEWED"
    assert keyword["search_volume"] is None
    gap = growth.build_content_gap(topic="business funding readiness", intent="INFORMATIONAL", existing_coverage="", competitor_coverage="FAQ", evidence_refs=["ev-1"])
    assert gap["recommended_action"] == "NEW_PAGE"
    brief = growth.build_content_brief(gap=gap)
    assert brief["status"] == "DRAFT_ONLY"
    assert brief["external_action_performed"] is False


def test_unsupported_claim_requires_source():
    gap = growth.build_content_gap(topic="funding", intent="UNKNOWN", existing_coverage="", competitor_coverage="", evidence_refs=[])
    brief = growth.build_content_brief(gap=gap)
    assert "NEEDS_SOURCE" in brief["claims_requiring_evidence"]


def test_measurement_pending_is_not_zero():
    result = growth.measurement_state(metric="readiness_review_leads", snapshot={"metrics": {}})
    assert result["status"] == "MEASUREMENT_PENDING"
    assert result["truth_class"] == "UNKNOWN"
    assert result["value"] is None


def test_stale_evidence_is_explicit():
    old = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
    row = make(observed_at=old)
    assert row["freshness"]["status"] == "STALE"


def test_public_audit_boundary():
    with pytest.raises(ValueError): growth.build_public_technical_audit("https://goclearonline.cc/admin")
    result = growth.build_public_technical_audit("https://example.com")
    assert result.get("status_code") == 200 or result.get("status") == "DEPENDENCY_UNAVAILABLE"
    assert result["external_action_performed"] is False


def test_no_publish_or_send_authority():
    forbidden = ("publish", "send_email", "send_sms", "post_social", "create_ad", "spend_money")
    assert all(not hasattr(growth, name) for name in forbidden)


def test_hermes_reads_canonical_growth_and_discloses_measurement_gap():
    row = make()
    growth.persist_growth_experiment(row)
    answer = growth.answer_growth_question("What SEO opportunities do we have?")
    assert answer["source"] == "canonical growth_experiments"
    measurement = growth.answer_growth_question("What has actually worked?")
    assert measurement["status"] == "MEASUREMENT_PENDING"
    assert "NOT_CONNECTED" in measurement["source"]
