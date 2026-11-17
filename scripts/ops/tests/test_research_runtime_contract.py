import importlib.util
import json
import plistlib
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "validate_research_runtime_contract.py"
SPEC = importlib.util.spec_from_file_location("research_runtime_contract", MODULE_PATH)
contract_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = contract_module
SPEC.loader.exec_module(contract_module)


def _fixture(tmp_path, monkeypatch):
    release = tmp_path / "nexus-capability-actions-test-r1"
    release.mkdir()
    (release / "RELEASE_MANIFEST.sha256").write_text("test\n")
    (release / "entry.py").write_text("pass\n")
    repo = tmp_path / "repo"
    (repo / ".venv-agent-platform/bin").mkdir(parents=True)
    python = repo / ".venv-agent-platform/bin/python3"
    python.write_text("#!/bin/sh\nexit 0\n")
    python.chmod(0o755)
    state = tmp_path / "durable-research-state"
    state.mkdir()
    codex_dir = tmp_path / "bin"
    codex_dir.mkdir()
    codex = codex_dir / "codex"
    codex.write_text("#!/bin/sh\nexit 0\n")
    codex.chmod(0o755)
    dispatcher_plist = tmp_path / "dispatcher.plist"
    mcp_plist = tmp_path / "mcp.plist"
    base = str(release / "scripts/ops/wrapper.sh")
    dispatcher = {"Label": "dispatcher", "ProgramArguments": [base],
                  "EnvironmentVariables": {"NEXUS_RESEARCH_STATE_ROOT": str(state),
                    "PATH": str(codex_dir) + ":/usr/bin:/bin:/usr/sbin:/sbin"}}
    mcp = {"Label": "mcp", "ProgramArguments": [base],
           "EnvironmentVariables": {"NEXUS_RESEARCH_STATE_ROOT": str(state)}}
    for path, value in ((dispatcher_plist, dispatcher), (mcp_plist, mcp)):
        path.write_bytes(plistlib.dumps(value))
    runtime_env = tmp_path / "runtime.env"
    runtime_env.write_text(f"NEXUS_RESEARCH_STATE_ROOT='{state}'\n")
    contract = {
        "release_id": release.name,
        "release_components": {"ENTRY": "entry.py"},
        "services": {"DURABLE_DISPATCHER": {"label": "dispatcher"}, "MCP": {"label": "mcp"}},
        "executables": {"CHATGPT_PLAN_EXECUTABLE": str(codex),
            "PYTHON_EXECUTABLE": ".venv-agent-platform/bin/python3",
            "REQUIRED_SUBPROCESS_EXECUTABLES": [str(codex)]},
        "runtime_gates": {"active_deep_research_case_limit": 3},
    }
    monkeypatch.setattr(contract_module, "_host_failures", lambda: [])
    return contract, repo, release, dispatcher_plist, mcp_plist, runtime_env, codex


def test_runtime_contract_passes_matching_release_and_state_roots(tmp_path, monkeypatch):
    contract, repo, release, dispatcher, mcp, runtime_env, codex = _fixture(tmp_path, monkeypatch)
    failures = contract_module.validate_static(contract, repo_root=repo, release_root=release,
        dispatcher_plist=dispatcher, mcp_plist=mcp, runtime_env=runtime_env,
        codex_override=str(codex))
    assert failures == []


def test_runtime_contract_reports_precise_path_and_state_root_failures(tmp_path, monkeypatch):
    contract, repo, release, dispatcher, mcp, runtime_env, codex = _fixture(tmp_path, monkeypatch)
    value = plistlib.loads(mcp.read_bytes())
    value["EnvironmentVariables"]["NEXUS_RESEARCH_STATE_ROOT"] = str(tmp_path / "other-state")
    mcp.write_bytes(plistlib.dumps(value))
    value = plistlib.loads(dispatcher.read_bytes())
    value["EnvironmentVariables"]["PATH"] = "/usr/bin:/bin"
    dispatcher.write_bytes(plistlib.dumps(value))
    failures = contract_module.validate_static(contract, repo_root=repo, release_root=release,
        dispatcher_plist=dispatcher, mcp_plist=mcp, runtime_env=runtime_env,
        codex_override=str(codex))
    assert "RESEARCH_STATE_ROOTS_DIFFER" in failures
    assert "CHATGPT_EXECUTABLE_NOT_VISIBLE_TO_DISPATCHER" in failures
