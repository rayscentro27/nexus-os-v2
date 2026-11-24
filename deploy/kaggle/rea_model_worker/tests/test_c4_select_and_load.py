"""Offline exercise of Cell 4 select_and_load with stubbed GPU/download/backend (catches cell-level bugs before GPU runs)."""
import json
import types
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]


def load_cell(tmp_path):
    ns = {"__name__": "__main__"}
    exec("import json, os, sys, time, shutil, subprocess\nfrom pathlib import Path", ns)
    ns.update({"WORK": tmp_path, "REPORT": {}, "save_report": lambda: None, "GPUS": [{}, {}], "SECRET_HF_TOKEN": "HF_TOKEN",
               "get_secret": lambda n: (None, None), "LLAMA_SERVER": Path("/bin/false"), "BACKEND_PORT": 0,
               "kv": lambda k, v: None, "BLOCKER": "SKIP_MAIN", "SELECTOR_SOURCE": (HERE / "model_selector.py").read_text(),
               "CATALOG_JSON": (HERE / "model_catalog.json").read_text()})
    exec((HERE / "cells" / "c4_model.py").read_text(), ns)
    ns["gpu_free_mb"] = lambda: [14906, 14918]
    ns["gpu_used_mb"] = lambda: [13053, 12497]
    ns["ensure_model_file"] = lambda m: tmp_path / m["file"]
    return ns


def test_manual_load_ready(tmp_path):
    ns = load_cell(tmp_path)
    ns["start_backend"] = lambda path, ctx: types.SimpleNamespace(poll=lambda: 0, pid=None)
    out = ns["select_and_load"]("manual", "qwen3-30b-a3b", "qwen3-14b", "general_rea", {"tool_count": 30}, None)
    assert out["status"] == "READY" and out["model_key"] == "qwen3-30b-a3b" and out["context"] == 32768
    assert json.loads((tmp_path / "model_state.json").read_text())["status"] == "READY"


def test_oom_retries_half_context_then_fallback_then_paused(tmp_path):
    ns = load_cell(tmp_path)
    calls = []

    def oom_then_ok(path, ctx):
        calls.append((path.name, ctx))
        if len(calls) == 1:
            raise RuntimeError("LLAMA_SERVER_EXITED: cudaMalloc failed: out of memory")
        return types.SimpleNamespace(poll=lambda: 0, pid=None)
    ns["start_backend"] = oom_then_ok
    out = ns["select_and_load"]("manual", "qwen3-30b-a3b", "qwen3-14b", "general_rea", {}, None)
    assert out["status"] == "READY" and out["context"] == 16384 and calls[1][1] == 16384

    ns["start_backend"] = lambda path, ctx: (_ for _ in ()).throw(RuntimeError("LLAMA_SERVER_LOAD_TIMEOUT"))
    out = ns["select_and_load"]("manual", "qwen3-30b-a3b", "qwen3-14b", "general_rea", {}, None)
    assert out["status"] == "PAUSED" and [f["model"] for f in out["failures"]] == ["qwen3-30b-a3b", "qwen3-14b"]

    seq = iter([RuntimeError("LLAMA_SERVER_LOAD_TIMEOUT")])
    def first_fails(path, ctx):
        err = next(seq, None)
        if err:
            raise err
        return types.SimpleNamespace(poll=lambda: 0, pid=None)
    ns["start_backend"] = first_fails
    out = ns["select_and_load"]("manual", "qwen3-30b-a3b", "qwen3-14b", "general_rea", {}, None)
    assert out["status"] == "READY" and out["model_key"] == "qwen3-14b" and out["fallback_used"] is True
