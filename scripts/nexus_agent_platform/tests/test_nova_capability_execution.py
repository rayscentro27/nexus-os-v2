def test_model_request_is_allowlisted_and_not_authoritative():
    from nexus_agent_platform.nova_capability_broker import validate_model_request
    ok = validate_model_request({"capability": "PUBLIC_WEB_SEARCH", "arguments": {"query": "x"}})
    assert ok["status"] == "validated"
    assert ok["capability"] == "public_web_search"
    denied = validate_model_request({"capability": "NEXUS_DIRECT_EXECUTION", "arguments": {}})
    assert denied["status"] == "rejected"
    nexus = validate_model_request({"capability": "NEXUS_CAPABILITY_MAP", "arguments": {}})
    assert nexus["status"] == "validated"
    assert nexus["capability"] == "get_capability_registry"


def test_alpha_model_request_can_use_contextual_referent():
    from nexus_agent_platform.nova_capability_broker import validate_model_request
    result = validate_model_request({
        "capability": "ALPHA_RESEARCH",
        "arguments": {"referent": "the prior recommendation about onboarding"},
    })
    assert result["status"] == "validated"
    assert result["arguments"]["objective"] == "the prior recommendation about onboarding"


def test_model_selected_web_resource_executes_and_returns_for_continuation(monkeypatch, tmp_path):
    from nexus_agent_platform.agents import nova
    from nexus_agent_platform.adapters.state_adapter import AgentState

    calls = []

    async def fake_model(messages, chat_id, purpose="final_generation"):
        calls.append(purpose)
        if len(calls) == 1:
            return {"content": '{"nova_capability_request":{"capability":"PUBLIC_WEB_SEARCH","arguments":{"query":"credit repair affiliate programs"}}}', "model": "test"}
        return {"content": "I reviewed the returned public evidence and can compare the options.", "model": "test"}

    def fake_execute(agent_id, capability, arguments, **kwargs):
        assert agent_id == nova.AGENT_ID
        assert capability == "public_web_search"
        assert arguments["query"] == "credit repair affiliate programs"
        return {"status": "success", "data": {"results": [{"title": "source", "url": "https://example.com"}]}, "provenance": {"provider": "test-free", "freshness": "live"}}

    monkeypatch.setattr(nova, "_call_model", fake_model)
    import nexus_agent_platform.capabilities.shared as shared
    monkeypatch.setattr(shared, "execute_shared_capability", fake_execute)
    monkeypatch.setattr(nova, "MEMORY_DIR", str(tmp_path))
    state = AgentState(user_message="Find current affiliate opportunities", metadata={"chat_id": 87654321, "model_messages": [{"role": "system", "content": nova.SOUL}]})
    result = nova._generate_response(state)
    assert result.metadata["model_selected_capability"]["capability"] == "public_web_search"
    assert result.metadata["capability_invocation_attempted"] is True
    assert result.metadata["capability_followup"] is True
    assert calls == ["final_generation", "capability_followup"]


def test_model_request_parser_accepts_only_strict_envelope():
    from nexus_agent_platform.agents.nova import _extract_model_capability_request
    assert _extract_model_capability_request('{"nova_capability_request":{"capability":"PUBLIC_WEB_SEARCH","arguments":{"query":"x"}}}')
    assert _extract_model_capability_request("I cannot search") is None


def test_public_retrieval_is_read_only_and_bounded(monkeypatch):
    from nexus_agent_platform.capabilities import shared

    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, limit): return b"<html>real public content</html>"

    monkeypatch.setattr(shared.urllib.request, "urlopen", lambda *args, **kwargs: Response())
    result = shared.execute_shared_capability("hermes_nova", "public_web_retrieval", {"url": "https://example.com"})
    assert result["status"] == "success"
    assert result["data"]["content"] == "<html>real public content</html>"
    assert result["provenance"]["read_only"] is True


def test_alpha_execution_produces_artifact(monkeypatch, tmp_path):
    from nexus_agent_platform import alpha_research

    from nexus_agent_platform.phase15 import live_research
    monkeypatch.setattr(live_research, "_load_web_search", lambda: (lambda query, max_results=6: {"status": "ok", "provider": "test-free", "results": [{"title": "source", "url": "https://example.com", "snippet": "evidence"}]}, None))
    result = alpha_research.execute_alpha_request(objective="Investigate GoClear onboarding improvements", runtime_root=tmp_path)
    assert result["execution"]["executed"] is True
    assert result["receipt"]["research_job_id"] == result["job"]["research_job_id"]
    assert (tmp_path / f"{result['job']['research_job_id']}.json").exists()
