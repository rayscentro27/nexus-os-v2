"""Tests for the isolated upstream Hermes compatibility lab."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_scripts_dir = Path(__file__).resolve().parents[1]
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))


def test_nexus_status_synthesis_uses_deterministic_facts(monkeypatch):
    from nexus_agent_platform.hermes_lab.upstream_compatibility import _synthesise_nexus_status

    system = {"status": "success"}
    processes = {"total": 19, "configuration_counts": {"enabled": 17, "disabled": 2}}
    runtime = {"summary": {"event_count": 4, "current_state": "idle", "last_terminal_status": "completed"}, "coverage": {"coverage_status": "complete"}}

    answer = _synthesise_nexus_status(system, processes, runtime)
    assert "19 processes" in answer
    assert "17 enabled" in answer
    assert "runtime telemetry is available" in answer.lower()


def test_lab_prepares_isolated_plugin_and_tool(tmp_path, monkeypatch):
    from nexus_agent_platform.hermes_lab import upstream_compatibility as lab_mod

    monkeypatch.setattr(lab_mod.tempfile, "mkdtemp", lambda **kwargs: str(tmp_path / "sandbox"))
    lab = lab_mod.UpstreamHermesCompatibilityLab(upstream_repo=Path.home() / ".hermes" / "hermes-agent")
    plugin_dir = lab.hermes_home / "plugins" / "nexus-lab"

    assert plugin_dir.exists()
    assert (plugin_dir / "plugin.yaml").exists()
    assert (plugin_dir / "__init__.py").exists()

    config = json.loads(json.dumps(lab_mod._load_yaml(lab.hermes_home / "config.yaml")))
    enabled = config.get("plugins", {}).get("enabled", [])
    assert "nexus-lab" in enabled


def test_lab_run_collects_expected_probes_without_live_upstream_calls(tmp_path, monkeypatch):
    from nexus_agent_platform.hermes_lab import upstream_compatibility as lab_mod

    monkeypatch.setattr(lab_mod.tempfile, "mkdtemp", lambda **kwargs: str(tmp_path / "sandbox"))

    def fake_run(args, *, cwd, env, timeout=45):
        command = " ".join(args)
        if "--version" in args:
            return {"command": args, "command_summary": command, "returncode": 0, "stdout": "Hermes Agent v1.0\n", "stderr": "", "duration_ms": 5, "timed_out": False}
        if args[-1] == "status" and "gateway" not in args:
            return {"command": args, "command_summary": command, "returncode": 0, "stdout": "status ok\n", "stderr": "", "duration_ms": 5, "timed_out": False}
        if "gateway" in args and "status" in args:
            return {"command": args, "command_summary": command, "returncode": 0, "stdout": "gateway ok\n", "stderr": "", "duration_ms": 5, "timed_out": False}
        if "resolve_runtime_provider" in command:
            return {"command": args, "command_summary": command, "returncode": 1, "stdout": "No Codex credentials stored. Run `hermes auth` to authenticate.\n", "stderr": "", "duration_ms": 5, "timed_out": False}
        if "localhost:11434" in command or "ollama" in command:
            payload = {"provider": "local-ollama", "model": "gemma4:31b-cloud", "content": "OK"}
            return {"command": args, "command_summary": command, "returncode": 0, "stdout": json.dumps(payload), "stderr": "", "duration_ms": 5, "timed_out": False}
        if "memory" in args and "status" in args:
            return {"command": args, "command_summary": command, "returncode": 0, "stdout": "memory ok\n", "stderr": "", "duration_ms": 5, "timed_out": False}
        if "skills" in args and "list" in args:
            return {"command": args, "command_summary": command, "returncode": 0, "stdout": "nexus-lab-skill\n", "stderr": "", "duration_ms": 5, "timed_out": False}
        if "cron" in args and "status" in args:
            return {"command": args, "command_summary": command, "returncode": 0, "stdout": "cron ok\n", "stderr": "", "duration_ms": 5, "timed_out": False}
        if "discover_plugins" in command or "registry.dispatch" in command:
            payload = {
                "answer": "Nexus is up.",
                "capability_lookup": {"status": "success", "capability": {"capability_id": "get_system_health"}},
                "tool_names": ["nexus_current_status"],
            }
            return {"command": args, "command_summary": command, "returncode": 0, "stdout": json.dumps(payload), "stderr": "", "duration_ms": 5, "timed_out": False}
        if "delegate_tool" in command:
            return {"command": args, "command_summary": command, "returncode": 0, "stdout": "callback\n", "stderr": "", "duration_ms": 5, "timed_out": False}
        return {"command": args, "command_summary": command, "returncode": 0, "stdout": "ok\n", "stderr": "", "duration_ms": 5, "timed_out": False}

    monkeypatch.setattr(lab_mod, "_run_upstream_python_timeout", fake_run)
    monkeypatch.setattr(
        lab_mod,
        "_build_nexus_status_payload",
        lambda: {
            "source_type": "nexus_current_status_tool",
            "capability_lookup": {"status": "success", "capability": {"capability_id": "get_system_health"}},
            "answer": "Nexus is up.",
            "answer_chars": 12,
            "answer_tokens_approx": 3,
        },
    )
    report = lab_mod.run_upstream_compatibility_lab()

    assert report.overall_status == "pass"
    assert report.probes["install_start"].status == "pass"
    assert report.probes["plugin_tool_integration"].status == "pass"
    assert report.probes["nexus_tool_dispatch"].status == "pass"
    assert report.probes["nexus_capability_lookup"].status == "pass"
    assert report.nexus_status["answer"] == "Nexus is up."


def test_report_rendering_includes_classification_and_first_proof(tmp_path, monkeypatch):
    from nexus_agent_platform.hermes_lab import upstream_compatibility as lab_mod

    monkeypatch.setattr(lab_mod.tempfile, "mkdtemp", lambda **kwargs: str(tmp_path / "sandbox"))
    monkeypatch.setattr(lab_mod, "_build_nexus_status_payload", lambda: {"answer": "Nexus is up.", "capability_lookup": {"status": "success", "capability": {"capability_id": "get_system_health"}}})
    monkeypatch.setattr(lab_mod, "_run_upstream_python_timeout", lambda *args, **kwargs: {"command": [], "command_summary": "", "returncode": 0, "stdout": "ok\n", "stderr": "", "duration_ms": 1, "timed_out": False})

    report = lab_mod.run_upstream_compatibility_lab()
    md = lab_mod.build_upstream_compatibility_report(report)

    assert "# Hermes Upstream Compatibility Lab" in md
    assert "First Proof: Nexus Status" in md
    assert "Nexus is up." in md
    assert "| Capability | Classification |" in md
    assert "nexus_tool_dispatch" in md


def test_deterministic_capability_invocation_is_read_only():
    from nexus_agent_platform.hermes_lab.upstream_compatibility import _build_nexus_status_payload

    payload = _build_nexus_status_payload()
    assert payload["source_type"] == "nexus_current_status_tool"
    assert payload["answer"]
    assert payload["capability_lookup"]["status"] == "success"
