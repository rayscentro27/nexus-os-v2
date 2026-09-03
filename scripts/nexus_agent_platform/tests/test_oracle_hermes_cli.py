from nexus_agent_platform.bridge.oracle_hermes_cli import _remote_command, run_oracle_hermes


def test_remote_command_is_fixed_and_session_is_stdin_bound():
    command = _remote_command()
    assert "nexus-hermes-0206" in command
    assert "HERMES_PROFILE=nova_nexus" in command
    assert "-t nexus_mcp_remote" in command
    assert "$prompt" in command
    assert "$session" in command


def test_invalid_session_fails_closed():
    try:
        run_oracle_hermes("hello", "bad session", timeout_seconds=1)
    except Exception as exc:
        assert str(exc) == "invalid_session_id"
    else:
        raise AssertionError("invalid session was accepted")
