def test_model_request_is_allowlisted_and_not_authoritative():
    from nexus_agent_platform.nova_capability_broker import validate_model_request
    ok = validate_model_request({"capability": "PUBLIC_WEB_SEARCH", "arguments": {"query": "x"}})
    assert ok["status"] == "validated"
    assert ok["capability"] == "public_web_search"
    denied = validate_model_request({"capability": "NEXUS_DIRECT_EXECUTION", "arguments": {}})
    assert denied["status"] == "rejected"


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
