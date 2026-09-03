from tool_loop_recovery import progress_trace, recovery_plan


def test_repeated_same_failure_is_not_progress():
    rows = [
        {"name": "alpha", "payload": {"status": "ERROR", "error": "unavailable"}},
        {"name": "alpha", "payload": {"status": "ERROR", "error": "unavailable"}},
    ]
    trace = progress_trace(rows)
    assert trace[0]["progress"] in {"TRANSIENT_FAILURE", "STRUCTURALLY_BLOCKED"}
    assert trace[1]["progress"] == "SAME_FAILURE"


def test_successful_identical_result_is_no_new_information():
    rows = [{"name": "research", "payload": {"status": "SUCCESS", "value": 1}}] * 2
    assert progress_trace(rows)[1]["progress"] == "NO_NEW_INFORMATION"


def test_recovery_suppresses_only_current_failed_tool_and_preserves_evidence():
    plan = recovery_plan(
        "Should we change the offer?",
        "I stopped retrying tool_call because it hit the tool-call guardrail (same_tool_failure_halt).",
        [{"name": "alpha", "payload": {"status": "ERROR", "error": "unavailable"}}],
    )
    assert plan["action"] == "SYNTHESIZE_EXISTING_EVIDENCE"
    assert plan["temporarily_suppressed_tools"] == ["alpha"]
    assert plan["preserve_evidence"] is True
    assert plan["max_recovery_attempts"] == 1
    assert "MUTATION" in plan["mutation_policy"]
