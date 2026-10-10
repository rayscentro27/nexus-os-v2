from operations.nexus_active_operator_runner import autonomous_trigger_blocked


def test_autonomous_workflow_triggers_are_blocked():
    for trigger in ("launchd", "cron", "autostart"):
        assert autonomous_trigger_blocked(trigger)


def test_interactive_invocation_is_not_misclassified_as_autostart():
    assert not autonomous_trigger_blocked("")
    assert not autonomous_trigger_blocked("interactive")
