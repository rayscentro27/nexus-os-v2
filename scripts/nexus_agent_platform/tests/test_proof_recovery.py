from nexus_agent_platform.proof_recovery import apply_recovery, recover, run_architecture_alternative_canary


def test_recovery_allows_two_attempts_then_requires_alternative():
    objective = {"executor": "voice", "failure_stage": "S4_EXECUTOR_STARTED", "failure_reason": "no heartbeat"}
    first = recover(objective)
    assert first["status"] == "RECOVERING"
    second = recover({**objective, "repair_cycles_used": 1, "failure_signature": first["failure_signature"]})
    assert second["status"] == "RECOVERING"
    third = recover({**objective, "repair_cycles_used": 2, "failure_signature": first["failure_signature"]})
    assert third["status"] == "ARCHITECTURE_ALTERNATIVE"
    assert len(third["alternatives"]) == 3


def test_recovery_does_not_claim_success_without_new_proof():
    result = apply_recovery({"executor": "tests", "failure_stage": "S5_ARTIFACT_PRODUCED", "repair_count": 0})
    assert result["status"] == "RECOVERING"
    assert result["proof_required"] is True


def test_architecture_alternative_canary_really_executes_and_verifies(tmp_path):
    receipt = run_architecture_alternative_canary(receipt_path=tmp_path / "alternative.json")
    assert receipt["status"] == "PASS"
    assert receipt["decision"] == "ARCHITECTURE_ALTERNATIVE"
    assert receipt["selected_executor"] == "alternate_fixture"
    assert receipt["independent_verification"]["status"] == "PASS"
    assert (tmp_path / "alternative.json").exists()
