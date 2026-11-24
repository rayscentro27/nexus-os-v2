"""Zero-cost after-action review provider selection.

The caller owns deterministic execution. This module only observes completed
evidence and never makes provider availability a prerequisite for the loop.
"""
from __future__ import annotations
import json, os, time, urllib.request
from typing import Any

def ollama_health(base_url: str = "http://127.0.0.1:11434") -> dict[str, Any]:
    started = time.monotonic()
    try:
        req = urllib.request.Request(base_url.rstrip("/") + "/api/tags")
        with urllib.request.urlopen(req, timeout=3) as response:
            body = json.loads(response.read().decode() or "{}")
        models = [x.get("name") for x in body.get("models", []) if x.get("name")]
        return {"provider": "ollama", "local": True, "status": "AVAILABLE" if models else "DEGRADED", "models": models, "latency_ms": round((time.monotonic()-started)*1000, 2), "network_api": False, "cost_bearing": False}
    except Exception as exc:
        return {"provider": "ollama", "local": True, "status": "UNAVAILABLE", "models": [], "latency_ms": round((time.monotonic()-started)*1000, 2), "error": exc.__class__.__name__, "network_api": False, "cost_bearing": False}

def select_review_provider() -> dict[str, Any]:
    oracle = {"status": "OFFLINE_EXPERIMENT_ONLY", "provider": "oracle_ollama_gemma",
              "production_eligible": False}
    if os.environ.get("NEXUS_REASONING_CLASS") == "OFFLINE_EXPERIMENT":
        try:
            from nexus_agent_platform.oracle_gemma_provider import health as oracle_health
            value = oracle_health()
            if value["status"] == "ORACLE_AI_READY":
                return {**value, "reasoning_class": "OFFLINE_EXPERIMENT", "production_eligible": False}
            oracle = value
        except Exception:
            oracle = {"status": "ORACLE_TUNNEL_UNAVAILABLE", "production_eligible": False}
    local = ollama_health()
    if local["status"] == "AVAILABLE": return local
    return {"provider": "deterministic_fallback", "status": "DETERMINISTIC_FALLBACK_USED", "fallback_status": local["status"], "network_api": False, "cost_bearing": False, "oracle": oracle, "ollama": local, "reasoning_class": "DETERMINISTIC"}
