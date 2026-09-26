import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from nexus_agent_platform.creative.creative_intelligence_v2 import (  # noqa: E402
    CreativeIdeationBudget,
    diversity_gate,
    extract_creative_tension,
    run_creative_intelligence_v2,
    select_ideation_stances,
)
from nexus_agent_platform.creative.intelligence import generate_concept_round_v2  # noqa: E402


def brief():
    return {
        "creative_brief_id": "brief-v2",
        "audience": "small-business owners preparing for a funding conversation",
        "customer_tension": "they do not know what evidence to prepare",
        "desired_outcome": "choose the next safe preparation step",
        "evidence_constraints": ["no invented proof", "draft only"],
    }


def response_for(stance, round_number=1):
    return {
        "status": "PASS",
        "concepts": [{
            "human_insight": f"insight {stance} {round_number}",
            "audience_tension": "uncertainty about preparation",
            "strategic_angle": f"angle {stance} {round_number}",
            "central_idea": f"central idea {stance} {round_number}",
            "visual_metaphor": f"metaphor {stance} {round_number}",
            "narrative_structure": f"story {stance} {round_number}",
            "emotional_direction": f"emotion {stance}",
            "hook_family": f"hook {stance}",
            "visual_family": f"visual {stance}",
            "layout_family": f"layout {stance}",
            "cta_pattern": f"cta {stance}",
            "channel_fit": "landing page",
            "proof_boundary": "no unsupported claims",
        }],
    }


class FakeModel:
    def __init__(self):
        self.calls = []

    def call(self, purpose, instruction, context):
        self.calls.append((purpose, instruction, context))
        if "Contrarian" in purpose:
            return {"status": "PASS", "alternative_territory": "find a less obvious frame"}
        if "Customer Advocate" in purpose:
            return {"status": "PASS", "findings": ["customer tension is explicit"]}
        if "Critic" in purpose:
            return {"status": "PASS", "verdicts": []}
        if "Director" in purpose:
            return {"status": "PASS", "primary": "first", "alternate": "second", "experimental": "third"}
        stance = context.get("stance", context.get("build_on_stance", {"stance_id": "build"}))["stance_id"]
        round_number = 2 if "Build On" in purpose else 1
        return response_for(stance, round_number)


def test_tension_is_bounded_to_brief_fields():
    value = extract_creative_tension(brief())
    assert value["audience"] == brief()["audience"]
    assert value["current_reality"] == brief()["customer_tension"]
    assert value["proof_boundary"] == brief()["evidence_constraints"]


def test_stances_are_bounded_and_distinct():
    stances = select_ideation_stances(brief(), max_stances=5)
    assert 4 <= len(stances) <= 7
    assert len({x["stance_id"] for x in stances}) == len(stances)


def test_diversity_gate_rejects_cosmetic_clone():
    model = FakeModel()
    result = run_creative_intelligence_v2(brief(), model, budget=CreativeIdeationBudget(max_total_calls=6))
    clone = dict(result["concepts"][0])
    clone["concept_id"] = "clone"
    gate = diversity_gate([result["concepts"][0], clone])
    assert gate["status"] == "REGENERATE_REQUIRED"
    assert gate["rejected"][0]["diversity_gate"] in {"NEAR_DUPLICATE", "HIGH_SIMILARITY"}


def test_initial_generators_are_blind_and_build_on_sees_pool_only_afterward():
    model = FakeModel()
    result = run_creative_intelligence_v2(brief(), model, budget=CreativeIdeationBudget(max_total_calls=6))
    initial = [x for x in model.calls if "Creative V2 " in x[0] and x[0].split()[-1] not in {"On", "Contrarian", "Advocate", "Critic", "Director"}]
    assert initial
    assert all("pool" not in ctx for _, _, ctx in initial)
    build = [x for x in model.calls if "Build On" in x[0]]
    assert build
    assert "FULL_BOUNDED_CONTEXT_JSON" in build[0][1]
    assert "pool" in build[0][1]


def test_v2_budget_is_bounded():
    model = FakeModel()
    budget = CreativeIdeationBudget(max_total_calls=12)
    result = run_creative_intelligence_v2(brief(), model, budget=budget)
    assert result["calls"] <= budget.max_total_calls
    assert result["blind_generation"] is True


def test_v2_is_exposed_through_canonical_intelligence_entrypoint():
    model = FakeModel()
    result = generate_concept_round_v2(brief(), model, budget=CreativeIdeationBudget(max_total_calls=6))
    assert result["model_assisted_ideation"] == "PASS_REAL_BOUNDED"
    assert result["round_id"].startswith("v2_round_")
    assert result["evaluation"]["concept_count"] >= 1
