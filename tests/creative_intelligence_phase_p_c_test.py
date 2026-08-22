import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from nexus_agent_platform.creative.intelligence import (  # noqa: E402
    build_campaign_packet,
    build_feedback,
    build_preference_profile,
    creative_signature,
    evaluate_concept_set,
    generate_concept_round,
    persist_concept_round,
    persist_feedback,
    rank_with_preferences,
    similarity,
)
from nexus_agent_platform.creative.studio import answer_creative_question  # noqa: E402


def brief():
    return {"creative_brief_id": "brief-pc", "business_id": "goclear", "title": "Funding readiness", "target_offer": "goclear_readiness_review_97", "audience": "small-business owners", "evidence_refs": ["ev-public"], "measurement_metric": "readiness_review_leads"}


def test_dynamic_round_has_six_distinct_concepts_and_signatures(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path))
    result = generate_concept_round(brief())
    assert result["status"] == "PASS"
    assert len(result["concepts"]) == 6
    assert len({c["signature_fingerprint"] for c in result["concepts"]}) == 6
    assert sum(c["exploration"] for c in result["concepts"]) >= 1
    assert result["ai_calls"] == 0


def test_cosmetic_clone_is_rejected():
    result = generate_concept_round(brief())
    concepts = result["concepts"]
    clone = dict(concepts[0])
    clone["concept_id"] = "clone"
    clone["signature_fingerprint"] = concepts[0]["signature_fingerprint"]
    evaluation = evaluate_concept_set([concepts[0], clone, *concepts[1:5]])
    assert evaluation["status"] == "CREATIVE_DIVERSITY_INSUFFICIENT"


def test_history_penalizes_semantic_repetition(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path))
    first = generate_concept_round(brief())
    persisted = persist_concept_round(first)
    assert persisted["persistence"] == "CREATED"
    second = generate_concept_round(brief())
    assert second["evaluation"]["concepts"][0]["historical_similarity"] in {"HIGH", "NEAR_DUPLICATE"}


def test_feedback_updates_dimensions_without_fabricating_ray_history(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path))
    feedback = build_feedback(concept_id="concept-x", decision="REVISION_MINOR", positive_tags=["LOVE_METAPHOR"], negative_tags=["TOO_MUCH_TEXT"], synthetic_fixture=True)
    persisted = persist_feedback(feedback)
    profile = build_preference_profile([persisted])
    assert profile["source"] == "explicit_feedback_only"
    assert profile["synthetic_feedback_count"] == 1
    assert profile["preferred_qualities"]["LOVE_METAPHOR"]["preference"] == "preferred"
    assert profile["preferred_qualities"]["TOO_MUCH_TEXT"]["preference"] == "disliked"


def test_preferences_rank_without_removing_exploration():
    result = generate_concept_round(brief())
    profile = {"preferred_qualities": {"LOVE_METAPHOR": {"preference": "preferred"}}}
    ranked = rank_with_preferences(result["concepts"], profile)
    assert ranked
    assert any(c["exploration"] for c in ranked)
    assert len({c["concept_id"] for c in ranked}) == len(ranked)


def test_campaign_translates_one_idea_across_media():
    concept = generate_concept_round(brief())["concepts"][0]
    packet = build_campaign_packet(concept, brief())
    assert packet["central_idea"] == concept["central_idea"]
    assert packet["landing_page_direction"]["structure"]
    assert packet["video_direction"]["story"]
    assert packet["image_direction"]["metaphor"] == concept["visual_metaphor"]
    assert packet["external_action_performed"] is False


def test_existing_studio_question_path_reads_canonical_intelligence():
    answer = answer_creative_question("Which concept is most original?")
    assert "creative_intelligence" in answer
    assert answer["source"] == "creative_concepts"
