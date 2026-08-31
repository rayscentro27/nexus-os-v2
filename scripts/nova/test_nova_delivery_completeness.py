import json

from scripts.nova import nova_telegram_worker as worker


def test_transient_delivery_is_persisted_and_recovered_without_resynthesis(tmp_path, monkeypatch):
    monkeypatch.setattr(worker, "NOVA_DELIVERY_DIR", str(tmp_path / "delivery"))
    calls = []

    def fake_attempt(chat_id, chunk, token=None, timeout=None):
        calls.append(chunk)
        if len(calls) <= 2:
            return {"ok": False, "retryable": True, "error": "connection reset"}
        return {"ok": True, "message_id": 77}

    monkeypatch.setattr(worker, "_tg_send_attempt", fake_attempt)
    monkeypatch.setattr(worker, "TELEGRAM_SEND_ATTEMPTS", 2)
    monkeypatch.setattr(worker.time, "sleep", lambda _: None)

    first = worker._deliver_response(41, 99, "same composed answer", hermes_run_id="h-41", mission_id="m-41")
    assert first["state"] == "FAILED_TRANSIENT"
    assert first["terminal_outcome"] == "DELIVERY_PENDING"
    assert first["attempt_count"] == 2

    second = worker._deliver_response(41, 99, "same composed answer", hermes_run_id="h-41", mission_id="m-41")
    assert second["state"] == "DELIVERED"
    assert second["message_ids"] == [77]
    assert calls == ["same composed answer"] * 3

    persisted = json.loads((tmp_path / "delivery" / "41.json").read_text())
    assert persisted["state"] == "DELIVERED"
    assert persisted["response_hash"] == first["response_hash"]


def test_permanent_delivery_failure_is_terminal_and_not_retried(tmp_path, monkeypatch):
    monkeypatch.setattr(worker, "NOVA_DELIVERY_DIR", str(tmp_path / "delivery"))
    calls = []

    def fake_attempt(*args, **kwargs):
        calls.append(True)
        return {"ok": False, "retryable": False, "error": "HTTP 400"}

    monkeypatch.setattr(worker, "_tg_send_attempt", fake_attempt)
    result = worker._deliver_response(42, 99, "answer")
    assert result["state"] == "FAILED_TERMINAL"
    assert result["terminal_outcome"] == "TERMINAL_DELIVERY_FAILURE"
    assert len(calls) == 1
