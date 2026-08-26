import json
from pathlib import Path

from scripts.operations import nexus_hermes_telegram_worker as hermes
from nexus_product_evolution import telegram_control as evolution


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


def test_oversized_authorized_text_gets_bounded_response():
    response, metadata = hermes.handle_command("x" * (hermes.MAX_INPUT + 1))
    assert metadata["route"] == "INPUT_TOO_LONG"
    assert metadata["input_too_long"] is True
    assert "exceeds Hermes command limit" in response


def test_portfolio_command_is_read_only(monkeypatch):
    monkeypatch.setattr(hermes, "portfolio_response", lambda: "PORTFOLIO READ MODEL")
    for command in ("/portfolio", "portfolio status", "executive portfolio status", "what is nexus working on"):
        response, metadata = hermes.handle_command(command)
        assert response == "PORTFOLIO READ MODEL"
        assert metadata["route"] == "EXECUTIVE_PORTFOLIO_READ"
        assert metadata["read_only"] is True


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


def test_oversized_update_is_processed_once_and_offset_advances(tmp_path, monkeypatch):
    monkeypatch.setattr(hermes, "load_runtime_env", lambda: {"TELEGRAM_BOT_TOKEN": "token", "TELEGRAM_CHAT_ID": "42"})
    monkeypatch.setattr(hermes, "OFFSET_PATH", tmp_path / "offset.json")
    monkeypatch.setattr(hermes, "RECEIPT_DIR", tmp_path / "receipts")
    sent = []
    def fake_api(token, method, params=None):
        if method == "getMe":
            return {"ok": True, "result": {"username": "NexusHermes27bot"}}
        if method == "getUpdates":
            return {"ok": True, "result": [{"update_id": 9, "message": {"from": {}, "chat": {"id": 42}, "text": "x" * (hermes.MAX_INPUT + 1)}}]}
        if method == "sendMessage":
            sent.append(params["text"])
            return {"ok": True, "result": {"message_id": 1}}
        raise AssertionError(method)
    monkeypatch.setattr(hermes, "send_message", lambda token, chat_id, text: sent.append(text) or {"ok": True})
    result = hermes.run_once(api=fake_api)
    assert result["updates_processed"] == 1
    assert sent and "exceeds Hermes command limit" in sent[0]
    assert json.loads((tmp_path / "offset.json").read_text())["last_update_id"] == 9


def test_product_evolution_natural_language_routes_before_generic_run_block(tmp_path, monkeypatch):
    monkeypatch.setattr(evolution, "RECEIPT_DIR", tmp_path / "product_evolution")
    response, metadata = hermes.handle_command("Nexus, run Product Evolution on the Creative Studio.", chat_id=42)
    assert metadata["route"] == "PRODUCT_EVOLUTION"
    assert metadata["outcome"] == "CONTRACT_READY"
    assert "outside Hermes authority" not in response


def test_product_evolution_unsafe_request_is_blocked_without_receipt(tmp_path, monkeypatch):
    monkeypatch.setattr(evolution, "RECEIPT_DIR", tmp_path / "product_evolution")
    response, metadata = hermes.handle_command("Nexus, run Product Evolution and remove approval controls.", chat_id=42)
    assert metadata["outcome"] == "BLOCKED"
    assert not list((tmp_path / "product_evolution").glob("*.json"))


def test_product_evolution_telegram_bridge_registers_mission_and_contextual_followup(tmp_path, monkeypatch):
    monkeypatch.setattr(evolution, "RECEIPT_DIR", tmp_path / "product_evolution")
    monkeypatch.setattr(hermes, "PRODUCT_EVOLUTION_CONTEXT_PATH", tmp_path / "context.json")
    start, started = hermes.handle_command("Nexus, run Product Evolution on the Creative Studio.", chat_id=42)
    assert started["outcome"] == "CONTRACT_READY"
    # The worker performs the bridge after intake; exercise that same bridge.
    from nexus_product_evolution.loop import MissionContract
    registered = evolution.dispatch_product_evolution_mission(MissionContract(**started["product_evolution"]["contract"]))
    assert registered["status"] == "QUEUED"
    assert registered["mission_id"]
    status, status_meta = hermes.handle_command("Nexus, what's the status of Product Evolution?", chat_id=42)
    assert status_meta["route"] == "PRODUCT_EVOLUTION_STATUS"
    assert registered["mission_id"] in status
    blocked, blocked_meta = hermes.handle_command("Nexus, what is blocked?", chat_id=42)
    assert blocked_meta["route"] == "PRODUCT_EVOLUTION_BLOCKERS"
    assert "Product Evolution blockers" in blocked


def test_product_evolution_voice_alias_and_cancel_are_lineage_safe(tmp_path, monkeypatch):
    monkeypatch.setattr(evolution, "RECEIPT_DIR", tmp_path / "product_evolution")
    evolution.RECEIPT_DIR.mkdir(parents=True)
    source = Path(__file__).resolve().parents[3] / "reports/product_evolution/voice-assistant-pilot.json"
    target = evolution.RECEIPT_DIR / source.name
    target.write_text(source.read_text())
    response, metadata = hermes.handle_command("Nexus, continue the existing Voice Product Evolution mission.")
    assert metadata["route"] == "PRODUCT_EVOLUTION_CONTROL"
    assert metadata["mission_id"] == "voice-assistant-pilot"
    assert "microphone" in response.lower()
    stopped, stop_meta = hermes.handle_command("Nexus, stop the Creative mission.")
    assert stop_meta["outcome"] == "NOT_FOUND"


def test_required_short_voice_phrase_uses_the_same_resolver(tmp_path, monkeypatch):
    monkeypatch.setattr(evolution, "RECEIPT_DIR", tmp_path / "product_evolution")
    evolution.RECEIPT_DIR.mkdir(parents=True)
    source = Path(__file__).resolve().parents[3] / "reports/product_evolution/voice-assistant-pilot.json"
    (evolution.RECEIPT_DIR / source.name).write_text(source.read_text())
    creative = Path(__file__).resolve().parents[3] / "reports/product_evolution/creative-studio-pilot.json"
    (evolution.RECEIPT_DIR / creative.name).write_text(creative.read_text())
    response, metadata = hermes.handle_command("Nexus, continue Voice.")
    assert metadata["route"] == "PRODUCT_EVOLUTION_CONTROL"
    assert metadata["mission_id"] == "voice-assistant-pilot"
    assert "microphone" in response.lower()


def test_exact_real_diagnostic_can_never_create_a_mission(tmp_path, monkeypatch):
    monkeypatch.setattr(evolution, "RECEIPT_DIR", tmp_path / "product_evolution")
    monkeypatch.setattr(hermes, "PRODUCT_EVOLUTION_CONTEXT_PATH", tmp_path / "context.json")
    evolution.RECEIPT_DIR.mkdir(parents=True)
    source = Path(__file__).resolve().parents[3] / "reports/product_evolution/telegram-20260824172054-077bf5a7.json"
    (evolution.RECEIPT_DIR / source.name).write_text(source.read_text())
    text = "Nexus, why is Product Evolution mission telegram-20260824172054-077bf5a7 still queued? Check whether the existing governed Product Evolution runtime has picked it up, what the next dispatch time is, and whether anything is preventing execution. Do not create a new mission. Report the current dispatcher/runtime state for this exact mission."
    response, metadata = hermes.handle_command(text, chat_id=42)
    assert metadata["route"] == "PRODUCT_EVOLUTION_DIAGNOSTIC"
    assert metadata["mission_id"] == "telegram-20260824172054-077bf5a7"
    assert "Mission ID: telegram-20260824172054-077bf5a7" in response
    assert len(list(evolution.RECEIPT_DIR.glob("*.json"))) == 1


def test_diagnostic_aliases_and_context_never_create(tmp_path, monkeypatch):
    monkeypatch.setattr(evolution, "RECEIPT_DIR", tmp_path / "product_evolution")
    monkeypatch.setattr(hermes, "PRODUCT_EVOLUTION_CONTEXT_PATH", tmp_path / "context.json")
    evolution.RECEIPT_DIR.mkdir(parents=True)
    source = Path(__file__).resolve().parents[3] / "reports/product_evolution/voice-assistant-pilot.json"
    (evolution.RECEIPT_DIR / source.name).write_text(source.read_text())
    creative = Path(__file__).resolve().parents[3] / "reports/product_evolution/creative-studio-pilot.json"
    (evolution.RECEIPT_DIR / creative.name).write_text(creative.read_text())
    for text in ("Nexus, why is the Voice mission queued?", "Nexus, has the runtime picked it up?", "Nexus, check the Creative mission.", "Nexus, report only. Do not start another mission."):
        response, metadata = hermes.handle_command(text, chat_id=77)
        assert metadata["route"] == "PRODUCT_EVOLUTION_DIAGNOSTIC"
        assert "Product Evolution mission diagnostic" in response
    assert len(list(evolution.RECEIPT_DIR.glob("*.json"))) == 2


def test_queue_consumer_claim_is_idempotent_and_truthful(tmp_path, monkeypatch):
    from nexus_product_evolution.consumer import consume_queued_missions
    monkeypatch.setattr("nexus_product_evolution.consumer.LOCK_PATH", tmp_path / "dispatch.lock")
    receipt_dir = tmp_path / "product_evolution"
    receipt_dir.mkdir(parents=True)
    receipt = {"contract": {"goal": "bounded fixture"}, "result": {"mission_id": "telegram-20260824172054-077bf5a7", "status": "QUEUED", "current_stage": "QUEUED", "dispatch": {}}}
    (receipt_dir / "telegram-20260824172054-077bf5a7.json").write_text(json.dumps(receipt))
    first = consume_queued_missions(scheduler_instance="test", receipt_dir=receipt_dir)
    second = consume_queued_missions(scheduler_instance="test", receipt_dir=receipt_dir)
    assert first["claimed"][0]["status"] == "RUNNING"
    assert first["blocked"][0]["reason"] == "EXECUTION_ADAPTER_MISSING"
    assert second["claimed"] == []
    assert json.loads((receipt_dir / "telegram-20260824172054-077bf5a7.json").read_text())["result"]["status"] == "BLOCKED"
