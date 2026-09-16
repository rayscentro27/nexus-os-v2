from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "research"))

from research_v2 import (  # noqa: E402
    action_sufficiency,
    alpha_collaborative_analysis,
    classify_intents,
    extract_claims,
    investigation_decision,
    knowledge_maturity,
    opportunity_thesis,
    productivity_metrics,
    score_plan,
    source_reputation,
    strategy_package,
)


def test_intents_are_multi_label_and_learning_is_not_rejected():
    intents = classify_intents("new software business model with SEO and compliance questions")
    assert "SOFTWARE_CAPABILITY" in intents
    assert "BUSINESS_MODEL_RESEARCH" in intents
    assert "SEO_RESEARCH" in intents
    assert investigation_decision(kind="KNOWLEDGE")["decision"] == "KNOWLEDGE_CAPTURE"


def test_first_observation_has_no_novelty_penalty():
    result = knowledge_maturity(0)
    assert result["novelty_status"] == "BASELINE_FIRST_OBSERVATION"
    assert result["no_novelty_penalty"] is True
    assert result["novelty_penalty"] == 0.0


def test_claims_are_distinct_and_typed():
    claims = extract_claims(
        "The product costs $20 per month. The company reports revenue of $10,000 per month. This strategy should use a short funnel.",
        {"source_id": "source-1", "source_url": "https://example.test"},
    )
    assert len(claims) == 3
    assert {claim["claim_type"] for claim in claims} >= {"REVENUE_CLAIM", "STRATEGY_CLAIM"}
    assert all(claim["source_segment"] for claim in claims)


def test_alpha_is_action_dependent_and_non_veto():
    result = alpha_collaborative_analysis({"facts": ["fact"], "unknowns": ["demand"]}, proposed_action="LOW_COST_INTERNAL_TEST")
    assert result["alpha_assessment"] == "SUFFICIENT_FOR_BOUNDED_TEST"
    assert result["gatekeeper"] is False
    assert result["research_may_continue"] is True
    assert action_sufficiency("LARGE_CAPITAL_COMMITMENT")["required_evidence_level"] == "HIGH"


def test_thesis_plan_reputation_and_metrics_are_explicit():
    thesis = opportunity_thesis(title="Independent local service", customer="local owners", problem="inconvenience")
    plan = score_plan({"assumptions": thesis["assumptions"], "market_demand": "UNKNOWN"})
    reputation = source_reputation({"source_id": "s", "false_or_contradicted_claims": 4})
    strategy = strategy_package(title="funnel method", text="Use a narrow message and measure qualified response before scaling.")
    metrics = productivity_metrics([{"acquired": True, "processing_status": "FULLY_PROCESSED", "substantive_findings": ["x"], "summary_created": True, "extraction_created": True}])
    assert thesis["unknowns"]
    assert plan["not_a_raw_idea_score"] is True
    assert reputation["source_trust_status"] == "UNRELIABLE"
    assert strategy["test_method"]
    assert metrics["useful_output_rate"] == 1.0
