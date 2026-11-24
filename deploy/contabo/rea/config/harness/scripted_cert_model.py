#!/usr/bin/env python3
"""Deterministic OpenAI-compatible *certification stub* for the REA harness tool layer.

NOT a model and NOT intelligent. It replays a fixed tool-call script so OpenCode -> REA MCP ->
tool -> result -> OpenCode can be proven before a real model endpoint exists. It binds to
127.0.0.1 inside the nexus-rea container only and is started/stopped per certification session.

Every request is logged (advertised tool names, tool-result digests) to <session temp>/stub_log.jsonl.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = int(os.environ.get("REA_STUB_PORT", "18799"))
TEMP = Path(os.environ["REA_SESSION_TEMP"])
FIXTURE_PORT = int(os.environ.get("REA_FIXTURE_PORT", "18798"))
CHROMIUM = os.environ["REA_CHROMIUM_PATH"]
LOG = TEMP / "stub_log.jsonl"
MODEL_ID = "scripted-certification-stub"


def script() -> list[tuple[str, dict]]:
    repo = str(TEMP / "repo")
    origin = f"http://127.0.0.1:{FIXTURE_PORT}"
    return [
        ("read", {"filePath": f"{repo}/README.md"}),
        ("rea_analyze_javascript_application", {"input_path": repo, "format": "directory", "detail": "summary"}),
        ("rea_capture_browser_scenario", {
            "browser": {"mode": "launch", "executable_path": CHROMIUM, "headless": True},
            "start_url": {"url": origin + "/"},
            "actions": [
                {"step_id": "open", "action": "goto", "destination": {"url": origin + "/"}, "wait_until": "load", "timeout_ms": 20000},
                {"step_id": "items", "action": "wait_for", "locator": {"kind": "css", "selector": "li[data-sku=\"MUG-11OZ\"]"}, "state": "visible", "timeout_ms": 10000},
                {"step_id": "refresh", "action": "click", "locator": {"kind": "role", "role": "button", "name": "Refresh catalog"}, "timeout_ms": 10000},
                {"step_id": "settle", "action": "wait_for_timeout", "duration_ms": 500},
            ],
            "capture": {"at_end": ["url", "dom", "screenshot"], "events": ["network", "console"],
                        "network": {"request_body": False, "response_body": True, "header_values": False}},
        }),
        ("rea_open_binary", {"path": str(TEMP / "bin" / "true"), "provider_id": "ghidra"}),
        ("rea_binary_overview", {}),
        ("rea_list_procedures", {"detail": "summary"}),
        ("rea_close_binary", {}),
    ]


def _log(entry: dict) -> None:
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"at": time.time(), **entry}, sort_keys=True) + "\n")


def _tool_messages(messages: list[dict]) -> list[dict]:
    return [m for m in messages if m.get("role") == "tool"]


def _content_text(message: dict) -> str:
    content = message.get("content")
    if isinstance(content, list):
        return " ".join(str(part.get("text") or "") for part in content if isinstance(part, dict))
    return str(content or "")


def _resolve(advertised: list[str], name: str) -> str | None:
    if name in advertised:
        return name
    matches = [a for a in advertised if a.endswith("_" + name.split("_", 1)[-1]) and a.startswith("rea")]
    return matches[0] if len(matches) == 1 else None


def _final(messages: list[dict], advertised: list[str]) -> str:
    results = []
    for msg in _tool_messages(messages):
        text = _content_text(msg)
        results.append({"tool_call_id": msg.get("tool_call_id"), "bytes": len(text),
                        "sha256": hashlib.sha256(text.encode()).hexdigest()[:16],
                        "evidence_ids": sorted(set(re.findall(r"\bev[-_][A-Za-z0-9_-]{6,64}", text)))[:5],
                        "error": bool(re.search(r'"isError"\s*:\s*true|\b(?:error|failed)\b', text[:400], re.I))})
    rea_tools = [a for a in advertised if a.startswith("rea_")]
    return json.dumps({
        "OBJECTIVE": "Certify the REA harness tool layer (model-less).",
        "TARGET": "Nexus-authored fixture repo, fixture web page, GNU coreutils `true` binary.",
        "OBSERVED_BEHAVIOR": "Scripted certification stub executed a fixed tool sequence; no reasoning performed.",
        "WORKFLOWS": ["read README", "static JS app analysis", "headless browser scenario", "Ghidra headless session"],
        "FEATURES": [], "DATA_FLOW": [], "INTERFACES": [], "DEPENDENCIES": [],
        "SECURITY_CONSIDERATIONS": ["No secrets supplied; fixture targets only."],
        "LIMITATIONS": ["SCRIPTED_CERTIFICATION_STUB: not an intelligent REA result."],
        "OPPORTUNITIES": [], "NEXUS_SPECIFIC_IMPROVEMENTS": [], "ORIGINAL_IMPLEMENTATION_GUIDANCE": [],
        "DEVELOPMENT_DIRECTIVE": "NONE (certification run).",
        "EVIDENCE": [{"tool": "opencode_tool_result", "evidence_ref": r["sha256"], "supports": r} for r in results],
        "CONFIDENCE": "HIGH tool-layer evidence; NOT_APPLICABLE for analysis quality.",
        "STUB_ADVERTISED_REA_TOOL_COUNT": len(rea_tools),
    }, sort_keys=True)


def _chunk(delta: dict, finish: str | None = None, usage: dict | None = None) -> bytes:
    body = {"id": "chatcmpl-stub", "object": "chat.completion.chunk", "created": int(time.time()), "model": MODEL_ID,
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}
    if usage:
        body["usage"] = usage
    return b"data: " + json.dumps(body).encode() + b"\n\n"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # quiet
        return

    def _json(self, status: int, payload: dict) -> None:
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path.rstrip("/").endswith("/models"):
            return self._json(200, {"object": "list", "data": [{"id": MODEL_ID, "object": "model"}]})
        return self._json(404, {"error": "not_found"})

    def do_POST(self):
        length = int(self.headers.get("content-length") or 0)
        req = json.loads(self.rfile.read(length) or b"{}")
        messages = req.get("messages") or []
        advertised = [t.get("function", {}).get("name") for t in (req.get("tools") or []) if isinstance(t, dict)]
        advertised = [a for a in advertised if a]
        done = len(_tool_messages(messages))
        steps = script()
        if not advertised:
            # Title/summary side requests: plain text, no tools.
            kind, payload = "text", {"content": "REA harness certification"}
        elif done < len(steps):
            name, args = steps[done]
            resolved = _resolve(advertised, name)
            if not resolved:
                kind, payload = "text", {"content": json.dumps({"CERT_FAILURE": f"TOOL_NOT_ADVERTISED:{name}"})}
            else:
                kind, payload = "tool", {"name": resolved, "arguments": json.dumps(args)}
        else:
            kind, payload = "text", {"content": _final(messages, advertised)}
        _log({"request_tools": len(advertised), "rea_tools": sorted(a for a in advertised if a.startswith("rea_"))[:400]
              if done == 0 else len([a for a in advertised if a.startswith("rea_")]),
              "tool_results_seen": done, "reply": kind, "tool": payload.get("name"),
              "last_tool_result_bytes": len(_content_text(_tool_messages(messages)[-1])) if done else 0})
        usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        if not req.get("stream"):
            msg = {"role": "assistant", "content": payload.get("content")}
            if kind == "tool":
                msg = {"role": "assistant", "content": None, "tool_calls": [
                    {"id": f"call_{done}", "type": "function", "function": payload}]}
            return self._json(200, {"id": "chatcmpl-stub", "object": "chat.completion", "created": int(time.time()), "model": MODEL_ID,
                                    "choices": [{"index": 0, "message": msg, "finish_reason": "tool_calls" if kind == "tool" else "stop"}],
                                    "usage": usage})
        self.send_response(200)
        self.send_header("content-type", "text/event-stream")
        self.send_header("cache-control", "no-cache")
        self.end_headers()
        if kind == "tool":
            self.wfile.write(_chunk({"role": "assistant", "tool_calls": [
                {"index": 0, "id": f"call_{done}", "type": "function", "function": {"name": payload["name"], "arguments": ""}}]}))
            self.wfile.write(_chunk({"tool_calls": [{"index": 0, "function": {"arguments": payload["arguments"]}}]}))
            self.wfile.write(_chunk({}, "tool_calls", usage))
        else:
            self.wfile.write(_chunk({"role": "assistant", "content": payload["content"]}))
            self.wfile.write(_chunk({}, "stop", usage))
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


def main() -> int:
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(json.dumps({"stub": "listening", "port": PORT}), flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
