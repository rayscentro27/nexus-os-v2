import pytest

from nexus_agent_platform import intelligence_fabric as fabric
from nexus_agent_platform.governed import persistence


DEPARTMENTS = [
    "ALPHA", "HERMES_NOVA", "SYSTEMS_ENGINEERING", "CREATIVE", "MARKETING",
    "SEO", "CLYDE_CREDIT", "FUNDING", "FINANCE", "BUSINESS_OPPORTUNITY",
    "TRADING_RESEARCH",
]


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path))


def test_all_departments_can_request_alpha_review_and_resume():
    for department in DEPARTMENTS:
        request = fabric.build_research_request(
            department=department,
            objective_id=f"objective-{department.lower()}",
            parent_goal_id="goal-company",
            work_order_id=f"wo-{department.lower()}",
            question=f"What verified internal capability does {department} need next?",
            knowledge_gap="Need evidence-backed next action for this department.",
        )
        result = fabric.run_research_request(request, [{"text": "A bounded internal capability receipt supports the next action.", "source": "engineering-fixture"}], claim="A bounded capability receipt supports the department next action.")
        assert result["alpha_decision"] == "QUALIFIED"
        resumed = fabric.resume_department(result["request"], next_action="Continue the original objective using the Alpha-reviewed result.")
        assert resumed["department_resume"] == "RESUMED"
        assert resumed["objective_id"] == request["objective_id"]


def test_weak_evidence_creates_targeted_follow_up_without_failing_parent():
    request = fabric.build_research_request(department="MARKETING", objective_id="goal-revenue", question="Which evidence is missing for this channel?", knowledge_gap="Need independently verified demand evidence.")
    result = fabric.run_research_request(request, [], claim="This claim has no evidence.")
    assert result["alpha_decision"] == "MORE_RESEARCH_REQUIRED"
    assert result["follow_up"]["department"] == "MARKETING"
    assert result["request"]["objective_id"] == "goal-revenue"


def test_result_feedback_returns_through_research_and_alpha():
    result = fabric.record_result_feedback(
        department="SYSTEMS_ENGINEERING", objective_id="goal-reliability",
        action="Run bounded benchmark", result="The benchmark receipt was produced.",
        evidence=[{"evidence_id": "bench-1", "text": "Measured internal benchmark receipt.", "source": "test"}],
        outcome="SUCCESS", what_changed="A measured receipt now exists.", knowledge_implication="The benchmark can inform the next reliability action.",
    )
    assert result["feedback"]["research_review_state"] == "COMPLETE"
    assert result["feedback"]["alpha_review_state"] == "QUALIFIED"
    assert result["research"]["request"]["objective_id"] == "goal-reliability"
    assert persistence.read_records("result_feedback")
