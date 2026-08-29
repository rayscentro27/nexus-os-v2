import json
from pathlib import Path

from nexus_agent_platform.credential_control_plane import generate_credential_display_name, resolve
from nexus_agent_platform import credential_control_plane as cp
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

def test_keychain_store_status_read_round_trip_uses_same_record(monkeypatch):
    """The writer, status check, and reader must address one record identity."""
    monkeypatch.setattr(cp.sys, "platform", "darwin")
    records = {}
    secret = "round-trip-fixture"

    class Result:
        def __init__(self, returncode=0, stdout=""):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = ""

    def fake_security(args, **kwargs):
        service = args[args.index("-s") + 1]
        account = args[args.index("-a") + 1]
        record = (service, account)
        if args[1] == "add-generic-password":
            records[record] = args[args.index("-w") + 1]
            return Result()
        if args[1] == "find-generic-password":
            return Result(stdout=records.get(record, "")) if record in records else Result(returncode=44)
        raise AssertionError(f"unexpected security operation: {args[1]}")

    monkeypatch.setattr(cp.subprocess, "run", fake_security)
    credential_id = "credential.google.workspace.prod.v1"
    component = "refresh_token"

    stored = cp.store_keychain(credential_id, component, secret)
    assert stored["status"] == "STORED"
    assert cp.keychain_status(credential_id, component) == "CONFIGURED"
    assert cp._keychain_value(credential_id, component) == secret
    assert records.keys() == {("nexus/credential.google.workspace.prod.v1", "refresh_token")}
    assert secret not in json.dumps(stored)

def test_machine_profile_selects_healthy_alternative_runtime():
    profile = {"python":{"interpreters":[{"executable":"python3.14","version":"3.14.5","ssl_import":"BROKEN"},{"executable":"python3.11","version":"3.11.15","ssl_import":"HEALTHY"}]},"browser":{"playwright_package":True}}
    result = evaluate_execution_target({"ssl":True}, profile)
    assert result["decision"] == "LOCAL_ALTERNATIVE_RUNTIME"
    assert result["runtime"] == "python3.11"
