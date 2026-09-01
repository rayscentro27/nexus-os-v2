"""Bounded Creative model health and fallback routing."""
from __future__ import annotations

import time
import os
import shutil
from typing import Any

from nexus_agent_platform.ai_review_provider import ollama_health
from nexus_agent_platform.oracle_gemma_provider import health as oracle_health
from nexus_agent_platform.governed.persistence import read_records

HEALTH_STATES = {"AVAILABLE", "DEGRADED", "UNAVAILABLE", "TIMEOUT", "AUTH_REQUIRED", "RATE_LIMITED", "NOT_CONFIGURED"}


def catalog() -> list[dict[str, Any]]:
    oracle = oracle_health()
    local = ollama_health()
    oracle_state = "AVAILABLE" if oracle.get("status") == "ORACLE_AI_READY" else ("TIMEOUT" if "TIMEOUT" in str(oracle.get("status")) else "UNAVAILABLE")
    local_state = "AVAILABLE" if local.get("status") == "AVAILABLE" else "UNAVAILABLE"
    hermes_configured = bool(shutil.which("hermes") and os.path.exists(os.path.expanduser("~/.hermes/auth.json")))
    return [
        {"model_id": oracle.get("model", "gemma3:4b"), "provider": "oracle_ollama_gemma", "execution_location": "existing Oracle VM", "task_class": "creative_reasoning", "health": oracle_state, "latency_ms": oracle.get("latency_ms"), "cost_class": "ZERO_TOKEN_CHARGE_CONFIGURED_ROUTE", "context": "JSON advisory", "multimodal": False, "last_success": None, "failure_count": 1 if oracle_state != "AVAILABLE" else 0},
        {"model_id": "local_ollama", "provider": "ollama", "execution_location": "Mac control plane", "task_class": "creative_reasoning", "health": local_state, "latency_ms": local.get("latency_ms"), "cost_class": "LOCAL_COMPUTE", "context": "JSON advisory", "multimodal": False, "last_success": None, "failure_count": 1 if local_state != "AVAILABLE" else 0},
        {"model_id": os.getenv("HERMES_INFERENCE_MODEL", "gpt-5.5"), "provider": "openai_codex_oauth", "execution_location": "active Hermes runtime", "task_class": "creative_reasoning", "health": "AVAILABLE" if hermes_configured else "AUTH_REQUIRED", "latency_ms": None, "cost_class": "EXISTING_AUTHORIZED_ROUTE", "context": "JSON advisory", "multimodal": False, "last_success": None, "failure_count": 0 if hermes_configured else 1},
    ]


def select() -> dict[str, Any]:
    rows = catalog()
    # A completed bounded invocation is stronger evidence than a provider
    # health endpoint that only proves the service is reachable.
    successes = read_records("creative_ai")
    proven = next((r for r in successes if r.get("status") == "PASS" and r.get("provider")), None)
    if proven:
        for row in rows:
            if row["provider"] == proven["provider"] and row["model_id"] == proven.get("model", row["model_id"]):
                row["health"] = "AVAILABLE"
                row["last_success"] = proven.get("created_at")
                row["latency_ms"] = proven.get("latency_ms")
                return {"status": "AVAILABLE", "selected": row, "fallback_policy": "primary -> configured local/private -> approved zero-cost -> BLOCKED", "evidence": "completed creative_ai invocation"}
    for row in rows:
        if row["health"] == "AVAILABLE":
            return {"status": "AVAILABLE", "selected": row, "fallback_policy": "primary -> configured local/private -> approved zero-cost -> BLOCKED"}
    return {"status": "UNAVAILABLE", "selected": None, "candidates": rows, "fallback_policy": "primary -> configured local/private -> approved zero-cost -> BLOCKED", "checked_at": time.time()}
