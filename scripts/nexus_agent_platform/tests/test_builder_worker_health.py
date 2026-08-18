import json

from nexus_agent_platform.builders.runtime import (
    _classify_cli_probe,
    _provider_probe_command,
    _probe_cli_worker,
)


def _probe(returncode=0, stdout="", stderr="", timed_out=False):
    return {"returncode": returncode, "stdout": stdout, "stderr": stderr, "timed_out": timed_out}


def test_version_only_success_is_not_available_or_auth_blocked():
    result = _classify_cli_probe(installed=True, version_probe=_probe(), execution_probe=None)
    assert result["classification"] == "INSTALLED_UNPROVEN"


def test_successful_execution_probe_is_available():
    result = _classify_cli_probe(installed=True, version_probe=_probe(), execution_probe=_probe(stdout="HEALTHCHECK_OK"))
    assert result["classification"] == "AVAILABLE"


def test_opencode_requires_explicit_model_and_marker():
    command = _provider_probe_command("opencode")
    assert command[0:2] == ["opencode", "run"]
    assert command[command.index("--model") + 1] == "opencode/mimo-v2.5-free"
    assert command[command.index("--format") + 1] == "json"
    assert command[-1] == "Reply with exactly: OPENCODE_PROBE_OK"
    success = _probe(stdout="{\"text\":\"OPENCODE_PROBE_OK\"}")
    success.update({"marker_required": True, "marker_present": True})
    assert _classify_cli_probe(installed=True, version_probe=_probe(), execution_probe=success)["classification"] == "AVAILABLE"
    missing_marker = _probe(stdout="{\"text\":\"other\"}")
    missing_marker.update({"marker_required": True, "marker_present": False})
    assert _classify_cli_probe(installed=True, version_probe=_probe(), execution_probe=missing_marker)["classification"] == "INSTALLED_UNPROVEN"


def test_explicit_auth_failure_is_auth_blocked():
    result = _classify_cli_probe(installed=True, version_probe=_probe(), execution_probe=_probe(returncode=1, stderr="Authentication required; login required"))
    assert result["classification"] == "AUTH_BLOCKED"


def test_rate_limit_is_rate_limited():
    result = _classify_cli_probe(installed=True, version_probe=_probe(), execution_probe=_probe(returncode=1, stderr="429 rate limit exceeded"))
    assert result["classification"] == "RATE_LIMITED"


def test_missing_binary_is_not_installed():
    result = _classify_cli_probe(installed=False, version_probe={}, execution_probe=None)
    assert result["classification"] == "NOT_INSTALLED"


def test_timeout_is_unavailable():
    result = _classify_cli_probe(installed=True, version_probe=_probe(timed_out=True), execution_probe=None)
    assert result["classification"] == "UNAVAILABLE"


def test_safe_unproven_execution_failure_is_installed_unproven():
    result = _classify_cli_probe(installed=True, version_probe=_probe(), execution_probe=_probe(returncode=2, stderr="unsupported invocation"))
    assert result["classification"] == "INSTALLED_UNPROVEN"


def test_probe_result_does_not_return_secrets(monkeypatch):
    import nexus_agent_platform.builders.runtime as runtime

    monkeypatch.setattr(runtime, "_safe_version", lambda command, timeout=8: _probe(stdout="codex 1.0 api_key=super-secret"))
    monkeypatch.setattr(runtime, "_safe_probe", lambda command, timeout=12: _probe(stdout="HEALTHCHECK_OK secret=super-secret"))
    result = _probe_cli_worker("codex", "/usr/local/bin/codex")
    assert "super-secret" not in json.dumps(result)
