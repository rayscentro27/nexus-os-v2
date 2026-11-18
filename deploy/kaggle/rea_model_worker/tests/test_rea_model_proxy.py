"""Offline contracts for rea_model_proxy.py against a scriptable fake llama-server backend."""
import json
import os
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
import pytest

HERE = Path(__file__).resolve().parents[1]
CLIENT_KEY = "test-client-key-0123456789abcdef"
BACKEND_KEY = "test-backend-key-0123456789abcdef"
SCRIPT: list = []          # queue of backend behaviours for /v1/chat/completions
SEEN: list = []
STATE_DIR: list = []


def _port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, status, obj):
        raw = json.dumps(obj).encode() if not isinstance(obj, bytes) else obj
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.headers.get("authorization") != f"Bearer {BACKEND_KEY}":
            return self._send(401, {"error": "auth"})
        self._send(200, {"status": "ok"})

    def do_POST(self):
        if self.headers.get("authorization") != f"Bearer {BACKEND_KEY}":
            return self._send(401, {"error": "auth"})
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        SEEN.append(body)
        step = SCRIPT.pop(0) if SCRIPT else {"content": "ok"}
        if step.get("sleep"):
            time.sleep(step["sleep"])
        if step.get("status"):
            return self._send(step["status"], {"error": {"message": step.get("text", "")}})
        msg = {"role": "assistant", "content": step.get("content")}
        if step.get("tool_calls"):
            msg = {"role": "assistant", "content": None, "tool_calls": step["tool_calls"], "reasoning_content": "hidden"}
        self._send(200, {"choices": [{"index": 0, "message": msg, "finish_reason": "tool_calls" if step.get("tool_calls") else "stop"}],
                         "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}})


@pytest.fixture(scope="module")
def proxy(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("rea")
    (tmp / "client.key").write_text(CLIENT_KEY)
    (tmp / "backend.key").write_text(BACKEND_KEY)
    bport, pport = _port(), _port()
    backend = ThreadingHTTPServer(("127.0.0.1", bport), Fake)
    threading.Thread(target=backend.serve_forever, daemon=True).start()
    env = {**os.environ, "REA_BACKEND_URL": f"http://127.0.0.1:{bport}", "REA_BACKEND_KEY_FILE": str(tmp / "backend.key"),
           "REA_CLIENT_KEY_FILE": str(tmp / "client.key"), "REA_MODEL_NAME": "test-model", "REA_MAX_CONTEXT": "8192",
           "REA_MAX_NEW_TOKENS": "512", "REA_MAX_BODY_BYTES": "200000", "REA_REQUEST_TIMEOUT_SECONDS": "20",
           "REA_SYSTEM_PROMPT_FILE": str(HERE / "REA_MODEL_SYSTEM_PROMPT.md"), "REA_SELF_TEST": "true", "PYTHONPATH": str(HERE),
           "REA_STATE_FILE": str(tmp / "state.json"), "REA_MODEL_REQUEST_FILE": str(tmp / "request.json"),
           "REA_CATALOG_FILE": str(HERE / "model_catalog.json"), "REA_TEST_GPU_TOTALS": "14910,14910"}
    (tmp / "state.json").write_text(json.dumps({"status": "READY", "model_key": "qwen3-30b-a3b", "context": 8192,
                                                "model_id": "Qwen/Qwen3-30B-A3B-GGUF"}))
    STATE_DIR.append(tmp)
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "rea_model_proxy:app", "--host", "127.0.0.1", "--port", str(pport),
                             "--log-level", "warning"], env=env, cwd=str(HERE))
    base = f"http://127.0.0.1:{pport}"
    deadline = time.time() + 60            # slow hosts: import alone can take several seconds
    while time.time() < deadline:
        try:
            if httpx.get(base + "/health", timeout=10).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.25)
    yield base, backend, bport
    proc.terminate()
    backend.shutdown()


AUTH = {"Authorization": f"Bearer {CLIENT_KEY}"}
TOOLS = [{"type": "function", "function": {"name": "read_file", "description": "Read a file",
                                            "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}}]


def chat(base, body, headers=AUTH, **kw):
    return httpx.post(base + "/v1/chat/completions", json=body, headers=headers, timeout=60, **kw)


def test_health_has_no_secrets_and_auth_is_required(proxy):
    base, _, _ = proxy
    h = httpx.get(base + "/health").json()
    assert h["status"] == "ok" and h["model"] == "test-model"
    assert CLIENT_KEY not in json.dumps(h) and BACKEND_KEY not in json.dumps(h)
    assert httpx.get(base + "/v1/models").status_code == 401
    assert httpx.get(base + "/v1/models", headers={"Authorization": "Bearer wrong"}).status_code == 401
    m = httpx.get(base + "/v1/models", headers=AUTH).json()
    assert m["data"][0]["id"] == "test-model" and m["data"][0]["context_length"] == 8192
    assert chat(base, {"messages": [{"role": "user", "content": "hi"}]}, headers={}).status_code == 401


def test_simple_chat_shape_and_rea_prompt_injected(proxy):
    base, _, _ = proxy
    SCRIPT[:] = [{"content": "hello"}]
    r = chat(base, {"model": "x", "messages": [{"role": "system", "content": "harness"}, {"role": "user", "content": "hi"}]}).json()
    assert r["object"] == "chat.completion" and r["choices"][0]["message"] == {"role": "assistant", "content": "hello"}
    assert r["choices"][0]["finish_reason"] == "stop" and r["usage"]["total_tokens"] == 15
    sys_msg = SEEN[-1]["messages"][0]["content"]
    assert sys_msg.startswith("You are the reasoning engine") and sys_msg.endswith("harness")
    assert SEEN[-1]["chat_template_kwargs"] == {"enable_thinking": False}


def test_malformed_and_oversized_requests_fail_clearly(proxy):
    base, _, _ = proxy
    assert httpx.post(base + "/v1/chat/completions", content=b"{not json", headers=AUTH).status_code == 400
    assert chat(base, {"messages": []}).status_code == 400
    assert chat(base, {"messages": [{"content": "no role"}]}).status_code == 400
    big = chat(base, {"messages": [{"role": "user", "content": "x" * 300000}]})
    assert big.status_code == 413 and big.json()["error"]["code"] == "request_too_large"
    ctx = chat(base, {"messages": [{"role": "user", "content": "y" * 40000}]})
    assert ctx.status_code == 413 and ctx.json()["error"]["code"] == "context_length_exceeded"


def test_native_tool_call_passthrough_and_invalid_call_retried_once(proxy):
    base, _, _ = proxy
    good = [{"id": "c1", "type": "function", "function": {"name": "read_file", "arguments": "{\"path\": \"a.py\"}"}}]
    SCRIPT[:] = [{"tool_calls": good}]
    r = chat(base, {"messages": [{"role": "user", "content": "read a.py"}], "tools": TOOLS, "tool_choice": "auto"}).json()
    msg = r["choices"][0]["message"]
    assert r["choices"][0]["finish_reason"] == "tool_calls" and msg["tool_calls"] == good and "reasoning_content" not in msg
    bad = [{"id": "c2", "type": "function", "function": {"name": "delete_everything", "arguments": "{}"}}]
    SCRIPT[:] = [{"tool_calls": bad}, {"tool_calls": good}]
    r = chat(base, {"messages": [{"role": "user", "content": "read"}], "tools": TOOLS}).json()
    assert r["choices"][0]["message"]["tool_calls"] == good
    SCRIPT[:] = [{"tool_calls": bad}, {"tool_calls": bad}]
    r = chat(base, {"messages": [{"role": "user", "content": "read"}], "tools": TOOLS})
    assert r.status_code == 502 and r.json()["error"]["code"] == "tool_call_invalid"


def test_structured_json_fallback_converts_and_retries_once(proxy):
    base, _, _ = proxy
    SCRIPT[:] = [{"content": "sure! here you go"}, {"content": "{\"type\":\"tool_call\",\"tool\":\"read_file\",\"arguments\":{\"path\":\"src/auth.ts\"}}"}]
    r = chat(base, {"messages": [{"role": "user", "content": "inspect auth"}], "tools": TOOLS, "x_tool_mode": "structured_json"}).json()
    call = r["choices"][0]["message"]["tool_calls"][0]
    assert call["function"]["name"] == "read_file" and json.loads(call["function"]["arguments"]) == {"path": "src/auth.ts"}
    assert SEEN[-1]["response_format"] == {"type": "json_object"} and "tools" not in SEEN[-1]
    assert "INVALID RESPONSE" in SEEN[-1]["messages"][-1]["content"]
    SCRIPT[:] = [{"content": "{\"type\":\"final\",\"content\":\"done\"}"}]
    r = chat(base, {"messages": [{"role": "user", "content": "x"}], "tools": TOOLS, "x_tool_mode": "structured_json"}).json()
    assert r["choices"][0]["message"]["content"] == "done"
    SCRIPT[:] = [{"content": "nope"}, {"content": "{\"type\":\"tool_call\",\"tool\":\"rm\",\"arguments\":{}}"}]
    r = chat(base, {"messages": [{"role": "user", "content": "x"}], "tools": TOOLS, "x_tool_mode": "structured_json"})
    assert r.status_code == 502 and r.json()["error"]["code"] == "structured_output_invalid"


def test_streaming_returns_openai_sse(proxy):
    base, _, _ = proxy
    good = [{"id": "c1", "type": "function", "function": {"name": "read_file", "arguments": "{\"path\": \"a.py\"}"}}]
    SCRIPT[:] = [{"tool_calls": good}]
    r = chat(base, {"messages": [{"role": "user", "content": "x"}], "tools": TOOLS, "stream": True})
    events = [json.loads(line[6:]) for line in r.text.splitlines() if line.startswith("data: {")]
    assert r.text.strip().endswith("data: [DONE]")
    assert events[-1]["choices"][0]["finish_reason"] == "tool_calls"
    args = "".join(d["choices"][0]["delta"].get("tool_calls", [{}])[0].get("function", {}).get("arguments", "") for d in events
                   if d["choices"][0]["delta"].get("tool_calls"))
    assert json.loads(args) == {"path": "a.py"}


def test_timeout_oom_and_backend_errors_are_bounded(proxy):
    base, _, _ = proxy
    SCRIPT[:] = [{"sleep": 3, "content": "late"}]
    t = time.monotonic()
    r = chat(base, {"messages": [{"role": "user", "content": "x"}]}, headers={**AUTH, "x-nexus-test-timeout": "1"})
    assert r.status_code == 504 and time.monotonic() - t < 10
    SCRIPT[:] = [{"status": 500, "text": "CUDA error: out of memory"}]
    r = chat(base, {"messages": [{"role": "user", "content": "x"}]})
    assert r.status_code == 503 and r.json()["error"]["code"] == "model_out_of_memory"
    SCRIPT[:] = [{"status": 500, "text": "boom"}]
    assert chat(base, {"messages": [{"role": "user", "content": "x"}]}).status_code == 502
    m = httpx.get(base + "/health").json()["metrics"]
    assert m["oom_count"] >= 1 and m["timeouts"] >= 1 and m["model_errors"] >= 1


def test_backend_down_fails_fast(proxy):
    base, backend, _ = proxy
    backend.shutdown()
    backend.server_close()
    t = time.monotonic()
    r = chat(base, {"messages": [{"role": "user", "content": "x"}]})
    assert r.status_code == 503 and r.json()["error"]["code"] == "model_unavailable" and time.monotonic() - t < 15
    assert httpx.get(base + "/health").json()["status"].startswith("degraded")


def test_model_selection_endpoint_validates_and_queues(proxy):
    base, _, _ = proxy
    tmp = STATE_DIR[0]
    url = base + "/nexus/v1/model"
    assert httpx.post(url, json={"mode": "manual"}).status_code == 401
    assert httpx.post(url, json={"mode": "bogus"}, headers=AUTH).status_code == 400
    assert httpx.post(url, json={"mode": "manual", "model_key": "not-approved"}, headers=AUTH).status_code == 400
    assert httpx.post(url, json={"mode": "auto", "profile": "nope"}, headers=AUTH).status_code == 400
    r = httpx.post(url, json={"mode": "manual", "model_key": "llama-3.3-70b-instruct", "dry_run": True}, headers=AUTH).json()
    assert r["decision"]["status"] == "REJECTED_DOES_NOT_FIT_USING_FALLBACK" and r["decision"]["selected"] == "qwen3-14b"
    r = httpx.post(url, json={"mode": "auto", "profile": "code_analysis", "dry_run": True}, headers=AUTH).json()
    assert r["decision"]["selected"] == "devstral-small-2507"
    assert not (tmp / "request.json").exists()
    r = httpx.post(url, json={"mode": "manual", "model_key": "qwen3-14b"}, headers=AUTH)
    assert r.status_code == 202 and json.loads((tmp / "request.json").read_text())["model_key"] == "qwen3-14b"
    assert httpx.post(url, json={"mode": "manual", "model_key": "qwen3-8b"}, headers=AUTH).status_code == 409
    (tmp / "request.json").unlink()
    st = httpx.get(url, headers=AUTH).json()
    assert st["state"]["model_key"] == "qwen3-30b-a3b" and len(st["catalog"]) == 8


def test_chat_refuses_while_model_switching_or_paused(proxy):
    base, _, _ = proxy
    f = STATE_DIR[0] / "state.json"
    good = f.read_text()
    f.write_text(json.dumps({"status": "PAUSED", "reason": "NO_APPROVED_MODEL_AVAILABLE"}))
    r = chat(base, {"messages": [{"role": "user", "content": "x"}]})
    assert r.status_code == 503 and r.json()["error"]["code"] == "model_paused"
    assert httpx.get(base + "/health").json()["status"] == "model_paused"
    f.write_text(good)
