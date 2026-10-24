#!/usr/bin/env python3
"""Nexus OS v2 — policy-gated Model Router (server-side decision layer).

Decides WHICH route a task is eligible for (deterministic / manual / local_private /
free_public_cloud / blocked) based on task type + data sensitivity + agent policy. It does NOT
call any external model. Sensitive client/credit/funding/trading data never routes to public
cloud. Integrates with scripts/agent_policy.py.

    python3 scripts/model_router.py --self-test
"""
from __future__ import annotations

import json
import re
import sys
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent / "social"))
import agent_policy  # noqa: E402
from _supabase import get, insert  # noqa: E402

PREF = ["deterministic", "local_private", "manual", "free_public_cloud", "premium_cloud"]
REASONING_CLASSES = {"DETERMINISTIC", "LIGHT_REASONING", "STRONG_REASONING", "SPECIALIZED_EXECUTOR", "OFFLINE_EXPERIMENT"}
OPENROUTER_PROVIDER = "https://openrouter.ai/api/v1"
SENSITIVE = {"client_general", "client_credit", "client_funding", "trading_research", "internal_strategy", "unknown_sensitive"}

# sensitivity -> routing rule
RULES = {
    "secrets_or_credentials": {"block": True},
    "trading_execution": {"block": True},
    "deployment": {"approval_only": True},
    "social_publication": {"approval_only": True},
    "trading_research": {"allowed": ["deterministic", "manual", "local_private"]},
    "client_credit": {"allowed": ["deterministic", "local_private", "manual"]},
    "client_funding": {"allowed": ["deterministic", "local_private", "manual"]},
    "client_general": {"allowed": ["deterministic", "local_private"]},
    "internal_strategy": {"allowed": ["deterministic", "manual", "local_private"]},
    "public_research": {"allowed": ["deterministic", "free_public_cloud", "manual", "local_private"]},
    "unknown_sensitive": {"allowed": ["deterministic", "manual", "local_private"]},
}


def classify_task_type(text: str) -> str:
    t = (text or "").lower()
    if re.search(r"transcript", t): return "transcript_intake_review"
    if re.search(r"mac mini|run (this|it) on|local hardware|gpu|vram|benchmark", t): return "local_hardware_feasibility"
    if re.search(r"build (a )?prompt|prompt packet|implement|write code|refactor", t): return "implementation"
    if re.search(r"trad(e|ing)|strategy|backtest", t): return "trading_research"
    if re.search(r"seo|keyword", t): return "seo_analysis"
    if re.search(r"creativ|campaign|content|caption", t): return "creative"
    if re.search(r"summari|review|what do you think|analy|trend", t): return "research_summary"
    return "general"


def classify_sensitivity(text: str, metadata: dict | None = None) -> str:
    t = (text or "").lower()
    if re.search(r"secret|api[_ ]?key|service_role|access[_ ]?token|\btoken\b|password|credential|\.env|_key\b", t): return "secrets_or_credentials"
    if (re.search(r"trad(e|ing)", t) and re.search(r"\b(execute|place|live|funded|real|buy|sell)\b", t)) or re.search(r"\bgo live\b", t):
        return "trading_execution"
    if re.search(r"deploy|ship to prod|restart (the )?server", t): return "deployment"
    if re.search(r"\bpublish\b|post to (facebook|instagram)", t) and not re.search(r"do not|don'?t", t): return "social_publication"
    if re.search(r"credit (report|data|score|repair)", t): return "client_credit"
    if re.search(r"funding|loan|lender|bank statement", t) and re.search(r"client|customer|uploaded|their", t): return "client_funding"
    if re.search(r"client|customer", t): return "client_general"
    if re.search(r"trad(e|ing)|strategy|backtest", t): return "trading_research"
    if re.search(r"public|trend|news|repo|youtube|article", t): return "public_research"
    if re.search(r"strategy|nexus|internal|roadmap", t): return "internal_strategy"
    return "unknown_sensitive"


def requested_public_cloud(text: str) -> bool:
    return bool(re.search(r"free (cloud|model)|public cloud|openrouter|send .* to .* cloud", (text or "").lower()))


def list_available_routes() -> list[dict]:
    st, rows = get("model_routes", "select=*&order=priority.asc")
    return rows if isinstance(rows, list) else []


def _decision(decision, route_key, reason, requires_approval=False):
    return {"decision": decision, "selected_route_key": route_key, "reason": reason,
            "requires_approval": requires_approval}


def choose_route(agent_key: str, task_type: str, sensitivity: str, metadata: dict | None = None) -> dict:
    md = metadata or {}
    rule = RULES.get(sensitivity, RULES["unknown_sensitive"])

    if rule.get("block"):
        return _decision("blocked", "blocked_sensitive_public_cloud" if sensitivity == "secrets_or_credentials" else None,
                         f"{sensitivity} is never routed to a model", requires_approval=True)
    if rule.get("approval_only"):
        return _decision("approval_required", None,
                         f"{sensitivity} requires Ray approval; no model execution", requires_approval=True)

    # explicit "send sensitive data to public/free cloud" → hard block
    if md.get("requested_public_cloud") and sensitivity in SENSITIVE and sensitivity != "public_research":
        return _decision("blocked", "blocked_sensitive_public_cloud",
                         f"sensitive data ({sensitivity}) cannot go to a public/free cloud route", requires_approval=True)

    allowed = rule.get("allowed", [])
    routes = [r for r in list_available_routes() if r.get("active") and r.get("route_type") in allowed]
    if sensitivity in SENSITIVE:
        # sensitive data: never public cloud; route must allow sensitive data or be deterministic/local/manual
        routes = [r for r in routes if r.get("route_type") != "free_public_cloud"
                  and (r.get("route_type") in ("deterministic", "local_private", "manual") or r.get("sensitive_data_allowed"))]

    routes.sort(key=lambda r: (PREF.index(r["route_type"]) if r["route_type"] in PREF else 99, r.get("priority", 100)))
    if not routes:
        return _decision("blocked", None, "no safe active route available for this sensitivity", requires_approval=True)

    sel = routes[0]
    if sel["route_type"] == "free_public_cloud" and not sel.get("external_call_allowed"):
        return _decision("external_disabled", sel["route_key"],
                         "eligible public route, but external model calls are disabled by default", requires_approval=True)
    return _decision("selected", sel["route_key"],
                     f"{sensitivity} → {sel['route_type']} ({sel['route_key']})",
                     requires_approval=bool(sel.get("requires_approval")))


def classify_workflow_step(*, deterministic: bool = False, reasoning_class: str | None = None) -> str:
    """Workflow-first policy: known transitions and reads never need a model."""
    if deterministic:
        return "DETERMINISTIC"
    value = str(reasoning_class or "LIGHT_REASONING").upper()
    if value not in REASONING_CLASSES:
        raise ValueError("UNKNOWN_REASONING_CLASS")
    return value


def _reasoning_metadata_limits(reasoning_class: str) -> dict[str, int]:
    """Local accounting estimate for the bounded subscription adapter."""
    return {"estimated_tokens": 2000 if reasoning_class == "LIGHT_REASONING" else 8000}


def creative_model_route(task_class: str) -> dict[str, Any]:
    """Compatibility shape for Creative, backed by the canonical registry."""
    decision = select_reasoning_model(agent_key="nexus_creative", task_type="creative",
        sensitivity="internal_strategy", reasoning_class="STRONG_REASONING", allow_free_tier=False)
    if decision.get("decision") != "selected":
        return {"status": "BLOCKED", "primary_spec": None, "fallback_spec": None,
            "primary_model": None, "reason": decision.get("reason")}
    route = decision["route"]
    provider = decision.get("provider")
    return {"status": "AVAILABLE", "primary_spec": {"provider": provider, "model": decision.get("model")},
        "fallback_spec": None, "primary_model": decision.get("model"), "route_key": route.get("route_key"),
        "reasoning_class": decision.get("reasoning_class"), "task_class": task_class}


def _openrouter_json(path: str, key: str, *, timeout: int = 20) -> dict[str, Any]:
    request = urllib.request.Request(OPENROUTER_PROVIDER + path,
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("OPENROUTER_INVALID_RESPONSE")
    return value.get("data", value)


def openrouter_account_state(*, key: str | None = None) -> dict[str, Any]:
    """Read provider-reported free request quota and account usage; never returns secrets."""
    token = (key or os.environ.get("OPENROUTER_API_KEY", "")).strip()
    if not token:
        return {"status": "AUTH_REQUIRED", "authenticated": False}
    try:
        info = _openrouter_json("/key", token)
        quota = info.get("free_model_daily_requests") or {}
        return {"status": "AVAILABLE", "authenticated": True,
            "is_free_tier": bool(info.get("is_free_tier")),
            "free_requests_used": quota.get("used"),
            "free_requests_limit": quota.get("limit"),
            "free_requests_remaining": quota.get("remaining"),
            "account_limit": info.get("limit"), "account_limit_remaining": info.get("limit_remaining"),
            "usage_daily": info.get("usage_daily"), "usage_monthly": info.get("usage_monthly"),
            "effective_budget": info.get("effective_budget"),
            "funded_balance_may_be_used": False}
    except Exception as exc:
        return {"status": "PROVIDER_UNAVAILABLE", "authenticated": False,
            "error_type": type(exc).__name__, "error": str(exc)[:160]}


def select_reasoning_model(*, agent_key: str, task_type: str, sensitivity: str,
                           reasoning_class: str, allow_free_tier: bool = True,
                           canary_route_key: str | None = None) -> dict[str, Any]:
    """Select only a registered, production-enabled model route for reasoning.

    A deterministic workflow step exits before model selection. This adapter
    extends the pre-existing model_routes registry and remains deny by default.
    """
    cls = classify_workflow_step(reasoning_class=reasoning_class)
    if cls == "DETERMINISTIC":
        return {"decision": "NO_MODEL", "reasoning_class": cls, "route": None, "model": None}
    if cls == "OFFLINE_EXPERIMENT":
        return _decision("blocked", None, "offline experiment providers require an explicit experiment executor")
    if cls == "SPECIALIZED_EXECUTOR":
        return {"decision": "SPECIALIZED_EXECUTOR", "reasoning_class": cls, "route": None, "model": None}
    registered = list_available_routes()
    routes = [r for r in registered if r.get("active")
        and r.get("route_type") == "free_public_cloud"
        and r.get("provider_key") == "openrouter"
        and r.get("model_key") and str(r.get("model_key")).endswith(":free")
        and r.get("external_call_allowed")]
    routes = [r for r in routes if r.get("task_type") in {task_type, "reasoning", "*"}]
    routes = [r for r in routes if cls in (r.get("metadata") or {}).get("reasoning_classes", [])
              and ((r.get("metadata") or {}).get("production_verified") is True
                   or (canary_route_key and r.get("route_key") == canary_route_key and cls == "LIGHT_REASONING"))]
    if cls == "LIGHT_REASONING" and allow_free_tier and sensitivity == "public_research" and routes:
        routes.sort(key=lambda r: (int(r.get("priority", 100)), str(r.get("route_key"))))
        route = routes[0]
        return {"decision": "selected", "reasoning_class": cls, "route": route,
            "model": route["model_key"], "provider": "openrouter", "cost_class": "ZERO_FREE_TIER",
            "reason": f"{cls} uses verified free-tier route {route['route_key']}"}

    # Existing subscription routes are first-class canonical routes. They are
    # selected only when the route record asserts this reasoning class and data
    # boundary; their adapter still owns the existing provider governor.
    eligible = [r for r in registered if r.get("active") and r.get("route_type") == "existing_budget"
        and r.get("external_call_allowed")
        and r.get("task_type") in {task_type, "reasoning", "*"}
        and cls in (r.get("metadata") or {}).get("reasoning_classes", [])
        and sensitivity in (r.get("metadata") or {}).get("allowed_sensitivities", [])]
    eligible.sort(key=lambda r: (int(r.get("priority", 100)), str(r.get("route_key"))))
    if eligible:
        route = eligible[0]
        return {"decision": "selected", "reasoning_class": cls, "route": route,
            "model": route.get("model_key"), "provider": route.get("provider_key"),
            "cost_class": "EXISTING_BUDGET",
            "reason": f"{cls} uses governed existing-budget route {route['route_key']}"}
    if sensitivity != "public_research":
        return _decision("blocked", None, f"no approved reasoning route for sensitivity={sensitivity}", True)
    if not allow_free_tier:
        return _decision("blocked", None, "free-tier OpenRouter route is not permitted", True)
    return _decision("blocked", None, f"no production-verified {cls} route", True)


def execute_reasoning(*, agent_key: str, task_type: str, sensitivity: str,
                      reasoning_class: str, payload: dict[str, Any], operation: Callable,
                      max_tokens: int = 1200, purpose: str | None = None,
                      canary_route_key: str | None = None,
                      timeout_seconds: int | None = None) -> dict[str, Any]:
    """Call one registered route. Provider-specific adapters retain their own governance boundary."""
    route = select_reasoning_model(agent_key=agent_key, task_type=task_type,
        sensitivity=sensitivity, reasoning_class=reasoning_class, canary_route_key=canary_route_key)
    if route.get("decision") != "selected":
        raise RuntimeError("MODEL_ROUTE_UNAVAILABLE:" + str(route.get("reason") or route.get("decision")))
    if route.get("cost_class") == "EXISTING_BUDGET":
        if route.get("provider") != "openai-codex" or route.get("model") != "gpt-5.6-terra":
            raise RuntimeError("UNSUPPORTED_EXISTING_BUDGET_ADAPTER")
        job_id = os.environ.get("NEXUS_DURABLE_JOB_ID")
        if not job_id or not os.environ.get("NEXUS_CORRELATION_ID") or not os.environ.get("NEXUS_DEPARTMENT"):
            raise RuntimeError("DURABLE_MODEL_CALL_CONTEXT_REQUIRED")
        messages = payload.get("messages") if isinstance(payload.get("messages"), list) else []
        prompt = "\n\n".join(f"{m.get('role','user').upper()}: {m.get('content','')}" for m in messages if isinstance(m, dict))
        if not prompt.strip():
            prompt = json.dumps(payload, ensure_ascii=False)
        from nexus_agent_platform.bridge.oracle_hermes_cli import run_oracle_hermes
        selected_model = route["model"]
        if agent_key == "nexus_research_room_advisor":
            from nexus_agent_platform.bridge.oracle_hermes_cli import RESEARCH_ROOM_MODEL
            selected_model = RESEARCH_ROOM_MODEL
        started = time.monotonic()
        route_timeout = min(180, max(30,
            int((route["route"].get("metadata") or {}).get("timeout_seconds", 120))))
        # Callers may request a shorter bounded deadline. A longer deadline is
        # still capped by the selected route's registered timeout.
        timeout = min(route_timeout, max(30, int(timeout_seconds))) if timeout_seconds is not None else (
            min(35, route_timeout) if reasoning_class == "LIGHT_REASONING" else route_timeout)
        result = run_oracle_hermes(prompt[:24000], f"router:{job_id}:{task_type}"[:160],
            timeout_seconds=timeout,
            request_id=os.environ.get("NEXUS_CORRELATION_ID"), structured_task=True,
            reasoning_class=reasoning_class,
            stateless_task=(agent_key == "nexus_research_room_advisor"),
            governor_purpose=(f"model:{task_type}:{purpose or agent_key}:attempt:"
                f"{os.environ.get('NEXUS_JOB_ATTEMPT_COUNT', '0')}" ))
        if result.status != "SUCCEEDED" or not result.response:
            raise RuntimeError("CODEX_SUBSCRIPTION_ROUTE_FAILED:" + str(result.error or result.status))
        data = {"choices": [{"message": {"content": result.response}, "finish_reason": "stop"}],
                "model": selected_model, "provider": route["provider"], "usage": result.usage or {}}
        limits = _reasoning_metadata_limits(reasoning_class)
        metadata = {"workflow_id": os.environ.get("NEXUS_WORKFLOW_ID"), "job_id": job_id,
            "step_id": os.environ.get("NEXUS_STEP_ID", task_type), "reasoning_class": reasoning_class,
            "execution_class": reasoning_class, "model_call_required": True,
            "model_call_reason": purpose or f"judgment_required:{task_type}",
            "selected_provider": route["provider"], "selected_model": selected_model,
            "cost_class": "EXISTING_BUDGET", "estimated_cost": 0,
            "estimated_usage": limits["estimated_tokens"], "actual_usage": result.usage or None,
            "resource_decision": "ALLOW_GOVERNED",
            "fallback_used": False, "latency_ms": result.latency_ms or round((time.monotonic()-started)*1000, 2), "status": "SUCCEEDED"}
        _persist_model_usage(route["route"], metadata)
        return {"result": data, "provider": route["provider"], "model": selected_model,
            "reasoning_class": reasoning_class, "cost_class": "EXISTING_BUDGET", "estimated_cost": 0,
            "funded_balance_used": False, "latency_ms": metadata["latency_ms"],
            "route_key": route["route"]["route_key"], "execution_metadata": metadata}

    model = str(route["model"])
    token = os.environ.get("OPENROUTER_API_KEY", "").strip()
    state = openrouter_account_state(key=token)
    if state.get("status") != "AVAILABLE":
        raise RuntimeError("OPENROUTER_ACCOUNT_UNAVAILABLE:" + str(state.get("error_type") or state.get("status")))
    remaining = state.get("free_requests_remaining")
    if remaining is None or int(remaining) < 1:
        raise RuntimeError("OPENROUTER_FREE_TIER_LIMIT_REACHED")
    # Verify current catalog price before any completion request. Only an exact
    # :free model with zero input/output prices can pass this gate.
    catalog = _openrouter_json("/models", token)
    entries = catalog if isinstance(catalog, list) else []
    model_row = next((item for item in entries if item.get("id") == model), None)
    price = (model_row or {}).get("pricing") or {}
    if (not model_row or not model.endswith(":free")
            or str(price.get("prompt")) not in {"0", "0.0"}
            or str(price.get("completion")) not in {"0", "0.0"}):
        raise RuntimeError("OPENROUTER_MODEL_NOT_VERIFIED_FREE")
    job_id = os.environ.get("NEXUS_DURABLE_JOB_ID")
    correlation_id = os.environ.get("NEXUS_CORRELATION_ID")
    if not job_id or not correlation_id:
        raise RuntimeError("DURABLE_MODEL_CALL_CONTEXT_REQUIRED")
    from nexus_agent_platform.provider_enforcement import execute as governed_execute
    request_payload = dict(payload)
    request_payload["model"] = model
    request_payload["max_tokens"] = min(max(1, int(max_tokens)), 1600)
    request_payload["provider"] = {"allow_fallbacks": False}
    request_payload["usage"] = {"include": True}
    supported = set((model_row or {}).get("supported_parameters") or [])
    if "response_format" in supported and "response_format" not in request_payload:
        request_payload["response_format"] = {"type": "json_object"}
    # Do not impose a reasoning-token mode on every provider model. Several
    # free reasoning models consume their completion window internally and
    # return an empty/truncated visible answer. Per-model controls belong in
    # the registered route metadata when a workflow has verified them.
    reasoning_options = (route["route"].get("metadata") or {}).get("reasoning_options")
    if "reasoning" in supported and isinstance(reasoning_options, dict):
        request_payload["reasoning"] = dict(reasoning_options)
    start = time.monotonic()
    result = governed_execute("OPENROUTER", "free_model_inference", "MODEL_INFERENCE",
        {"requests": 1, "operations": 1, "api_calls": 1, "tokens": request_payload["max_tokens"],
         "bytes": len(json.dumps(request_payload)), "cost": 0, "billable": False,
         "budget_period": "DAILY"},
        lambda: operation(request_payload, token), job_id=job_id,
        job_type=os.environ.get("NEXUS_JOB_TYPE", task_type), correlation_id=correlation_id,
        purpose=purpose or f"{agent_key}:{reasoning_class}:{model}",
        actual_usage=lambda result: {"requests": 1, "operations": 1, "api_calls": 1,
            "tokens": int(((result or {}).get("usage") or {}).get("total_tokens") or request_payload["max_tokens"]),
            "bytes": len(json.dumps(result)), "cost": 0, "free_tier_requests": 1})
    metadata = {"workflow_id": os.environ.get("NEXUS_WORKFLOW_ID"), "job_id": job_id,
        "step_id": os.environ.get("NEXUS_STEP_ID", task_type), "reasoning_class": reasoning_class,
        "execution_class": reasoning_class, "model_call_required": True,
        "model_call_reason": purpose or f"judgment_required:{task_type}",
        "selected_provider": "openrouter", "selected_model": model, "cost_class": "ZERO_FREE_TIER",
        "free_requests_remaining_before": remaining, "estimated_usage": request_payload["max_tokens"],
        "actual_usage": (result.get("usage") or {}) if isinstance(result, dict) else None,
        "resource_decision": "ALLOW_GOVERNED", "fallback_used": False,
        "latency_ms": round((time.monotonic()-start)*1000, 2), "status": "SUCCEEDED"}
    _persist_model_usage(route["route"], metadata)
    return {"result": result, "provider": "openrouter", "model": model,
        "reasoning_class": reasoning_class, "cost_class": "ZERO_FREE_TIER",
        "estimated_cost": 0, "free_requests_remaining_before": remaining,
        "funded_balance_used": False, "latency_ms": round((time.monotonic()-start)*1000, 2),
        "route_key": route["route"]["route_key"], "execution_metadata": metadata}


def _persist_model_usage(route: dict[str, Any], metadata: dict[str, Any]) -> None:
    """Persist route metadata without prompts or response content."""
    try:
        insert("model_usage_logs", {"route_key": route.get("route_key"),
            "provider_key": route.get("provider_key"), "task_type": metadata.get("reasoning_class"),
            "status": metadata.get("status", "UNKNOWN"), "fallback_used": metadata.get("fallback_used", False),
            "latency_ms": int(metadata.get("latency_ms") or 0),
            "token_estimate": metadata.get("estimated_usage"), "cost_estimate": metadata.get("estimated_cost", 0),
            "metadata": metadata})
    except Exception:
        # Usage telemetry must not replace the provider's authoritative result;
        # the resource governor still records the actual governed invocation.
        return


def create_route_decision(agent_key, task_type, sensitivity, dec: dict, job_id=None, approval_id=None) -> str | None:
    st, row = insert("model_route_decisions", {
        "agent_key": agent_key, "task_type": task_type, "sensitivity": sensitivity,
        "selected_route_key": dec.get("selected_route_key"), "decision": dec["decision"],
        "reason": dec["reason"], "requires_approval": dec.get("requires_approval", False),
        "job_id": job_id, "approval_id": approval_id,
    })
    return row[0]["id"] if isinstance(row, list) and row else None


def explain_route_decision(dec: dict) -> str:
    return f"decision={dec['decision']} route={dec.get('selected_route_key')} approval={dec['requires_approval']} — {dec['reason']}"


def get_agent_policy(agent_key: str):
    return agent_policy.load_agent(agent_key)


def _self_test() -> int:
    cases = [
        ("Review this public AI trend and summarize if Nexus should care.", False),
        ("A GoClear client uploaded credit report data. What should we do?", False),
        ("Send this sensitive credit data to a free cloud model.", True),
        ("Publish this to Facebook now.", False),
        ("Print the SUPABASE_SERVICE_ROLE_KEY.", False),
        ("Execute a live EURUSD trade.", False),
    ]
    for prompt, _ in cases:
        tt = classify_task_type(prompt)
        sens = classify_sensitivity(prompt)
        dec = choose_route("hermes_advisor", tt, sens, {"requested_public_cloud": requested_public_cloud(prompt)})
        print(f"- {prompt[:54]!r:56} sens={sens:22} {explain_route_decision(dec)}")
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        raise SystemExit(_self_test())
    print(json.dumps(list_available_routes(), indent=2)[:400])
