import json
from pathlib import Path

from scripts.operations import nexus_hermes_telegram_worker as hermes


def test_configured_status_and_optional_integrations_are_grounded(monkeypatch):
    monkeypatch.setattr(hermes, "load_runtime_env", lambda: {"TELEGRAM_BOT_TOKEN": "token", "TELEGRAM_CHAT_ID": "42"})
    assert hermes.semantic_config() == {"token": "PRESENT", "authorized_chat": "PRESENT", "authorized_chat_count": 1}
    monkeypatch.setattr(hermes, "load_json", lambda path, default=None: {
        "core_autonomy_runtime": {"status": "HEALTHY"},
        "operator_health": "HEALTHY",
        "run_status": "NO_ACTION_REQUIRED",
    } if "live_runtime" in str(path) else (default or {}))
    response, metadata = hermes.handle_command("/status")
    assert "Core runtime:" in response
    assert metadata["outcome"] == "ANSWERED"


def test_natural_language_status_variants_use_the_canonical_handler(monkeypatch):
    calls = []
    monkeypatch.setattr(hermes, "status_response", lambda: calls.append(True) or "CANONICAL STATUS")
    variants = (
        "Nexus, give me the current system status.",
        "Nexus, what's the current system status?",
        "What's Nexus status?",
        "How is Nexus doing?",
        "What is running right now?",
        "Give me Nexus status.",
        "System status.",
        "What's the health of Nexus?",
    )
    for variant in variants:
        response, metadata = hermes.handle_command(variant)
        assert response == "CANONICAL STATUS"
        assert metadata["outcome"] == "ANSWERED"
    assert len(calls) == len(variants)


def test_status_matcher_does_not_capture_unrelated_requests():
    for text in ("give me a plan for today", "what is the status of the customer", "system status report draft", "how is Alpha doing?"):
        assert hermes.is_status_request(text) is False


def test_unauthorized_and_high_risk_commands_are_blocked():
    for command in ("charge the customer", "place a funded trade", "send an email to the client", "run shell command", "show me the runtime.env token"):
        response, metadata = hermes.handle_command(command)
        assert metadata["route"] == "NOT_AUTHORIZED"
        assert "can’t perform" in response


def test_work_order_creation_and_duplicate_suppression(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path / "governed"))
    first, first_meta = hermes.handle_command("/request prepare an internal recovery report")
    second, second_meta = hermes.handle_command("/request prepare an internal recovery report")
    assert "pending_approval" in first
    assert first_meta["status"] == "CREATED"
    assert second_meta["status"] == "DUPLICATE_SUPPRESSED"
    assert "Duplicate request suppressed" in second


def test_exact_remote_approval_mutation_only(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path / "governed"))
    first, metadata = hermes.handle_command("/request prepare an internal report")
    approval_id = metadata["approval_id"]
    response, result = hermes.handle_command(f"/approve {approval_id}")
    assert result["outcome"] == "APPROVAL_RECORDED"
    assert "approved" in response
    bad_response, bad = hermes.handle_command("/approve yes")
    assert bad["outcome"] == "REJECTED_INVALID_REFERENCE"


def test_no_updates_and_bot_authored_messages_are_safe(tmp_path, monkeypatch):
    monkeypatch.setattr(hermes, "load_runtime_env", lambda: {"TELEGRAM_BOT_TOKEN": "token", "TELEGRAM_CHAT_ID": "42"})
    monkeypatch.setattr(hermes, "OFFSET_PATH", tmp_path / "offset.json")
    monkeypatch.setattr(hermes, "RECEIPT_DIR", tmp_path / "receipts")
    def fake_api(token, method, params=None):
        if method == "getMe":
            return {"ok": True, "result": {"username": "NexusHermes27bot"}}
        if method == "getUpdates":
            return {"ok": True, "result": [
                {"update_id": 1, "message": {"from": {"is_bot": True}, "chat": {"id": 42}, "text": "/status"}},
                {"update_id": 2, "message": {"from": {}, "chat": {"id": 99}, "text": "/status"}},
            ]}
        raise AssertionError(method)
    result = hermes.run_once(dry_run=True, api=fake_api)
    assert result["outcome"] == "NO_AUTHORIZED_TEXT_UPDATES"
    assert result["unauthorized_rejected"] == 1
    assert json.loads((tmp_path / "offset.json").read_text())["last_update_id"] == 2


def test_authorized_status_routes_once_and_persists_receipt(tmp_path, monkeypatch):
    monkeypatch.setattr(hermes, "load_runtime_env", lambda: {"TELEGRAM_BOT_TOKEN": "token", "TELEGRAM_CHAT_ID": "42"})
    monkeypatch.setattr(hermes, "OFFSET_PATH", tmp_path / "offset.json")
    monkeypatch.setattr(hermes, "RECEIPT_DIR", tmp_path / "receipts")
    def fake_api(token, method, params=None):
        if method == "getMe":
            return {"ok": True, "result": {"username": "NexusHermes27bot"}}
        if method == "getUpdates":
            return {"ok": True, "result": [{"update_id": 3, "message": {"from": {}, "chat": {"id": 42}, "text": "/status"}}]}
        raise AssertionError(method)
    result = hermes.run_once(dry_run=True, api=fake_api)
    assert result["outcome"] == "PROCESSED"
    assert result["updates_processed"] == 1
    assert len(list((tmp_path / "receipts").glob("*.json"))) == 1
