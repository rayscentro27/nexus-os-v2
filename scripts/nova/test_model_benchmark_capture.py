import json

from model_benchmark_capture import normalize_response, parse_provider_envelope, serialize_result


def test_normal_text_and_unicode_are_captured_as_string():
    raw = json.dumps({"id": "x", "model": "m", "choices": [{"message": {"content": "Ray — Nexus\nworks", "role": "assistant"}, "finish_reason": "stop"}]}).encode()
    result = normalize_response(benchmark_case_id="x", provider="openrouter", requested_model="m", raw=raw, http_status=200, content_type="application/json")
    assert result["capture_status"] == "CAPTURED"
    assert result["assistant_text"] == "Ray — Nexus\nworks"
    assert result["finish_reason"] == "stop"


def test_illegal_raw_controls_are_escaped_not_deleted():
    raw = b'{"model":"m","choices":[{"message":{"content":"line1\nline2\tend"}}]}'
    envelope, evidence = parse_provider_envelope(raw, content_type="application/json")
    assert envelope is not None
    assert evidence["parse_mode"] == "escaped_controls"
    result = normalize_response(benchmark_case_id="x", provider="p", requested_model="m", raw=raw, http_status=200, content_type="application/json")
    assert result["assistant_text"] == "line1\nline2\tend"


def test_tool_calls_and_empty_content_are_distinct_from_provider_error():
    raw = json.dumps({"model": "m", "choices": [{"message": {"content": None, "tool_calls": [{"id": "c1", "type": "function"}]}, "finish_reason": "tool_calls"}]}).encode()
    result = normalize_response(benchmark_case_id="x", provider="p", requested_model="m", raw=raw, http_status=200, content_type="application/json")
    assert result["capture_status"] == "CAPTURED"
    assert result["assistant_text"] is None
    assert result["tool_calls"][0]["id"] == "c1"


def test_provider_error_is_not_scored_as_model_quality():
    raw = json.dumps({"error": {"code": 429, "type": "rate_limit", "message": "redacted"}}).encode()
    result = normalize_response(benchmark_case_id="x", provider="p", requested_model="m", raw=raw, http_status=429, content_type="application/json")
    assert result["capture_status"] == "PROVIDER_ERROR"
    assert result["provider_error"]["code"] == 429
    assert result["assistant_text"] is None


def test_sse_and_safe_serialization():
    raw = b'data: {"model":"m","choices":[{"message":{"content":"hello"}}]}\n\ndata: [DONE]\n'
    envelope, evidence = parse_provider_envelope(raw, content_type="text/event-stream")
    assert envelope["model"] == "m"
    assert evidence["stream"] is True
    result = normalize_response(benchmark_case_id="x", provider="p", requested_model="m", raw=raw, http_status=200, content_type="text/event-stream")
    encoded = serialize_result(result)
    assert json.loads(encoded)["assistant_text"] == "hello"
    assert "Authorization" not in encoded
