from nexus_agent_platform.proof_recovery import apply_recovery, recover


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
