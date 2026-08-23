from pathlib import Path

from scripts.nexus_product_evolution.loop import (
    FailureClass,
    MissionContract,
    ProductEvolutionLoop,
    Stage,
)


def test_loop_repairs_once_and_stops_on_pass(tmp_path: Path):
    attempts = {"build": 0}
    contract = MissionContract(
        goal="bounded test mission",
        user_visible_outcome="a passing pilot",
        acceptance_criteria=["critic passes"],
        max_cycles=3,
    )

    def build():
        attempts["build"] += 1
        return {"status": "FAIL" if attempts["build"] == 1 else "PASS", "error": "fixture failure", "failure_class": FailureClass.IMPLEMENTATION_BUG.value}

    def repair(_failure):
        return {"status": "PASS", "action": "diagnosed fixture and repaired"}

    result = ProductEvolutionLoop(receipt_dir=tmp_path).run(
        contract,
        mission_id="test-mission",
        stages={Stage.BUILD: build},
        critic=lambda _contract, evidence: {"status": "PASS", "scores": {"goal_completion": 5}},
        repair=repair,
    )
    assert result.status == "PASS"
    assert result.cycles == 2
    assert Path(result.receipt_path).exists()


def test_loop_does_not_repeat_identical_failure():
    contract = MissionContract(
        goal="blocked test mission",
        user_visible_outcome="a truthful blocker",
        acceptance_criteria=["blocker is reported"],
        max_cycles=5,
    )
    result = ProductEvolutionLoop().run(
        contract,
        mission_id="blocked-mission",
        stages={Stage.BROWSER: lambda: {"status": "BLOCKED", "failure_class": FailureClass.CREDENTIAL_BLOCKER.value, "error": "Access session required"}},
        critic=lambda _contract, _evidence: {"status": "FAIL"},
        repair=lambda _failure: {"status": "PASS", "action": "cannot authenticate without Ray"},
    )
    assert result.status == "PARTIAL"
    assert result.cycles == 2
    assert result.failures[0]["class"] == FailureClass.CREDENTIAL_BLOCKER.value
