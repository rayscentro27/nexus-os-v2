from datetime import datetime, timezone

import pytest

from nexus_agent_platform.opportunities.engine import (
    GOVERNED_OPPORTUNITY_SCHEMA,
    SCORING_POLICY_VERSION,
    create_opportunity_review_request,
    import_alpha_opportunity_candidate,
    ingest_legacy_opportunity,
    list_governed_opportunities,
    mark_stale_opportunities,
    opportunity_portfolio,
    opportunity_rankings,
    prepare_opportunity_work_order,
    answer_opportunity_question,
    validate_alpha_opportunity_candidate,
    validate_governed_opportunity_record,
)
from nexus_agent_platform.governed import approvals


@pytest.fixture(autouse=True)
def isolated_governed_store(monkeypatch, tmp_path):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path))


def _candidate(**overrides):
    value = {
        "opportunity_title": "GoClear funding readiness review",
        "description": "Evidence-backed public offer candidate for a bounded readiness review.",
        "category": "direct offer",
        "business": "GoClear",
        "monetization_path": "fixed-price review",
        "target_audience": "small business owners",
        "evidence_refs": ["ev-public-1"],
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "freshness_requirement": "CURRENT",
        "scores": {"revenue_potential": 70, "speed_to_value": 80, "business_fit": 90, "confidence": 80},
        "value_estimate": {"status": "EVIDENCE_BACKED_ESTIMATE", "low": 50, "expected": 97, "high": 150, "currency": "USD", "time_horizon": "0-30 DAYS", "assumptions": ["price is still subject to Ray review"]},
        "risks": ["COMPLIANCE"],
        "unknowns": ["conversion rate"],
    }
    value.update(overrides)
    return value


def _pack():
    return {"schema_version": "nexus.alpha-research-pack.v1", "research_job_id": "research-k", "evidence_refs": ["ev-public-1"], "claims": [{"evidence_refs": ["ev-public-1"]}]}


def test_alpha_candidate_contract_and_evidence_validation():
    candidate = _candidate()
    result = validate_alpha_opportunity_candidate(candidate, _pack())
    assert result["valid"] is True
    assert validate_alpha_opportunity_candidate({"title": "missing evidence"}, _pack())["status"] == "NEEDS_RESEARCH"
    imported = import_alpha_opportunity_candidate(candidate, research_job_id="research-k", research_pack_ref="alpha-pack:research-k", research_pack=_pack())
    assert imported["status"] == "CREATED"
    opportunity = imported["opportunity"]
    assert opportunity["schema_version"] == GOVERNED_OPPORTUNITY_SCHEMA
    assert opportunity["status"] == "QUALIFIED"
    assert opportunity["scores"]["policy"] == SCORING_POLICY_VERSION
    assert opportunity["value_estimate"]["actual_revenue"] is None
    assert validate_governed_opportunity_record({"schema_version": "wrong"})["valid"] is False


def test_duplicate_related_and_distinct_candidates_are_handled():
    candidate = _candidate()
    first = import_alpha_opportunity_candidate(candidate, research_job_id="r1", research_pack_ref="p1", research_pack=_pack())
    second = import_alpha_opportunity_candidate(candidate, research_job_id="r2", research_pack_ref="p2", research_pack=_pack())
    assert first["status"] == "CREATED"
    assert second["status"] == "DUPLICATE_SUPPRESSED"
    distinct = import_alpha_opportunity_candidate(_candidate(opportunity_title="GoClear public funding checklist", category="content"), research_job_id="r3", research_pack_ref="p3", research_pack=_pack())
    assert distinct["status"] == "CREATED"
    assert len(list_governed_opportunities()) == 2


def test_legacy_candidate_stays_unvalidated_and_missing_evidence_is_not_qualified():
    result = ingest_legacy_opportunity({"title": "Legacy affiliate idea", "category": "affiliate", "monetization": "referral"})
    assert result["opportunity"]["status"] == "NEEDS_RESEARCH"
    assert result["opportunity"]["legacy_classification"] == "UNVALIDATED_LEGACY"
    assert result["opportunity"]["value_estimate"]["status"] == "UNKNOWN"


def test_stale_evidence_transitions_and_rankings(monkeypatch):
    old = _candidate(opportunity_title="Old evidence offer", retrieved_at="2020-01-01T00:00:00+00:00")
    result = import_alpha_opportunity_candidate(old, research_job_id="old", research_pack_ref="old-pack", research_pack=_pack())
    assert result["opportunity"]["status"] == "NEEDS_RESEARCH"
    # Force a qualified record with stale freshness to exercise the explicit lifecycle path.
    from nexus_agent_platform.governed import persistence
    row = {**result["opportunity"], "status": "QUALIFIED", "freshness": {"requirement": "CURRENT", "status": "STALE"}}
    persistence.append_record("opportunities", row)
    changed = mark_stale_opportunities()
    assert changed and changed[0]["status"] == "STALE"
    portfolio = opportunity_portfolio()
    assert "pipeline_value_estimate" in portfolio
    assert "best_overall" in opportunity_rankings()


def test_ray_review_and_synthetic_work_order_handoff_are_governed(monkeypatch, tmp_path):
    imported = import_alpha_opportunity_candidate(_candidate(opportunity_title="Reviewable readiness offer"), research_job_id="review", research_pack_ref="review-pack", research_pack=_pack())
    oid = imported["opportunity"]["opportunity_id"]
    review = create_opportunity_review_request(oid)
    assert review["opportunity"]["status"] == "NEEDS_RAY_REVIEW"
    assert review["approval"]["status"] == "pending"
    # Certification uses a synthetic explicit approval only to prove the handoff shape.
    approvals.resolve_approval(review["approval"]["id"], "approve", resolved_by="ray")
    from nexus_agent_platform.opportunities.engine import transition_governed_opportunity
    transition_governed_opportunity(oid, "APPROVED_FOR_PLANNING", approval_id=review["approval"]["id"])
    handoff = prepare_opportunity_work_order(oid, review["approval"]["id"])
    assert handoff["work_order"]["status"] == "queued"
    assert handoff["external_action_performed"] is False
    assert handoff["opportunity"]["status"] == "CONVERTED_TO_WORK_ORDER"


def test_hermes_queries_read_canonical_rankings():
    import_alpha_opportunity_candidate(_candidate(), research_job_id="hermes", research_pack_ref="hermes-pack", research_pack=_pack())
    assert answer_opportunity_question("What are my best money opportunities?")["type"] == "best_overall"
    assert answer_opportunity_question("What needs Ray approval?")["type"] == "needs_ray"
    assert answer_opportunity_question("Why is this ranked above that?")["scoring_policy"] == SCORING_POLICY_VERSION
