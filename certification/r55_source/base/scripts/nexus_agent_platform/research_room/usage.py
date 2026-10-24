"""Honest per-case model-call accounting; absent provider data stays unknown."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any


def record_call(case: dict[str, Any], *, provider: str, model: str | None, role: str,
                usage: dict[str, Any] | None, cost_usd: float | None,
                duration_ms: float, purpose: str, cache_hit: bool = False,
                runtime: str | None = None, timeout: bool = False,
                fallback_model_used: str | None = None,
                provider_request_id: str | None = None,
                count_for_totals: bool = True) -> dict[str, Any]:
    usage = usage or {}
    input_tokens = usage.get("prompt_tokens", usage.get("input_tokens"))
    output_tokens = usage.get("completion_tokens", usage.get("output_tokens"))
    total_tokens = usage.get("total_tokens")
    if total_tokens is None and isinstance(input_tokens, (int, float)) and isinstance(output_tokens, (int, float)):
        total_tokens = int(input_tokens + output_tokens)
    call_end = datetime.now(timezone.utc)
    call = {"provider": provider, "model": model, "role": role,
            "call_id": "rrcall_" + uuid.uuid4().hex[:20],
            "provider_request_id": provider_request_id or "UNKNOWN",
            "call_start": (call_end - timedelta(milliseconds=max(duration_ms, 0))).isoformat(),
            "call_end": call_end.isoformat(),
            "input_tokens": input_tokens if isinstance(input_tokens, (int, float)) else "UNKNOWN",
            "output_tokens": output_tokens if isinstance(output_tokens, (int, float)) else "UNKNOWN",
            "total_tokens": total_tokens if isinstance(total_tokens, (int, float)) else "UNKNOWN",
            "estimated_cost_usd": float(cost_usd) if isinstance(cost_usd, (int, float)) else "UNKNOWN",
            "cache_hit": bool(cache_hit), "duration_ms": round(max(duration_ms, 0), 2),
            "call_duration_seconds": round(max(duration_ms, 0) / 1000, 3),
            "runtime": runtime or "UNKNOWN", "timeout": bool(timeout),
            "fallback_model_used": fallback_model_used or "NONE", "purpose": purpose}
    ledger = case.setdefault("model_usage", {})
    defaults = {"calls": [], "total_model_calls": 0,
        "total_input_tokens": 0, "total_output_tokens": 0, "total_tokens": 0,
        "estimated_total_cost_usd": 0.0, "cache_hits": 0, "cache_misses": 0,
        "token_counts_complete": True, "total_tokens_complete": True, "cost_complete": True,
        "total_model_latency": 0.0, "average_model_latency": 0.0,
        "slowest_model": None, "slowest_call_seconds": 0.0}
    for name, default in defaults.items():
        ledger.setdefault(name, default)
    ledger["calls"].append(call)
    if cache_hit:
        ledger["cache_hits"] += 1
    elif not count_for_totals:
        # Keep a denied/preflight attempt in the call history without counting
        # it as a provider invocation or poisoning measured usage totals.
        call["result_state"] = call.get("result_state") or "NOT_INVOKED"
    else:
        ledger["cache_misses"] += 1
        ledger["total_model_calls"] += 1
        duration_seconds = float(call["call_duration_seconds"])
        ledger["total_model_latency"] += duration_seconds
        ledger["average_model_latency"] = ledger["total_model_latency"] / max(1, ledger["total_model_calls"])
        if duration_seconds >= float(ledger.get("slowest_call_seconds", 0)):
            ledger["slowest_call_seconds"] = duration_seconds
            ledger["slowest_model"] = model or "UNKNOWN"
        if isinstance(call["input_tokens"], (int, float)) and isinstance(ledger.get("total_input_tokens"), (int, float)):
            ledger["total_input_tokens"] += int(call["input_tokens"])
        else:
            ledger["total_input_tokens"] = "UNKNOWN"
            ledger["token_counts_complete"] = False
        if isinstance(call["output_tokens"], (int, float)) and isinstance(ledger.get("total_output_tokens"), (int, float)):
            ledger["total_output_tokens"] += int(call["output_tokens"])
        else:
            ledger["total_output_tokens"] = "UNKNOWN"
            ledger["token_counts_complete"] = False
        if isinstance(call["total_tokens"], (int, float)) and isinstance(ledger.get("total_tokens"), (int, float)):
            ledger["total_tokens"] += int(call["total_tokens"])
        else:
            ledger["total_tokens"] = "UNKNOWN"
            ledger["total_tokens_complete"] = False
        if isinstance(call["estimated_cost_usd"], (int, float)) and isinstance(ledger.get("estimated_total_cost_usd"), (int, float)):
            ledger["estimated_total_cost_usd"] += float(call["estimated_cost_usd"])
        else:
            ledger["estimated_total_cost_usd"] = "UNKNOWN"
            ledger["cost_complete"] = False
    if not ledger["token_counts_complete"]:
        ledger["total_input_tokens"] = ledger["total_output_tokens"] = "UNKNOWN"
    if not ledger.get("total_tokens_complete", True):
        ledger["total_tokens"] = "UNKNOWN"
    if not ledger["cost_complete"]:
        ledger["estimated_total_cost_usd"] = "UNKNOWN"
    return call
