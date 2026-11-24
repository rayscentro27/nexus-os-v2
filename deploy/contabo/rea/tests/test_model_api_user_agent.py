"""Regression: the model-step preflight (_model_api) must send a named User-Agent.

The provider sits behind Cloudflare Bot Fight Mode, which rejects urllib's default
"Python-urllib/*" UA with HTTP 403 error 1010 (observed live 2026-11-15, causing a
false MODEL_ENDPOINT_AUTH_FAILED). This locks in a non-default UA so that cannot recur.
"""
import importlib.util
import json
import os
import urllib.request
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[1] / "config" / "harness" / "rea_harness.py"
os.environ.setdefault("REA_HARNESS_ROOT", "/tmp/rea-test-root")
spec = importlib.util.spec_from_file_location("rea_harness", HARNESS)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

PROVIDER = {"base_url": "https://kaggle-model.goclearonline.cc/v1"}


class _Resp:
    status = 200
    def read(self): return b"{}"
    def __enter__(self): return self
    def __exit__(self, *a): return False


def _capture(monkeypatch):
    seen = {}
    def fake_urlopen(req, timeout=None):
        seen["ua"] = req.get_header("User-agent")
        seen["url"] = req.full_url
        seen["auth"] = req.get_header("Authorization")
        return _Resp()
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return seen


def test_model_api_sends_named_user_agent(monkeypatch):
    seen = _capture(monkeypatch)
    code, _ = mod._model_api(PROVIDER, "KEY123", "GET", "/nexus/v1/model")
    assert code == 200
    assert seen["ua"], "User-Agent header must be set"
    assert "python-urllib" not in seen["ua"].lower(), "must not use urllib default UA (Cloudflare 1010)"
    assert seen["auth"] == "Bearer KEY123"
    assert seen["url"] == "https://kaggle-model.goclearonline.cc/nexus/v1/model"


def test_model_api_post_sets_ua_and_body(monkeypatch):
    seen = _capture(monkeypatch)
    code, _ = mod._model_api(PROVIDER, "K", "POST", "/nexus/v1/model", {"mode": "manual"})
    assert code == 200 and seen["ua"] and "python-urllib" not in seen["ua"].lower()


def test_successful_tool_calls_ignores_errors():
    hist=[{"status":"completed"},{"status":"error","error":"rejected"},{"status":"completed","error":None}]
    assert mod._successful_tool_calls(hist)==2
    assert mod._successful_tool_calls([{"status":"error","error":"The user rejected permission"}])==0


def test_evidence_gate_blocks_zero_successful_calls():
    full = {k: "x" for k in mod.OUTPUT_CONTRACT}
    final, gate = mod.model_result_status(0, full, [], False, total_tool_calls=1)
    assert final == "BLOCKED" and gate["pass"] is False
    assert gate["reason"] == "INSUFFICIENT_TOOL_EVIDENCE"
    assert gate["successful_tool_calls"] == 0 and gate["total_tool_calls"] == 1


def test_evidence_gate_blocks_one_successful_call():
    final, gate = mod.model_result_status(1, {"OBJECTIVE": "x"}, [], False)
    assert final == "BLOCKED" and gate["pass"] is False


def test_evidence_gate_allows_grounded_completion():
    full = {k: "x" for k in mod.OUTPUT_CONTRACT}
    final, gate = mod.model_result_status(2, full, [], False)
    assert final == "COMPLETED" and gate["pass"] is True and gate["successful_tool_calls"] == 2


def test_grounded_but_incomplete_contract_is_limited_not_blocked():
    final, gate = mod.model_result_status(3, {"OBJECTIVE": "x"}, ["EVIDENCE"], False)
    assert final == "COMPLETED_WITH_LIMITATIONS" and gate["pass"] is True


def test_grounded_timeout_is_limited():
    full = {k: "x" for k in mod.OUTPUT_CONTRACT}
    final, _ = mod.model_result_status(5, full, [], True)
    assert final == "COMPLETED_WITH_LIMITATIONS"


def test_target_cwd_resolves_repo_dir(tmp_path, monkeypatch):
    root = tmp_path / "rea"
    (root / "repos" / "fixture").mkdir(parents=True)
    monkeypatch.setattr(mod, "ROOT", root)
    fb = root / "workspace" / "sid"
    # existing dir under repos -> used
    assert mod._target_cwd("/does/not/matter", fb) == fb  # outside allowed root -> fallback
    got = mod._target_cwd(f"{root}/repos/fixture (desc, MIT)", fb)
    assert got == (root / "repos" / "fixture").resolve()
    # url target -> fallback
    assert mod._target_cwd("http://127.0.0.1:18798/", fb) == fb
    # path traversal / secrets dir -> fallback
    (root / "config" / "secrets").mkdir(parents=True)
    assert mod._target_cwd(f"{root}/config/secrets", fb) == fb


def test_min_tool_calls_profile_aware():
    assert mod.min_tool_calls("rea_web") == 1
    assert mod.min_tool_calls("rea_repo") == 2
    assert mod.min_tool_calls(None) == 2


def test_browser_single_capture_passes_gate():
    full = {k: "x" for k in mod.OUTPUT_CONTRACT}
    final, gate = mod.model_result_status(1, full, [], False, total_tool_calls=1,
                                          required=mod.min_tool_calls("rea_web"))
    assert final == "COMPLETED" and gate["pass"] is True and gate["required"] == 1


def test_rea_web_profile_disables_file_tools(monkeypatch):
    monkeypatch.setattr(mod, "HARNESS", HARNESS.parent)
    tpl = {"agent": {"rea": {}}}
    mod.apply_tool_profile(tpl, "rea_web")
    tools = tpl["agent"]["rea"]["tools"]
    assert tools.get("read") is False and tools.get("glob") is False and tools.get("grep") is False
    assert tools.get("list") is False
    assert tools.get("rea_capture_browser_scenario") is True
    assert tpl["agent"]["rea"]["permission"]["bash"] == "allow"


def test_rea_repo_profile_keeps_file_tools(monkeypatch):
    monkeypatch.setattr(mod, "HARNESS", HARNESS.parent)
    tpl = {"agent": {"rea": {}}}
    mod.apply_tool_profile(tpl, "rea_repo")
    tools = tpl["agent"]["rea"]["tools"]
    assert tools.get("read") is True and tools.get("glob") is True
