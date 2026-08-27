import json
from pathlib import Path

from nexus_agent_platform.credential_control_plane import generate_credential_display_name, resolve
from nexus_agent_platform.machine_profile import evaluate_execution_target

def test_brave_legacy_aliases_share_one_identity_and_canonical_wins():
    record = resolve("credential.brave.web_search.prod.v1", environ={"BRAVE_API_KEY":"old", "BRAVE_SEARCH_API_KEY":"new", "NEXUS_BRAVE_WEB_SEARCH_API_KEY":"canonical"})
    assert record["credential_id"] == "credential.brave.web_search.prod.v1"
    assert record["components"]["api_key"]["selected"]["alias"] == "NEXUS_BRAVE_WEB_SEARCH_API_KEY"

def test_display_name_is_deterministic_and_safe():
    name = generate_credential_display_name(provider="Google", purpose="Workspace", environment="prod")
    assert name == "nexus-prod-google-workspace-macmini-v1"
    assert name == generate_credential_display_name(provider="Google", purpose="Workspace", environment="prod")
    assert len(name) < 128 and name.replace("-", "").isalnum()

def test_missing_credential_is_exact_and_redacted():
    record = resolve("credential.anthropic.models.prod.v1", environ={})
    assert record["result"] == "MISSING"
    assert "api_key" in record["components"]
    assert "values_included" in record and record["values_included"] is False
    assert "old" not in json.dumps(record)

def test_machine_profile_selects_healthy_alternative_runtime():
    profile = {"python":{"interpreters":[{"executable":"python3.14","version":"3.14.5","ssl_import":"BROKEN"},{"executable":"python3.11","version":"3.11.15","ssl_import":"HEALTHY"}]},"browser":{"playwright_package":True}}
    result = evaluate_execution_target({"ssl":True}, profile)
    assert result["decision"] == "LOCAL_ALTERNATIVE_RUNTIME"
    assert result["runtime"] == "python3.11"
