from pathlib import Path
from types import SimpleNamespace

import nexus_agent_platform.bridge.oracle_hermes_cli as oracle
from nexus_agent_platform.bridge.oracle_hermes_cli import _executive_prompt, _remote_command, run_oracle_hermes


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


def test_guardrail_halt_switches_once_to_tool_disabled_synthesis(tmp_path, monkeypatch):
    key = tmp_path / "key"
    key.write_text("test")
    monkeypatch.setattr(oracle, "ORACLE_KEY", str(key))
    calls = []
    responses = [
        "I stopped retrying tool_call because it hit the tool-call guardrail (same_tool_failure_halt).",
        "Recommendation: preserve the parent question and use the evidence already returned.",
    ]

    def fake_run(command, **kwargs):
        calls.append(command[-1])
        return SimpleNamespace(returncode=0, stdout=responses.pop(0), stderr="")

    monkeypatch.setattr(oracle.subprocess, "run", fake_run)
    result = run_oracle_hermes("What should we do next?", "recovery-test", timeout_seconds=10)
    assert result.recovery == "SYNTHESIS_AFTER_TOOL_HALT"
    assert result.response.startswith("Recommendation:")
    assert len(calls) == 2
    assert "-t nexus_mcp_remote" in calls[0]
    assert "-t skills" in calls[1]


def test_priority_prompt_requires_company_focus_not_status_dump():
    prompt = _executive_prompt("What should Nexus focus on today and why?")
    assert "PRIORITY_REQUEST" in prompt
    assert "choose exactly one primary company focus" in prompt
    assert "Do not substitute a list of telemetry" in prompt


def test_pricing_prompt_suppresses_irrelevant_telemetry_and_assigns_internal_work():
    prompt = _executive_prompt("Should our $97 readiness assessment become free?")
    assert "unvalidated hypothesis" in prompt
    assert "degraded telemetry" in prompt
    assert "do not ask" in prompt


def test_priority_judgment_correction_switches_to_bounded_no_tool_synthesis(tmp_path, monkeypatch):
    key = tmp_path / "key"
    key.write_text("test")
    monkeypatch.setattr(oracle, "ORACLE_KEY", str(key))
    calls = []
    responses = [
        "Nexus should focus on system health. Telemetry is degraded. Ray should approve the review.",
        "Nexus should focus on the highest-value open company objective. Why now: it advances the parent outcome. Nexus will research and prepare the next internal work; Ray has no action unless an approval boundary appears.",
    ]

    def fake_run(command, **kwargs):
        calls.append(command[-1])
        return SimpleNamespace(returncode=0, stdout=responses.pop(0), stderr="")

    monkeypatch.setattr(oracle.subprocess, "run", fake_run)
    result = run_oracle_hermes("What should Nexus focus on today and why?", "priority-correction", timeout_seconds=10)
    assert result.recovery == "JUDGMENT_CORRECTION"
    assert "highest-value open company objective" in result.response
    assert len(calls) == 2
    assert "-t skills" in calls[1]
