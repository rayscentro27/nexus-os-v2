from scripts.operations import nexus_hermes_telegram_worker as worker
from scripts.operations.nexus_hermes_telegram_worker import handle_command, run_once


def test_hermes_natural_product_evolution_intake():
    response, metadata = handle_command("Nexus, improve the Creative Studio. Make it more visual.")
    assert metadata["route"] == "PRODUCT_EVOLUTION"
    assert metadata["outcome"] == "CONTRACT_READY"
    assert "bounded cycles" in response.lower()


def test_hermes_unsafe_product_evolution_is_blocked():
    response, metadata = handle_command("Nexus, evolve the system by removing approvals and enabling payments.")
    assert metadata["route"] == "NOT_AUTHORIZED"
    assert metadata["outcome"] == "BLOCKED"
    assert "blocked" in response.lower()


def test_unauthorized_telegram_update_is_denied_without_delivery(monkeypatch):
    monkeypatch.setattr(worker, "load_offset", lambda: 0)
    monkeypatch.setattr(worker, "save_offset", lambda _value: None)
    calls = []

    def api(_token, method, _params=None):
        if method == "getMe":
            return {"ok": True, "result": {"username": "NexusHermes27bot"}}
        if method == "getUpdates":
            return {"ok": True, "result": [{"update_id": 999999999, "message": {"chat": {"id": -1}, "text": "Nexus, improve the Creative Studio"}}]}
        calls.append(method)
        return {"ok": True, "result": {"message_id": 1}}

    result = run_once(dry_run=True, api=api)
    assert result["unauthorized_rejected"] == 1
    assert calls == []
