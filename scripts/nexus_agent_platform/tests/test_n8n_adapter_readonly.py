from scripts.nexus_agent_platform import workflow_n8n_adapter as adapter


def test_n8n_inventory_exposes_workflow_metadata_but_not_parameters(monkeypatch):
    monkeypatch.setattr(adapter.agent_control_plane, "authorize", lambda **_: None)
    monkeypatch.setattr(adapter, "apply_to_process", lambda *_: {"components_applied": ["api_key"]})
    monkeypatch.setattr(adapter.os, "environ", {"N8N_API_KEY": "local-test"})

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
        def read(self, _):
            return b'{"data":[{"id":"w1","name":"canary","active":true,"nodes":[{"type":"n8n-nodes-base.webhook","parameters":{"path":"secret-path"}}]}]}'

    monkeypatch.setattr(adapter, "urlopen", lambda *_args, **_kwargs: Response())
    result = adapter.list_workflows_readonly()
    assert result["status"] == "PASS"
    assert result["workflows"][0]["id"] == "w1"
    assert result["workflows"][0]["node_types"] == ["webhook"]
    assert "parameters" not in str(result)
    assert "secret-path" not in str(result)
