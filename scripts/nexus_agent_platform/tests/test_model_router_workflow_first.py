import json

import model_router


def test_deterministic_workflow_steps_do_not_select_a_model():
    result = model_router.classify_workflow_step(deterministic=True, reasoning_class="STRONG_REASONING")
    assert result == "DETERMINISTIC"
    route = model_router.select_reasoning_model(agent_key="nexus", task_type="research",
        sensitivity="public_research", reasoning_class=result)
    assert route["decision"] == "NO_MODEL"


def test_free_model_is_light_only_and_requires_live_verification(monkeypatch):
    monkeypatch.setattr(model_router, "list_available_routes", lambda: [{
        "route_key": "openrouter_free_alpha", "task_type": "research", "provider_key": "openrouter",
        "model_key": "nvidia/nemotron-3-super-120b-a12b:free", "route_type": "free_public_cloud",
        "active": True, "external_call_allowed": True, "metadata": {"reasoning_classes": ["LIGHT_REASONING"], "production_verified": True},
    }])
    decision = model_router.select_reasoning_model(agent_key="alpha", task_type="research",
        sensitivity="public_research", reasoning_class="LIGHT_REASONING")
    assert decision["decision"] == "selected"
    assert decision["cost_class"] == "ZERO_FREE_TIER"
    assert decision["model"].endswith(":free")
    denied = model_router.select_reasoning_model(agent_key="alpha", task_type="research",
        sensitivity="public_research", reasoning_class="STRONG_REASONING")
    assert denied["decision"] == "blocked"


def test_free_execution_disables_paid_fallback_and_governs_zero_cost(monkeypatch):
    monkeypatch.setattr(model_router, "list_available_routes", lambda: [{
        "route_key": "openrouter_free_alpha", "task_type": "research", "provider_key": "openrouter",
        "model_key": "nvidia/nemotron-3-super-120b-a12b:free", "route_type": "free_public_cloud",
        "active": True, "external_call_allowed": True, "metadata": {"reasoning_classes": ["LIGHT_REASONING"], "production_verified": True},
    }])
    monkeypatch.setattr(model_router, "openrouter_account_state", lambda **_: {
        "status": "AVAILABLE", "free_requests_remaining": 50})
    monkeypatch.setattr(model_router, "_openrouter_json", lambda path, key: (
        [{"id": "nvidia/nemotron-3-super-120b-a12b:free", "pricing": {"prompt": "0", "completion": "0"},
          "supported_parameters": ["response_format"]}] if path == "/models" else {}))
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID", "job-test")
    monkeypatch.setenv("NEXUS_CORRELATION_ID", "mission-test")
    monkeypatch.setenv("NEXUS_DEPARTMENT", "ALPHA")
    monkeypatch.setenv("NEXUS_JOB_TYPE", "NEXUS_DEPARTMENT_QUERY")

    from nexus_agent_platform import provider_enforcement
    captured = {}
    def governed(provider, service, action, estimate, operation, **kwargs):
        captured.update(provider=provider, service=service, action=action, estimate=estimate, kwargs=kwargs)
        return operation()
    monkeypatch.setattr(provider_enforcement, "execute", governed)

    def invoke(payload, key):
        captured["payload"] = payload
        return {"choices": [{"message": {"content": '{"decision":"RESEARCH_MORE"}'}}], "usage": {"total_tokens": 12}}

    result = model_router.execute_reasoning(agent_key="alpha", task_type="research", sensitivity="public_research",
        reasoning_class="LIGHT_REASONING", payload={"messages": []}, operation=invoke, max_tokens=1400)
    assert result["cost_class"] == "ZERO_FREE_TIER"
    assert result["funded_balance_used"] is False
    assert captured["provider"] == "OPENROUTER"
    assert captured["estimate"]["cost"] == 0
    assert captured["estimate"]["billable"] is False
    assert captured["payload"]["provider"] == {"allow_fallbacks": False}
    assert captured["payload"]["response_format"] == {"type": "json_object"}


def test_existing_budget_codex_route_is_canonical_strong_fallback(monkeypatch):
    monkeypatch.setattr(model_router, "list_available_routes", lambda: [{
        "route_key": "openai_codex_subscription_reasoning", "task_type": "reasoning",
        "provider_key": "openai-codex", "model_key": "gpt-5.5", "route_type": "existing_budget",
        "active": True, "external_call_allowed": True, "priority": 1,
        "metadata": {"reasoning_classes": ["LIGHT_REASONING", "STRONG_REASONING"],
            "allowed_sensitivities": ["public_research", "internal_strategy", "unknown_sensitive"]},
    }])
    route = model_router.select_reasoning_model(agent_key="alpha", task_type="research",
        sensitivity="public_research", reasoning_class="STRONG_REASONING")
    assert route["decision"] == "selected"
    assert route["provider"] == "openai-codex"
    assert route["model"] == "gpt-5.5"
    assert route["cost_class"] == "EXISTING_BUDGET"


def test_light_reasoning_call_deadline_is_bounded_by_registered_route(monkeypatch):
    from nexus_agent_platform.bridge import oracle_hermes_cli
    monkeypatch.setattr(model_router, "list_available_routes", lambda: [{
        "route_key": "openai_codex_subscription_reasoning", "task_type": "reasoning",
        "provider_key": "openai-codex", "model_key": "gpt-5.5", "route_type": "existing_budget",
        "active": True, "external_call_allowed": True, "priority": 1,
        "metadata": {"reasoning_classes": ["LIGHT_REASONING"],
            "allowed_sensitivities": ["internal_strategy"], "timeout_seconds": 120},
    }])
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID", "job-needle")
    monkeypatch.setenv("NEXUS_CORRELATION_ID", "corr-needle")
    monkeypatch.setenv("NEXUS_DEPARTMENT", "RESEARCH")
    monkeypatch.setenv("NEXUS_JOB_ATTEMPT_COUNT", "0")
    seen = {}
    class Result:
        status = "SUCCEEDED"
        response = '{"ok":true}'
        error = None
    def invoke(prompt, session_id, **kwargs):
        seen.update(kwargs)
        return Result()
    monkeypatch.setattr(oracle_hermes_cli, "run_oracle_hermes", invoke)
    monkeypatch.setattr(model_router, "_persist_model_usage", lambda *args, **kwargs: None)
    result = model_router.execute_reasoning(agent_key="nexus_needle", task_type="research_readiness",
        sensitivity="internal_strategy", reasoning_class="LIGHT_REASONING",
        payload={"messages":[{"role":"user","content":"bounded review"}]},
        operation=lambda *_: None, timeout_seconds=90)
    assert result["provider"] == "openai-codex"
    assert result["cost_class"] == "EXISTING_BUDGET"
    assert seen["timeout_seconds"] == 90
    assert seen["governor_purpose"].endswith("attempt:0")
