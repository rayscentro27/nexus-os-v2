"""Provider-agnostic, benchmark-only response capture and normalization.

This module deliberately does not participate in Nova production execution.
It keeps provider-envelope parsing, assistant extraction, and benchmark scoring
as separate stages so malformed provider output cannot be mislabeled as model
quality.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _body_hash(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()[:24]


def _escape_controls_inside_json_strings(text: str) -> str:
    """Repair illegal raw controls only while inside JSON string literals.

    The original character is retained as a JSON unicode escape; meaningful
    model text is not deleted. This is only a tolerant envelope parser.
    """
    out: list[str] = []
    in_string = False
    escaped = False
    for char in text:
        if in_string:
            if escaped:
                out.append(char)
                escaped = False
            elif char == "\\":
                out.append(char)
                escaped = True
            elif char == '"':
                out.append(char)
                in_string = False
            elif ord(char) < 0x20:
                out.append(f"\\u{ord(char):04x}")
            else:
                out.append(char)
        else:
            out.append(char)
            if char == '"':
                in_string = True
    return "".join(out)


def parse_provider_envelope(raw: bytes, *, content_type: str | None = None) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Parse JSON or SSE JSON without exposing body contents in diagnostics."""
    evidence: dict[str, Any] = {
        "content_type": content_type,
        "stream": bool(content_type and "text/event-stream" in content_type.lower()),
        "body_hash": _body_hash(raw),
        "parse_status": "OK",
        "parse_exception": None,
    }
    text = raw.decode("utf-8", errors="replace")
    candidates = [text]
    if evidence["stream"] or text.lstrip().startswith("data:"):
        events = []
        for line in text.splitlines():
            if line.startswith("data:"):
                payload = line[5:].strip()
                if payload and payload != "[DONE]":
                    events.append(payload)
        candidates = events or [text]
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                evidence["envelope_keys"] = sorted(parsed.keys())
                evidence["parse_mode"] = "strict"
                return parsed, evidence
        except (TypeError, ValueError) as exc:
            evidence["parse_exception"] = type(exc).__name__
        try:
            parsed = json.loads(_escape_controls_inside_json_strings(candidate))
            if isinstance(parsed, dict):
                evidence["envelope_keys"] = sorted(parsed.keys())
                evidence["parse_mode"] = "escaped_controls"
                return parsed, evidence
        except (TypeError, ValueError) as exc:
            evidence["parse_exception"] = type(exc).__name__
    evidence["parse_status"] = "INVALID_PROVIDER_JSON"
    evidence["envelope_keys"] = []
    return None, evidence


def _extract_message(envelope: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    choices = envelope.get("choices")
    if not isinstance(choices, list) or not choices:
        return None, "missing_or_empty_choices"
    choice = choices[0] if isinstance(choices[0], dict) else {}
    message = choice.get("message")
    if not isinstance(message, dict):
        return None, "missing_message"
    return {"choice": choice, "message": message}, None


def normalize_response(*, benchmark_case_id: str, provider: str, requested_model: str,
                       raw: bytes, http_status: int | None, content_type: str | None,
                       started_at: str | None = None, completed_at: str | None = None) -> dict[str, Any]:
    """Return safe canonical result; assistant prose remains a string."""
    started = started_at or _now()
    completed = completed_at or _now()
    envelope, evidence = parse_provider_envelope(raw, content_type=content_type)
    result: dict[str, Any] = {
        "benchmark_case_id": benchmark_case_id,
        "provider": provider,
        "requested_model": requested_model,
        "observed_model": None,
        "started_at": started,
        "completed_at": completed,
        "latency_ms": None,
        "http_status": http_status,
        "capture_status": "CAPTURE_FAILED",
        "assistant_text": None,
        "tool_calls": [],
        "finish_reason": None,
        "usage": None,
        "provider_error": None,
        "extraction_error": None,
        "raw_evidence": evidence,
    }
    if envelope is None:
        result["extraction_error"] = evidence.get("parse_exception")
        return result
    result["observed_model"] = envelope.get("model")
    result["usage"] = envelope.get("usage") if isinstance(envelope.get("usage"), dict) else None
    if isinstance(envelope.get("error"), dict):
        result["provider_error"] = {"code": envelope["error"].get("code"), "type": envelope["error"].get("type"), "message_present": bool(envelope["error"].get("message"))}
        result["capture_status"] = "PROVIDER_ERROR"
        return result
    extracted, error = _extract_message(envelope)
    if error:
        result["extraction_error"] = error
        result["capture_status"] = "EXTRACTION_FAILED"
        return result
    choice = extracted["choice"]
    message = extracted["message"]
    content = message.get("content")
    if content is not None and not isinstance(content, str):
        result["extraction_error"] = "content_not_string"
    elif isinstance(content, str):
        result["assistant_text"] = content
    tool_calls = message.get("tool_calls")
    if isinstance(tool_calls, list):
        result["tool_calls"] = tool_calls
    result["finish_reason"] = choice.get("finish_reason")
    result["capture_status"] = "CAPTURED"
    return result


def serialize_result(result: dict[str, Any]) -> str:
    """Serialize safely; never reparse model prose as JSON."""
    return json.dumps(result, ensure_ascii=False, sort_keys=True)
