from __future__ import annotations

import json
from pathlib import Path

import pytest

from nexus_agent_platform.creative.lab import (
    CreativeBudget,
    CreativeLabError,
    build_creative_brief,
    build_creative_lab_report,
    build_creative_pilot,
    build_creative_territories,
    evaluate_creative_set,
    merge_ai_creative_rationale,
    recommended_creative_tier,
    validate_creative_claims,
)
from nexus_agent_platform.creative.intelligence import run_critic_panel
from nexus_agent_platform.research.open_source_scout import build_open_source_scout_report


def _opportunity():
    return build_open_source_scout_report()["opportunity_input"]


def test_critic_panel_reconciles_creative_brand_and_compliance():
    result = run_critic_panel([{"concept_id": "safe", "brief_fit": 84, "brand_fit": 82, "brand_voice": "measured", "signature_fingerprint": "x", "message": "Review evidence before choosing a next step."},
                               {"concept_id": "risky", "brief_fit": 90, "brand_fit": 80, "signature_fingerprint": "y", "message": "Guaranteed instant approval."}])
    assert result["status"] == "PASS"
    assert result["review_count"] == 2
    assert result["accepted_count"] == 1
    assert result["reviews"][1]["compliance_critic"]["status"] == "FAIL"


def test_fewer_than_three_territories_rejected():
    with pytest.raises(CreativeLabError):
        evaluate_creative_set([{"concept_name": "One", "positioning": "x", "target_audience": "y", "primary_hook": "z", "differentiator": "d", "evidence_refs": [1]} , {"concept_name": "Two", "positioning": "x", "target_audience": "y", "primary_hook": "z", "differentiator": "d", "evidence_refs": [1]}])


def test_cosmetic_only_variants_rejected():
    territory = {
        "concept_name": "A",
        "positioning": "Proof-first workspace",
        "target_audience": "Operators",
        "primary_hook": "Evidence first",
        "differentiator": "Proof visible",
        "brand_voice": "tight",
        "emotional_direction": "calm",
        "visual_direction": "minimal",
        "layout_direction": "grid",
        "cta": "Open",
        "evidence_refs": ["x"],
    }
    with pytest.raises(CreativeLabError):
        evaluate_creative_set([territory, {**territory, "concept_name": "B"}, {**territory, "concept_name": "C"}])


def test_evidence_refs_required():
    issues = validate_creative_claims({"concept_name": "A", "target_audience": "Ops", "primary_hook": "Hook", "differentiator": "Diff", "evidence_refs": []})
    assert "evidence_refs_required" in issues


def test_unsupported_market_claims_flagged():
    issues = validate_creative_claims({"concept_name": "A", "target_audience": "Ops", "primary_hook": "Guaranteed conversion", "differentiator": "Diff", "evidence_refs": ["x"], "claim": "guaranteed conversions"})
    assert "unsupported_market_claim" in issues


def test_deterministic_scores_reproducible():
    opportunity = _opportunity()
    brief = build_creative_brief(opportunity, opportunity["evidence"], [{"title": "ref", "source": "src", "reference": "x"}])
    a = build_creative_territories(brief)
    b = build_creative_territories(brief)
    assert [t["creative_score"] for t in a] == [t["creative_score"] for t in b]


def test_ai_rationale_cannot_overwrite_base_score_silently():
    merged = merge_ai_creative_rationale({"base_score": 70, "creative_score": 70}, {"base_score": 99, "creative_score": 1, "rationale": "strong"})
    assert merged["base_score"] == 70
    assert merged["creative_score"] == 70
    assert merged["ai_proposed_base_score"] == 99


def test_t3_escalation_requires_explicit_condition():
    assert recommended_creative_tier(90) == "T2_STANDARD_AI"
    assert recommended_creative_tier(90, explicit_premium_escalation=True) == "T3_PREMIUM_AI"


def test_full_history_not_replayed():
    opportunity = _opportunity()
    brief = build_creative_brief(opportunity, opportunity["evidence"], [{"title": "ref", "source": "src", "reference": "x"}], previous_state={"last_territory_hash": "abc", "history": ["a"] * 1000})
    assert "history" not in brief or brief["history"] is None
    assert "full_history" not in brief or brief["full_history"] is None
    assert len(json.dumps(brief)) < 5000


def test_token_and_cost_ceiling_enforced():
    budget = CreativeBudget(max_ai_calls=0, max_input_tokens=120, max_output_tokens=60, cost_ceiling_usd=0.01)
    assert budget.max_ai_calls == 0
    assert budget.cost_ceiling_usd == 0.01


def test_creative_skill_remains_non_persistent():
    from pathlib import Path

    skill = Path("plugins/nexus-hermes-plugin/skills/nexus-creative-director/SKILL.md")
    assert skill.exists()
    text = skill.read_text(encoding="utf-8")
    assert "status: DRAFT" in text
    assert "lifecycle: DRAFT" in text


def test_client_portal_unchanged():
    portal = Path("src/client-v2/pages/DashboardV2.tsx")
    before = portal.read_text(encoding="utf-8")
    assert "Creative Lab" not in before


def test_safe_pilot_creates_build_spec():
    report = build_creative_lab_report()
    assert report["territory_count"] == 3
    assert report["verification"]["status"] == "passed"
    assert report["build_spec"]
    assert report["zero_token_execution"] is True
    assert report["ai_calls"] == 0
