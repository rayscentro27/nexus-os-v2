"""Bounded Creative model health and fallback routing."""
from __future__ import annotations

import time
from typing import Any

from nexus_agent_platform.ai_review_provider import ollama_health
from nexus_agent_platform.oracle_gemma_provider import health as oracle_health

HEALTH_STATES = {"AVAILABLE", "DEGRADED", "UNAVAILABLE", "TIMEOUT", "AUTH_REQUIRED", "RATE_LIMITED", "NOT_CONFIGURED"}


def catalog() -> list[dict[str, Any]]:
    oracle = oracle_health()
    local = ollama_health()
    oracle_state = "AVAILABLE" if oracle.get("status") == "ORACLE_AI_READY" else ("TIMEOUT" if "TIMEOUT" in str(oracle.get("status")) else "UNAVAILABLE")
    local_state = "AVAILABLE" if local.get("status") == "AVAILABLE" else "UNAVAILABLE"
    return [
        {"model_id": oracle.get("model", "gemma3:4b"), "provider": "oracle_ollama_gemma", "execution_location": "existing Oracle VM", "task_class": "creative_reasoning", "health": oracle_state, "latency_ms": oracle.get("latency_ms"), "cost_class": "ZERO_TOKEN_CHARGE_CONFIGURED_ROUTE", "context": "JSON advisory", "multimodal": False, "last_success": None, "failure_count": 1 if oracle_state != "AVAILABLE" else 0},
        {"model_id": "local_ollama", "provider": "ollama", "execution_location": "Mac control plane", "task_class": "creative_reasoning", "health": local_state, "latency_ms": local.get("latency_ms"), "cost_class": "LOCAL_COMPUTE", "context": "JSON advisory", "multimodal": False, "last_success": None, "failure_count": 1 if local_state != "AVAILABLE" else 0},
    ]


def select() -> dict[str, Any]:
    rows = catalog()
    for row in rows:
        if row["health"] == "AVAILABLE":
            return {"status": "AVAILABLE", "selected": row, "fallback_policy": "primary -> configured local/private -> approved zero-cost -> BLOCKED"}
    return {"status": "UNAVAILABLE", "selected": None, "candidates": rows, "fallback_policy": "primary -> configured local/private -> approved zero-cost -> BLOCKED", "checked_at": time.time()}
