import json
import pytest

import scripts.nova.proactive_communications as proactive


@pytest.fixture(autouse=True)
def isolate_live_resource_incident_reads(monkeypatch,tmp_path):
    import nexus_agent_platform.feeder_runtime as feeder
    monkeypatch.setattr(feeder,"_request",lambda *args,**kwargs:[])
    monkeypatch.setattr(proactive,"HEARTBEAT_PATH",tmp_path/"heartbeat.json")
    monkeypatch.setattr(proactive,"OPERATOR_PATH",tmp_path/"operator.json")
    monkeypatch.setattr(proactive,"MATERIAL_EVENTS_PATH",tmp_path/"events.jsonl")
    monkeypatch.setattr(proactive,"RECEIPT_DIR",tmp_path/"receipts")


def test_classifier_is_deterministic_and_bounded():
    assert proactive.classify_event({"kind": "GOAL_ADVANCED"}) == "MATERIAL"
    assert proactive.classify_event({"kind": "RESEARCH_NOT_REAL"}) == "CRITICAL"
    assert proactive.classify_event({"kind": "HEARTBEAT"}) == "ROUTINE"
    assert proactive.classify_event({"kind": "unknown"}) == "SUPPRESSED"
    assert proactive.classify_event({"kind": "RESOURCE_ALARM"}) == "CRITICAL"


def test_real_resource_alarm_routes_through_nova_worker(monkeypatch,tmp_path):
    import nexus_agent_platform.feeder_runtime as feeder
    state=tmp_path/"proactive.json"
    monkeypatch.setattr(proactive,"STATE_PATH",state)
    monkeypatch.setattr(proactive,"HEARTBEAT_PATH",tmp_path/"heartbeat.json")
    monkeypatch.setattr(proactive,"OPERATOR_PATH",tmp_path/"operator.json")
    monkeypatch.setattr(proactive,"MATERIAL_EVENTS_PATH",tmp_path/"events.jsonl")
    monkeypatch.setattr(proactive,"RECEIPT_DIR",tmp_path/"receipts")
    monkeypatch.setattr(proactive,"get_env",lambda:{"TELEGRAM_CHAT_ID":"42"})
    monkeypatch.setattr(proactive,"_latest_receipt",lambda:None)
    def read(path):
        if "nexus_resource_incidents" in path:
            return [{"job_id":"job_v5_research_source_review_20261010","code":"BUDGET_HARD_LIMIT",
                "threshold":{"bytes":500000},"observed":{"bytes":600000},"created_at":"now"}]
        if "nexus_resource_policies" in path:
            return [{"state":"HARD_STOP","hard_limits":{"usage":{"bytes":500000}}}]
        return []
    monkeypatch.setattr(feeder,"_request",read)
    delivered=[]
    monkeypatch.setattr(proactive,"tg_send_message",lambda chat,text:delivered.append((chat,text)) or [123])
    result=proactive.process_once()
    assert result["status"]=="PASS"
    assert delivered and delivered[0][0]=="42"
    assert "NotebookLM research discovery reached" in delivered[0][1]
    assert "Continue independent V5 jobs" in delivered[0][1]


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
    assert second["results"][0]["status"] in {"SUPPRESSED_DUPLICATE", "SUPPRESSED_NO_MATERIAL_CHANGE"}
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


def test_capability_verification_is_not_material_progress(monkeypatch, tmp_path):
    state = tmp_path / "proactive.json"
    monkeypatch.setattr(proactive, "STATE_PATH", state)
    monkeypatch.setattr(proactive, "get_env", lambda: {"TELEGRAM_CHAT_ID": "42"})
    monkeypatch.setattr(proactive, "_read", lambda path, default: {
        "heartbeat": "ACTIVE", "result_status": "PASS"
    } if path == proactive.HEARTBEAT_PATH else {
        "status": "COMPLETED_WITH_FINDINGS",
        "safe_internal_execution": "PASS",
        "safe_action_results": [{"result": {
            "status": "PASS", "parent_goal": "media.youtube_video",
            "action": "ai.plan_and_verify",
            "executor_result": {"action": "internal.capability_verify"},
        }}],
    } if path == proactive.OPERATOR_PATH else default)
    monkeypatch.setattr(proactive, "tg_send_message", lambda chat, text: [1])
    result = proactive.process_once()
    assert result["status"] == "NO_SEND"


def test_bounded_deliverable_is_material_progress(monkeypatch, tmp_path):
    state = tmp_path / "proactive.json"
    monkeypatch.setattr(proactive, "STATE_PATH", state)
    monkeypatch.setattr(proactive, "get_env", lambda: {"TELEGRAM_CHAT_ID": "42"})
    monkeypatch.setattr(proactive, "_read", lambda path, default: {
        "heartbeat": "ACTIVE", "result_status": "PASS"
    } if path == proactive.HEARTBEAT_PATH else default)
    monkeypatch.setattr(proactive, "_latest_receipt", lambda: {
        "status": "COMPLETED_WITH_FINDINGS",
        "safe_internal_execution": "PASS",
        "parent_goal": "media.youtube_video",
        "safe_action_results": [{"result": {
            "status": "PASS", "parent_goal": "media.youtube_video",
            "action": "ai.plan_and_verify",
                "executor_result": {"action": "internal.create_bounded_work_artifact", "material_progress": True},
        }}],
    })
    sent = []
    monkeypatch.setattr(proactive, "tg_send_message", lambda chat, text: sent.append(text) or [1])
    result = proactive.process_once()
    assert result["status"] == "PASS"
    assert sent and "verified internal work result" in sent[0]


def test_terminal_certification_is_one_shot_and_truthful(monkeypatch, tmp_path):
    state = tmp_path / "proactive.json"
    monkeypatch.setattr(proactive, "STATE_PATH", state)
    monkeypatch.setattr(proactive, "get_env", lambda: {"TELEGRAM_CHAT_ID": "42"})
    calls = []
    monkeypatch.setattr(proactive, "tg_send_message", lambda chat, text: calls.append((chat, text)) or [123])
    event = {
        "autonomy": "PARTIAL",
        "departments": "Research, Trading, Portal/Product",
        "objectives_advanced": "7",
        "ai_workforce": "PARTIAL",
        "multi_cycle": "PARTIAL",
        "nova_control": "PARTIAL",
        "ray_action": "None",
    }
    first = proactive.process_once(terminal_event=event)
    second = proactive.process_once(terminal_event=event)
    assert first["status"] == "PASS"
    assert second["results"][0]["status"] in {"SUPPRESSED_DUPLICATE", "SUPPRESSED_NO_MATERIAL_CHANGE"}
    assert len(calls) == 1
    assert "A material company event was verified" in calls[0][1]
    assert json.loads(state.read_text())["last_event_severity"] == "MATERIAL"


def test_terminal_goal_review_event_uses_persisted_closure(monkeypatch, tmp_path):
    state = tmp_path / "proactive.json"
    monkeypatch.setattr(proactive, "STATE_PATH", state)
    monkeypatch.setattr(proactive, "get_env", lambda: {"TELEGRAM_CHAT_ID": "42"})
    monkeypatch.setattr(proactive, "_read", lambda path, default: {
        "heartbeat": "ACTIVE", "result_status": "PASS"
    } if path == proactive.HEARTBEAT_PATH else default)
    monkeypatch.setattr(proactive, "_latest_receipt", lambda: {
        "receipt_path": "reports/runtime/nexus_active_operator_receipts/closure.json",
        "objective_closures": [{
            "goal_id": "goclear.example_campaign",
            "status": "READY_FOR_HUMAN_REVIEW",
            "artifact_path": "reports/runtime/wp9b/creative_package.json",
        }],
    })
    sent = []
    monkeypatch.setattr(proactive, "tg_send_message", lambda chat, text: sent.append(text) or [7])
    result = proactive.process_once()
    assert result["status"] == "PASS"
    assert sent and "ready for Ray review" in sent[0]
    assert "persisted internal record" in sent[0]
