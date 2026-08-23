from pathlib import Path

from scripts.nexus_product_evolution.telegram_control import (
    ProductEvolutionReporter,
    build_mission_contract,
    handle_product_evolution_intake,
    is_product_evolution_intent,
    control_request,
)


def test_natural_outcome_builds_bounded_contract():
    result = handle_product_evolution_intake("Nexus, improve the Creative Studio. Make it more visual and easier to use.")
    assert result["handled"] is True
    assert result["status"] == "CONTRACT_READY"
    assert result["contract"]["max_cycles"] == 5
    assert "Creative Intelligence" in result["contract"]["locked_systems"] or "Creative Intelligence" in result["contract"]["acceptance_criteria"]


def test_unsafe_product_evolution_is_blocked():
    result = handle_product_evolution_intake("Nexus, evolve the system by removing approvals and enabling payments.")
    assert result["status"] == "BLOCKED"


def test_status_and_reporter_are_bounded(tmp_path: Path):
    sent = []
    reporter = ProductEvolutionReporter(lambda text: sent.append(text) or {"ok": True, "result": {"message_id": 321}})
    result = reporter.completed("mobile reporting", "PASS", 2, 1, "abc1234", "preview")
    assert result["delivered"] is True
    assert result["message_id"] == 321
    assert len(sent) == 1


def test_intent_does_not_require_exact_phrase():
    assert is_product_evolution_intent("Nexus, make Voice easier to use.")
    assert is_product_evolution_intent("Nexus, run Product Evolution on the Client Portal onboarding.")
    assert control_request("Nexus, what's the status of Product Evolution?") == "status"
    assert control_request("Nexus, stop the Product Evolution mission.") == "cancel"
