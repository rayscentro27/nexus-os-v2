import json

import scripts.nova.proactive_communications as proactive


def test_classifier_is_deterministic_and_bounded():
    assert proactive.classify_event({"kind": "GOAL_ADVANCED"}) == "MATERIAL"
    assert proactive.classify_event({"kind": "RESEARCH_NOT_REAL"}) == "CRITICAL"
    assert proactive.classify_event({"kind": "HEARTBEAT"}) == "ROUTINE"
    assert proactive.classify_event({"kind": "unknown"}) == "SUPPRESSED"


def test_trusted_chat_fails_closed(monkeypatch):
    monkeypatch.setattr(proactive, "get_env", lambda: {"TELEGRAM_CHAT_ID": "1,2"})
    assert proactive.trusted_ray_chat() is None


def test_test_event_is_idempotent(monkeypatch, tmp_path):
    state = tmp_path / "proactive.json"
    monkeypatch.setattr(proactive, "STATE_PATH", state)
    monkeypatch.setattr(proactive, "get_env", lambda: {"TELEGRAM_CHAT_ID": "42"})
    calls = []
    monkeypatch.setattr(proactive, "tg_send_message", lambda chat, text: calls.append((chat, text)) or [99])
    first = proactive.process_once(force_test=True)
    second = proactive.process_once(force_test=True)
    assert first["status"] == "PASS"
    assert second["results"][0]["status"] == "SUPPRESSED_DUPLICATE"
    assert len(calls) == 1
    saved = json.loads(state.read_text())
    assert saved["last_notification_at"]
    assert saved["last_event_severity"] == "MATERIAL"


def test_failed_nested_action_is_not_progress(monkeypatch, tmp_path):
    state = tmp_path / "proactive.json"
    monkeypatch.setattr(proactive, "STATE_PATH", state)
    monkeypatch.setattr(proactive, "get_env", lambda: {"TELEGRAM_CHAT_ID": "42"})
    monkeypatch.setattr(proactive, "_read", lambda path, default: {
        "heartbeat": "ACTIVE", "result_status": "PASS"
    } if path == proactive.HEARTBEAT_PATH else {
        "status": "COMPLETED_WITH_FINDINGS",
        "safe_internal_execution": "PASS",
        "safe_action_results": [{"result": {"status": "FAIL", "parent_goal": "trading.real_data"}}],
    } if path == proactive.OPERATOR_PATH else default)
    sent = []
    monkeypatch.setattr(proactive, "tg_send_message", lambda chat, text: sent.append(text) or [1])
    result = proactive.process_once()
    assert result["status"] == "NO_SEND"
    assert not sent
