"""Bounded model-powered Creative intelligence using the existing Oracle Ollama lane.

The model is advisory only. Nexus-owned code remains authoritative for state,
claims, versioning, budgets, and external-action denial. Prompts request short
summaries and structured JSON; no chain-of-thought is stored.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
import urllib.request
import asyncio
from datetime import datetime, timezone
from typing import Any

from nexus_agent_platform.governed.persistence import append_record, emit_audit_event, read_records
from nexus_agent_platform.creative.department import build_brief, territories
from nexus_agent_platform.creative.model_router import select_task_route

MAX_AI_INVOCATIONS = 40


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()[:20]


def _compact(value: Any, limit: int = 1800) -> str:
    text = json.dumps(value, sort_keys=True, default=str) if not isinstance(value, str) else value
    return text[:limit]


def _json_response(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {"raw_summary": str(value)}
    except json.JSONDecodeError:
        return {"raw_summary": " ".join(text.split())[:2400], "parse_status": "NON_JSON"}


class BoundedCreativeModel:
    def __init__(self) -> None:
        self.calls = 0

    def call(self, purpose: str, instruction: str, context: dict[str, Any], task_class: str = "creative.summary") -> dict[str, Any]:
        if self.calls >= MAX_AI_INVOCATIONS:
            raise RuntimeError("creative_ai_budget_exhausted")
        self.calls += 1
        prompt = (
            "You are Nexus Creative " + purpose + ". Return one concise JSON object only. "
            "Do not provide chain-of-thought or hidden reasoning. Do not invent evidence, "
            "testimonials, prices, results, demand, or claims. Use null or UNKNOWN when absent.\n"
            + instruction + "\nCONTEXT:\n" + _compact(context, 10000)
        )
        route = select_task_route(task_class)
        primary = route.get("primary_spec") or {}
        fallback = route.get("fallback_spec") or {}
        primary_provider = primary.get("provider")
        primary_model = route.get("primary_model")
        # Use the existing Nexus provider adapter selected by the router.
        if primary_provider == "openrouter" and primary_model:
            started = time.monotonic()
            try:
                from nexus_agent_platform.workflows.litellm_adapter import LlmGatewayAdapter
                response = asyncio.run(LlmGatewayAdapter("nexus_creative").completion(model=primary_model, messages=[{"role": "system", "content": "Return only the requested JSON."}, {"role": "user", "content": instruction + "\nCONTEXT:\n" + _compact(context, 10000)}], temperature=0.2, max_tokens=1024, timeout=min(float(os.getenv("NEXUS_CREATIVE_MODEL_TIMEOUT", "60")), 60.0)))
                if response.get("content") and not response.get("error"):
                    result = _json_response(response["content"])
                    result.update({"purpose": purpose, "model": response.get("model", primary_model), "provider": "openrouter", "execution_location": "existing Nexus provider adapter", "status": "PASS", "latency_ms": round((time.monotonic() - started) * 1000, 1), "call_number": self.calls, "task_class": task_class, "route": route})
                    return result
            except Exception:
                pass
        started = time.monotonic()
        fallback_model = fallback.get("model")
        endpoint = os.getenv("NEXUS_CREATIVE_MODEL_ENDPOINT", "http://127.0.0.1:11435")
        payload = json.dumps({"model": fallback_model, "prompt": prompt, "stream": False}).encode("utf-8")
        req = urllib.request.Request(endpoint.rstrip("/") + "/api/generate", data=payload, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=int(os.getenv("NEXUS_CREATIVE_MODEL_TIMEOUT", "120"))) as response:
                raw = json.loads(response.read().decode() or "{}")
            result = _json_response(raw.get("response", ""))
            result.update({"purpose": purpose, "model": fallback_model, "provider": "oracle_ollama_gemma", "execution_location": "existing Oracle Ollama service", "status": "PASS", "latency_ms": round((time.monotonic() - started) * 1000, 1), "call_number": self.calls, "task_class": task_class, "route": route})
            return result
        except Exception as exc:
            return {"purpose": purpose, "model": fallback_model, "provider": "oracle_ollama_gemma", "status": "BLOCKED", "error": type(exc).__name__, "call_number": self.calls, "task_class": task_class, "route": route}


def _persist(kind: str, payload: dict[str, Any], fingerprint: Any) -> dict[str, Any]:
    record = {"schema_version": "nexus.creative-ai.v1", "record_id": f"creative_ai_{_hash((kind, fingerprint))}", "kind": kind, "created_at": _now(), "external_action_performed": False, **payload}
    existing = next((x for x in read_records("creative_ai" ) if x.get("record_id") == record["record_id"]), None)
    if existing:
        return {**existing, "persistence": "DUPLICATE_SUPPRESSED"}
    append_record("creative_ai", record)
    return {**record, "persistence": "CREATED"}


def run_real_creative_ai_e2e() -> dict[str, Any]:
    brief = build_brief()
    existing = territories(brief)
    prior_assets = [x for x in read_records("creative_assets") if x.get("brief_id") == brief["creative_brief_id"]][:12]
    context = {"brief": brief, "existing_territories": existing, "prior_creative_assets": prior_assets, "growth_variant": "individual_vehicle_convenience", "evidence_boundary": "interest is not yet observed"}
    client = BoundedCreativeModel()
    director = client.call("Director", "Critique the four existing territories for distinctiveness and genericness. Ask whether the work could apply to 100 unrelated local businesses. Return keys: distinctiveness_summary, generic_elements, evidence_specificity_gaps, recommendation, additional_direction_if_justified.", context, "creative.direction")
    _persist("director", director, (brief["creative_brief_id"], "director", existing))
    copy = client.call("Copywriter", "Generate fresh immutable copy variants, not a rewrite of prior assets. Return keys: landing_hero, facebook, instagram, tiktok_hook, reel_hook, youtube_short_hook. Each must be specific to individual vehicle owners, internal-only, and avoid unsupported proof.", {**context, "director_summary": director}, "creative.copy_variation")
    _persist("copywriter", copy, (brief["creative_brief_id"], "copywriter", director.get("recommendation")))
    critic = client.call("Critic", "Inspect the actual proposed copy below as a separate critic. Return keys: strengths, weaknesses, genericness, claim_problems, channel_problems, recommended_revision. Do not approve by default.", {"brief": brief, "copy": copy, "territories": existing}, "creative.critic")
    _persist("critic", critic, (brief["creative_brief_id"], "critic", copy))
    revision = client.call("Revision", "Create one model-powered v2 responding to the critic. Return keys: revised_landing_hero, revised_cta, change, why_change, expected_improvement, claim_status.", {"brief": brief, "copy": copy, "critic": critic}, "creative.revision")
    _persist("revision", revision, (brief["creative_brief_id"], "revision", critic))
    emit_audit_event({"event": "creative_ai_e2e_completed", "brief_id": brief["creative_brief_id"], "provider": "nexus_model_router", "model": "task_specific", "ai_calls": client.calls, "external_action_performed": False})
    return {"status": "PASS" if all(x.get("status") == "PASS" for x in (director, copy, critic, revision)) else "BLOCKED", "provider": "nexus_model_router", "model": "task_specific", "execution_location": "existing Nexus model router", "calls": client.calls, "director": director, "copy": copy, "critic": critic, "revision": revision, "brief_id": brief["creative_brief_id"], "budget": {"max": MAX_AI_INVOCATIONS, "used": client.calls}}


if __name__ == "__main__":
    print(json.dumps(run_real_creative_ai_e2e(), indent=2, sort_keys=True, default=str))
