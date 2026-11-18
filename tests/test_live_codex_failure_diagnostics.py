"""Focused contract for diagnostics emitted by the active R10 Codex adapter."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ACTIVE_R10 = Path.home() / ".nexus/releases/nexus-research-runtime-r10-codex-native-search-20261104-r14"
sys.path.insert(0, str(ACTIVE_R10))

from nexus_research_r10.codex_adapter import CodexCliAdapter, CodexExecutionError  # noqa: E402
from nexus_research_r10.model import ModelRequest  # noqa: E402


def _request(timeout=15):
    return ModelRequest("RESEARCH_INVESTIGATOR", "Return a small structured diagnostic result.", [],
                        "live-codex-diagnostic-contract", {"timeout_seconds": timeout, "max_turns": 1},
                        {"type": "object"})


def test_live_adapter_retains_redacted_exit_diagnostics(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_RESEARCH_STATE_ROOT", str(tmp_path / "state"))
    fixture = tmp_path / "codex-exit-one"
    fixture.write_text("#!/bin/sh\nprintf 'partial stdout event\\n'\nprintf 'provider auth failed Authorization: Bearer secret-value-123\\n' >&2\nexit 1\n")
    fixture.chmod(0o755)
    with pytest.raises(CodexExecutionError) as caught:
        CodexCliAdapter(executable=str(fixture), model="fixture-model").run(_request())
    diagnostic = caught.value.safe_diagnostic
    assert diagnostic["exit_code"] == 1
    assert diagnostic["termination_cause"] == "PROCESS_EXIT"
    assert diagnostic["stderr_summary"]
    assert "secret-value-123" not in json.dumps(diagnostic)
    assert "partial stdout event" in diagnostic["stdout_tail"]
    assert diagnostic["provider"] == "openai-codex-cli"
    assert diagnostic["model"] == "fixture-model"


def test_live_adapter_still_accepts_structured_codex_result(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_RESEARCH_STATE_ROOT", str(tmp_path / "state"))
    fixture = tmp_path / "codex-success"
    event = {"type": "item.completed", "item": {"type": "agent_message", "text": json.dumps({"ok": True})}}
    fixture.write_text("#!/bin/sh\nprintf '%s\\n' '" + json.dumps(event).replace("'", "'\\''") + "'\n")
    fixture.chmod(0o755)
    result = CodexCliAdapter(executable=str(fixture), model="fixture-model").run(_request())
    assert result.structured == {"ok": True}
