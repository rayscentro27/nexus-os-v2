from nexus_agent_platform import access_resolver


def test_remote_voice_access_does_not_require_local_secret(monkeypatch):
    monkeypatch.setattr(access_resolver, "_netlify_env_names", lambda: {
        "CF_ACCESS_CLIENT_ID", "CF_ACCESS_CLIENT_SECRET", "VOICE_ACCESS_ORIGIN"
    })
    monkeypatch.setattr(access_resolver, "resolve", lambda *args, **kwargs: {
        "source_found": [], "source_classification": "MISSING"
    })
    result = access_resolver.resolve_access("voice.transport", environ={})
    assert result["auth_state"] == "AVAILABLE_REMOTE_NETLIFY"
    assert result["execution_location"] == "NETLIFY_SERVER"
    assert result["local_secret_required"] is False
    assert result["resolution"] == "USE_NETLIFY_RELAY"
    assert result["values_included"] is False


def test_remote_groq_access_is_not_global_missing(monkeypatch):
    monkeypatch.setattr(access_resolver, "_netlify_env_names", lambda: {"GROQ_API_KEY"})
    monkeypatch.setattr(access_resolver, "resolve", lambda *args, **kwargs: {
        "source_found": [], "source_classification": "MISSING"
    })
    result = access_resolver.resolve_access("model.groq", environ={})
    assert result["auth_state"] == "AVAILABLE_REMOTE_NETLIFY"
    assert result["human_action_required"] is False


def test_unknown_capability_is_discovery_incomplete():
    result = access_resolver.resolve_access("unknown.capability", environ={})
    assert result["auth_state"] == "DISCOVERY_INCOMPLETE"
    assert result["values_included"] is False
