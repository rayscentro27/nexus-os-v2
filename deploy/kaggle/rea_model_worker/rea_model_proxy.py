"""Nexus REA model worker proxy (KAGGLE_HUGGING_FACE_REA_MODEL_WORKER_R1).

OpenAI-compatible front for a local llama.cpp `llama-server` (MODEL COMPUTE ONLY: no job state, no
orchestration, no MCP). Adds: bearer auth, /health without secrets, metrics, request size/time bounds,
OOM classification, SSE for streaming clients (OpenCode), native tool-call validation and a strict JSON
tool protocol fallback (TOOL_MODE=structured_json) with exactly one correction retry.

All configuration is environment-driven; secrets are read from files written with mode 0600 and are
never logged or echoed.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

BACKEND_URL = os.environ.get("REA_BACKEND_URL", "http://127.0.0.1:8081")
BACKEND_KEY = Path(os.environ["REA_BACKEND_KEY_FILE"]).read_text().strip()
CLIENT_KEY = Path(os.environ["REA_CLIENT_KEY_FILE"]).read_text().strip()
MODEL_NAME = os.environ.get("REA_MODEL_NAME", "nexus-rea-model")
TOOL_MODE = os.environ.get("REA_TOOL_MODE", "native")              # native | structured_json
MAX_CONTEXT = int(os.environ.get("REA_MAX_CONTEXT", "32768"))
MAX_NEW_TOKENS = int(os.environ.get("REA_MAX_NEW_TOKENS", "2048"))
DEFAULT_TEMPERATURE = float(os.environ.get("REA_TEMPERATURE", "0.2"))
MAX_BODY_BYTES = int(os.environ.get("REA_MAX_BODY_BYTES", "3000000"))
MAX_MESSAGES = int(os.environ.get("REA_MAX_MESSAGES", "400"))
REQUEST_TIMEOUT = float(os.environ.get("REA_REQUEST_TIMEOUT_SECONDS", "300"))
THINKING = os.environ.get("REA_THINKING", "false").lower() == "true"
REA_PROMPT = Path(os.environ["REA_SYSTEM_PROMPT_FILE"]).read_text() if os.environ.get("REA_SYSTEM_PROMPT_FILE") else ""
SELF_TEST = os.environ.get("REA_SELF_TEST", "false").lower() == "true"
STATE_FILE = Path(os.environ["REA_STATE_FILE"]) if os.environ.get("REA_STATE_FILE") else None
REQUEST_FILE = Path(os.environ["REA_MODEL_REQUEST_FILE"]) if os.environ.get("REA_MODEL_REQUEST_FILE") else None
CATALOG = json.loads(Path(os.environ["REA_CATALOG_FILE"]).read_text()) if os.environ.get("REA_CATALOG_FILE") else None


def _state() -> dict:
    """Model state written by the notebook (model selection/switching). No state file = a single static model."""
    if not STATE_FILE:
        return {"status": "READY", "context": MAX_CONTEXT}
    try:
        return json.loads(STATE_FILE.read_text())
    except (OSError, ValueError):
        return {"status": "STARTING"}


def _context() -> int:
    return int(_state().get("context") or MAX_CONTEXT)

METRICS = {"request_count": 0, "ok_count": 0, "total_seconds": 0.0, "last_response_seconds": None, "last_request_at": None,
           "oom_count": 0, "model_errors": 0, "timeouts": 0, "rejected_auth": 0, "rejected_size": 0, "rejected_malformed": 0,
           "tool_call_retries": 0, "structured_retries": 0, "prompt_tokens": 0, "completion_tokens": 0}

app = FastAPI(title="nexus-rea-model-worker", docs_url=None, redoc_url=None, openapi_url=None)


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def _err(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"type": code, "code": code, "message": message}})


@app.exception_handler(ApiError)
async def _api_error(_: Request, exc: ApiError):
    return _err(exc.status, exc.code, exc.message)


def _authorized(request: Request) -> bool:
    header = request.headers.get("authorization", "")
    token = header[7:].strip() if header.lower().startswith("bearer ") else ""
    # constant-time compare
    return bool(token) and len(token) == len(CLIENT_KEY) and sum(a != b for a, b in zip(token, CLIENT_KEY)) == 0


def _gpu() -> list[dict]:
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=index,name,memory.used,memory.total", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return []
    rows = []
    for line in out.strip().splitlines():
        idx, name, used, total = [x.strip() for x in line.split(",")]
        rows.append({"index": int(idx), "name": name, "memory_used_mb": int(used), "memory_total_mb": int(total)})
    return rows


async def _backend(path: str, payload: dict | None = None, *, timeout: float = REQUEST_TIMEOUT) -> dict:
    headers = {"Authorization": f"Bearer {BACKEND_KEY}"}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=10)) as client:
            resp = await (client.post(BACKEND_URL + path, json=payload, headers=headers) if payload is not None
                          else client.get(BACKEND_URL + path, headers=headers))
    except httpx.TimeoutException as exc:
        METRICS["timeouts"] += 1
        raise ApiError(504, "model_timeout", f"model did not answer within {int(timeout)}s") from exc
    except httpx.HTTPError as exc:
        METRICS["model_errors"] += 1
        raise ApiError(503, "model_unavailable", "model backend unreachable") from exc
    text = resp.text
    if resp.status_code >= 400:
        low = text.lower()
        if "out of memory" in low or "cudamalloc" in low or "failed to allocate" in low:
            METRICS["oom_count"] += 1
            raise ApiError(503, "model_out_of_memory", "GPU memory exhausted for this request; reduce context or max_tokens")
        if "context" in low and ("exceed" in low or "too long" in low or "n_ctx" in low):
            raise ApiError(413, "context_length_exceeded", f"request exceeds model context ({MAX_CONTEXT} tokens)")
        METRICS["model_errors"] += 1
        raise ApiError(502, "model_error", f"backend HTTP {resp.status_code}")
    try:
        return resp.json()
    except ValueError as exc:
        METRICS["model_errors"] += 1
        raise ApiError(502, "model_error", "backend returned invalid JSON") from exc


def _estimate_tokens(obj: Any) -> int:
    return len(json.dumps(obj, ensure_ascii=False)) // 4


def _with_rea_prompt(messages: list[dict]) -> list[dict]:
    if not REA_PROMPT:
        return messages
    msgs = [dict(m) for m in messages]
    if msgs and msgs[0].get("role") == "system":
        content = msgs[0].get("content")
        content = content if isinstance(content, str) else json.dumps(content)
        msgs[0]["content"] = REA_PROMPT.strip() + "\n\n" + content
    else:
        msgs.insert(0, {"role": "system", "content": REA_PROMPT.strip()})
    return msgs


def _tool_names(tools: list[dict] | None) -> set[str]:
    return {((t or {}).get("function") or {}).get("name") for t in (tools or []) if isinstance(t, dict)} - {None}


def _valid_tool_calls(calls: list[dict], names: set[str]) -> tuple[bool, str]:
    for call in calls or []:
        fn = call.get("function") or {}
        if fn.get("name") not in names:
            return False, f"unknown tool {fn.get('name')!r}"
        try:
            args = json.loads(fn.get("arguments") or "{}")
        except ValueError:
            return False, f"arguments for {fn.get('name')} are not valid JSON"
        if not isinstance(args, dict):
            return False, f"arguments for {fn.get('name')} must be a JSON object"
    return True, ""


# ---------------------------------------------------------------- structured_json fallback protocol

PROTOCOL = """You must answer with exactly ONE JSON object and nothing else, in one of two forms:
{"type":"tool_call","tool":"<tool name>","arguments":{...}}
{"type":"final","content":"<final answer text>"}
Use "tool_call" only with a tool listed below and arguments matching its JSON schema.
Available tools:
"""


def _structured_messages(messages: list[dict], tools: list[dict]) -> list[dict]:
    catalog = [{"name": (t.get("function") or {}).get("name"), "description": ((t.get("function") or {}).get("description") or "")[:400],
                "parameters": (t.get("function") or {}).get("parameters")} for t in tools]
    out = [{"role": "system", "content": PROTOCOL + json.dumps(catalog, ensure_ascii=False)}]
    for m in messages:
        role = m.get("role")
        if role == "tool":
            out.append({"role": "user", "content": f"TOOL_RESULT ({m.get('tool_call_id')}):\n{m.get('content')}"})
        elif role == "assistant" and m.get("tool_calls"):
            fn = (m["tool_calls"][0].get("function") or {})
            out.append({"role": "assistant", "content": json.dumps({"type": "tool_call", "tool": fn.get("name"),
                                                                    "arguments": json.loads(fn.get("arguments") or "{}")})})
        else:
            content = m.get("content")
            out.append({"role": role, "content": content if isinstance(content, str) else json.dumps(content)})
    return out


def parse_structured(text: str, names: set[str]) -> tuple[dict | None, str]:
    """Validate one protocol object. Returns (object, '') or (None, reason)."""
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        obj = json.loads(text)
    except ValueError:
        return None, "response is not a single JSON object"
    if not isinstance(obj, dict) or obj.get("type") not in {"tool_call", "final"}:
        return None, 'field "type" must be "tool_call" or "final"'
    if obj["type"] == "final":
        return (obj, "") if isinstance(obj.get("content"), str) else (None, '"final" requires string "content"')
    if obj.get("tool") not in names:
        return None, f"unknown tool {obj.get('tool')!r}"
    if not isinstance(obj.get("arguments"), dict):
        return None, '"arguments" must be a JSON object'
    return obj, ""


# ---------------------------------------------------------------- endpoints

@app.get("/health")
async def health():
    try:
        backend = await _backend("/health", timeout=5)
        status = "ok" if (backend or {}).get("status") in {"ok", None} else "loading"
    except ApiError as exc:
        status = "degraded:" + exc.code
    gpus = _gpu()
    n = METRICS["ok_count"]
    st = _state()
    if st.get("status") != "READY":
        status = "model_" + str(st.get("status", "unknown")).lower()
    return {"status": status, "model": MODEL_NAME, "served_model": st.get("model_id"), "served_model_key": st.get("model_key"),
            "model_state": st.get("status"), "tool_mode": TOOL_MODE, "max_context": _context(),
            "gpu": [g["name"] for g in gpus], "gpu_memory_used_mb": sum(g["memory_used_mb"] for g in gpus),
            "gpu_memory_total_mb": sum(g["memory_total_mb"] for g in gpus), "requests_served": METRICS["request_count"],
            "last_request_at": METRICS["last_request_at"],
            "metrics": {**{k: v for k, v in METRICS.items() if k not in {"total_seconds"}},
                        "avg_response_seconds": round(METRICS["total_seconds"] / n, 2) if n else None}}


@app.get("/v1/models")
async def models(request: Request):
    if not _authorized(request):
        METRICS["rejected_auth"] += 1
        return _err(401, "unauthorized", "missing or invalid bearer token")
    st = _state()
    return {"object": "list", "data": [{"id": MODEL_NAME, "object": "model", "owned_by": "nexus", "context_length": _context(),
                                        "max_output_tokens": MAX_NEW_TOKENS, "tool_mode": TOOL_MODE,
                                        "served_model": st.get("model_id"), "served_model_key": st.get("model_key")}]}


def _selection_inputs(body: dict) -> dict:
    mode = str(body.get("mode") or "manual")
    if mode not in {"manual", "auto"}:
        raise ApiError(400, "invalid_model_request", "mode must be manual or auto")
    keys = {m["key"] for m in CATALOG["models"]}
    for field in ("model_key", "fallback_key"):
        if body.get(field) is not None and body[field] not in keys:
            raise ApiError(400, "invalid_model_request", f"{field} not in approved catalog")
    profile = str(body.get("profile") or "general_rea")
    import model_selector as ms
    if profile not in ms.PROFILES:
        raise ApiError(400, "invalid_model_request", "unknown profile")
    ctx = body.get("required_context")
    if ctx is not None and (not isinstance(ctx, int) or not 2048 <= ctx <= 262144):
        raise ApiError(400, "invalid_model_request", "required_context must be an integer 2048..262144")
    job = body.get("job") if isinstance(body.get("job"), dict) else {}
    return {"mode": mode, "model_key": body.get("model_key"), "fallback_key": body.get("fallback_key"), "profile": profile,
            "job": {k: job[k] for k in ("tool_count", "code_heavy", "binary_analysis", "security_focus",
                                         "latency_priority", "quality_priority") if k in job}, "required_context": ctx}


@app.get("/nexus/v1/model")
async def model_state(request: Request):
    if not _authorized(request):
        METRICS["rejected_auth"] += 1
        return _err(401, "unauthorized", "missing or invalid bearer token")
    st = _state()
    return {"state": {k: st.get(k) for k in ("status", "model_key", "model_id", "context", "selection", "fallback_used",
                                             "reason", "updated_at", "tool_call_support")},
            "catalog": [{k: m[k] for k in ("key", "MODEL_ID", "MODEL_FAMILY", "TASK_PROFILES", "STATUS", "CONTEXT_LIMIT")}
                        for m in (CATALOG or {}).get("models", [])]}


@app.post("/nexus/v1/model")
async def request_model(request: Request):
    """Per-assignment model selection. dry_run returns the deterministic decision without loading anything."""
    if not _authorized(request):
        METRICS["rejected_auth"] += 1
        return _err(401, "unauthorized", "missing or invalid bearer token")
    if not CATALOG or not REQUEST_FILE:
        return _err(501, "model_switching_unavailable", "worker started without a model catalog")
    try:
        body = json.loads(await request.body() or b"{}")
        assert isinstance(body, dict)
    except (ValueError, AssertionError):
        return _err(400, "invalid_model_request", "body must be a JSON object")
    sel_in = _selection_inputs(body)
    import model_selector as ms
    # Decide as if the current model were unloaded: per-GPU total minus measured idle usage.
    totals = [g["memory_total_mb"] - 450 for g in _gpu()]
    if SELF_TEST and os.environ.get("REA_TEST_GPU_TOTALS"):
        totals = [int(x) for x in os.environ["REA_TEST_GPU_TOTALS"].split(",")]
    job = dict(sel_in["job"]); job["required_context"] = sel_in["required_context"]
    decision = ms.select(CATALOG, mode=sel_in["mode"], gpus_free_mb=totals, model_key=sel_in["model_key"],
                         fallback_key=sel_in["fallback_key"], profile=sel_in["profile"], job=job)
    out = {"decision": {k: decision.get(k) for k in ("status", "selected", "fallback", "context", "profile", "rule")},
           "considered": decision.get("considered")}
    st = _state()
    if body.get("dry_run"):
        return {"dry_run": True, **out}
    if decision["status"] == "NO_MODEL_FITS":
        return JSONResponse(status_code=409, content={"accepted": False, **out})
    if st.get("status") == "SWITCHING" or REQUEST_FILE.exists():
        return _err(409, "model_switch_in_progress", "a model switch is already in progress")
    if decision["selected"] == st.get("model_key") and decision["context"] == st.get("context") and st.get("status") == "READY":
        return {"accepted": True, "already_loaded": True, **out}
    tmp = REQUEST_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps({**sel_in, "requested_at": time.time()}))
    os.replace(tmp, REQUEST_FILE)
    return JSONResponse(status_code=202, content={"accepted": True, "already_loaded": False, **out})


@app.post("/v1/chat/completions")
async def chat(request: Request):
    if not _authorized(request):
        METRICS["rejected_auth"] += 1
        return _err(401, "unauthorized", "missing or invalid bearer token")
    raw = await request.body()
    if len(raw) > MAX_BODY_BYTES:
        METRICS["rejected_size"] += 1
        return _err(413, "request_too_large", f"request body exceeds {MAX_BODY_BYTES} bytes")
    try:
        req = json.loads(raw)
        messages = req["messages"]
        assert isinstance(messages, list) and messages and all(isinstance(m, dict) and m.get("role") for m in messages)
    except (ValueError, KeyError, AssertionError, TypeError):
        METRICS["rejected_malformed"] += 1
        return _err(400, "invalid_request", "body must be JSON with a non-empty messages array of {role, content}")
    if len(messages) > MAX_MESSAGES:
        METRICS["rejected_size"] += 1
        return _err(413, "request_too_large", f"more than {MAX_MESSAGES} messages")
    st = _state()
    if st.get("status") != "READY":
        return _err(503, "model_" + str(st.get("status", "unavailable")).lower(),
                    "model step not ready: " + str(st.get("reason") or st.get("status")))
    ctx_limit = _context()
    est = _estimate_tokens(messages) + _estimate_tokens(req.get("tools") or [])
    max_tokens = min(int(req.get("max_tokens") or req.get("max_completion_tokens") or MAX_NEW_TOKENS), MAX_NEW_TOKENS)
    if est + max_tokens > ctx_limit:
        METRICS["rejected_size"] += 1
        return _err(413, "context_length_exceeded", f"estimated {est} prompt tokens + {max_tokens} output exceeds {ctx_limit}")
    timeout = REQUEST_TIMEOUT
    if SELF_TEST and request.headers.get("x-nexus-test-timeout"):
        timeout = float(request.headers["x-nexus-test-timeout"])  # self-test only: exercises the timeout path
    started = time.monotonic()
    METRICS["request_count"] += 1
    METRICS["last_request_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    tools = req.get("tools") or []
    names = _tool_names(tools)
    mode = req.get("x_tool_mode") or TOOL_MODE
    base = {"model": MODEL_NAME, "temperature": req.get("temperature", DEFAULT_TEMPERATURE), "max_tokens": max_tokens,
            "stream": False, "chat_template_kwargs": {"enable_thinking": THINKING}}
    if req.get("response_format"):
        base["response_format"] = req["response_format"]
    for key in ("top_p", "stop", "seed"):
        if key in req:
            base[key] = req[key]
    try:
        message, finish, usage = await asyncio.wait_for(_complete(base, messages, tools, names, req, mode, timeout), timeout + 15)
    except asyncio.TimeoutError:
        METRICS["timeouts"] += 1
        return _err(504, "model_timeout", f"model did not answer within {int(timeout)}s")
    elapsed = time.monotonic() - started
    METRICS["ok_count"] += 1
    METRICS["total_seconds"] += elapsed
    METRICS["last_response_seconds"] = round(elapsed, 2)
    METRICS["prompt_tokens"] += int(usage.get("prompt_tokens") or 0)
    METRICS["completion_tokens"] += int(usage.get("completion_tokens") or 0)
    body = {"id": "chatcmpl-" + uuid.uuid4().hex[:24], "object": "chat.completion", "created": int(time.time()), "model": MODEL_NAME,
            "choices": [{"index": 0, "message": message, "finish_reason": finish}], "usage": usage,
            "nexus": {"elapsed_seconds": round(elapsed, 2), "tool_mode": mode, "estimated_prompt_tokens": est}}
    if req.get("stream"):
        return StreamingResponse(_sse(body), media_type="text/event-stream")
    return body


async def _complete(base: dict, messages: list[dict], tools: list[dict], names: set[str], req: dict, mode: str, timeout: float):
    if mode == "structured_json" and tools:
        msgs = _structured_messages(_with_rea_prompt(messages), tools)
        payload = {**base, "messages": msgs, "response_format": {"type": "json_object"}}
        for attempt in range(2):
            out = await _backend("/v1/chat/completions", payload, timeout=timeout)
            text = ((out.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
            obj, why = parse_structured(text, names)
            if obj:
                usage = out.get("usage") or {}
                if obj["type"] == "final":
                    return {"role": "assistant", "content": obj["content"]}, "stop", usage
                call = {"id": "call_" + uuid.uuid4().hex[:24], "type": "function",
                        "function": {"name": obj["tool"], "arguments": json.dumps(obj["arguments"])}}
                return {"role": "assistant", "content": None, "tool_calls": [call]}, "tool_calls", usage
            if attempt == 0:
                METRICS["structured_retries"] += 1
                payload = {**payload, "messages": msgs + [{"role": "assistant", "content": text[:2000]},
                                                          {"role": "user", "content": f"INVALID RESPONSE: {why}. Reply again with exactly one valid JSON object in the required form."}]}
        METRICS["model_errors"] += 1
        raise ApiError(502, "structured_output_invalid", f"model did not produce a valid protocol object after one retry ({why})")
    payload = {**base, "messages": _with_rea_prompt(messages)}
    if tools:
        payload["tools"] = tools
        if req.get("tool_choice") is not None:
            payload["tool_choice"] = req["tool_choice"]
    for attempt in range(2):
        out = await _backend("/v1/chat/completions", payload, timeout=timeout)
        choice = (out.get("choices") or [{}])[0]
        message = dict(choice.get("message") or {})
        message.pop("reasoning_content", None)
        calls = message.get("tool_calls") or []
        ok, why = _valid_tool_calls(calls, names) if calls else (True, "")
        if ok:
            message.setdefault("role", "assistant")
            return message, ("tool_calls" if calls else choice.get("finish_reason") or "stop"), out.get("usage") or {}
        if attempt == 0:
            METRICS["tool_call_retries"] += 1
            payload = {**payload, "messages": payload["messages"] + [
                {"role": "user", "content": f"Your previous tool call was invalid: {why}. Call one listed tool with JSON object arguments."}]}
    METRICS["model_errors"] += 1
    raise ApiError(502, "tool_call_invalid", f"model produced an invalid tool call after one retry ({why})")


async def _sse(body: dict):
    choice = body["choices"][0]
    msg = choice["message"]
    head = {k: body[k] for k in ("id", "object", "created", "model")}
    head["object"] = "chat.completion.chunk"

    def chunk(delta: dict, finish=None, usage=None):
        data = {**head, "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}
        if usage is not None:
            data["usage"] = usage
        return "data: " + json.dumps(data) + "\n\n"

    yield chunk({"role": "assistant"})
    if msg.get("content"):
        yield chunk({"content": msg["content"]})
    for i, call in enumerate(msg.get("tool_calls") or []):
        yield chunk({"tool_calls": [{"index": i, "id": call.get("id"), "type": "function",
                                     "function": {"name": call["function"]["name"], "arguments": ""}}]})
        yield chunk({"tool_calls": [{"index": i, "function": {"arguments": call["function"].get("arguments") or "{}"}}]})
    yield chunk({}, choice["finish_reason"], body.get("usage") or {})
    yield "data: [DONE]\n\n"
