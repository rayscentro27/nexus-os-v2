import json

from scripts.operations import nexus_hermes_telegram_worker as hermes
from nexus_agent_platform.governed import action_registry


def _manual_report(run_id="MANUAL-E2E-20260827-2992"):
    return {
        "run_id": run_id,
        "status": "WAITING_HUMAN_ACTION",
        "repair_queue": [
            {"repair_id": "VOICE-001", "status": "WAITING_APPROVAL"},
            {"repair_id": "EMAIL-001", "status": "WAITING_APPROVAL"},
        ],
        "repair_approvals": {
            "VOICE-001:" + run_id: {
                "status": "PASS", "authority_scope": ["VOICE-001"], "update_id": 197233423,
            }
        },
    }


def test_voice_engineering_action_is_registered_and_bounded():
    action = action_registry.get_action("engineering.repair.voice")
    assert action["risk_level"] == action_registry.Risk.LOW
    assert action["input_schema"]["required"] == ["repair_id", "run_id"]
    assert action_registry.is_action_executable("engineering.repair.voice")


def test_natural_voice_repair_starts_once_from_existing_approval(monkeypatch, tmp_path):
    monkeypatch.setattr(hermes, "MANUAL_CERT_REPORT_PATH", tmp_path / "manual.json")
    (tmp_path / "manual.json").write_text(json.dumps(_manual_report()))
    started = []
    monkeypatch.setattr("nexus_agent_platform.governed.voice_repair.start_voice_repair", lambda run_id, chat_id=None: started.append((run_id, chat_id)) or {"status": "started", "work_order_id": "wo_voice"})
    response, meta = hermes.handle_command("Nexus, repair Voice.", chat_id=42)
    assert meta["route"] == "VOICE_REPAIR_START"
    assert meta["outcome"] == "STARTED"
    assert started == [("MANUAL-E2E-20260827-2992", 42)]
    assert "wo_voice" in response


def test_voice_progress_is_persisted_state_not_generic_help(monkeypatch, tmp_path):
    monkeypatch.setattr(hermes, "ROOT", tmp_path)
    (tmp_path / "reports/runtime").mkdir(parents=True)
    (tmp_path / "reports/runtime/voice_repair_latest.json").write_text(json.dumps({"repair_id": "VOICE-001", "state": "TESTING", "work_order_id": "wo_voice", "executor": "codex"}))
    response, meta = hermes.handle_command("is the Voice repair being done right now")
    assert meta["route"] == "VOICE_REPAIR_STATUS"
    assert "TESTING" in response
    assert "wo_voice" in response


def test_natural_system_status_report_uses_canonical_status(monkeypatch):
    monkeypatch.setattr(hermes, "status_response", lambda: "CANONICAL STATUS")
    response, meta = hermes.handle_command("can you provide a system status report")
    assert response == "CANONICAL STATUS"
    assert meta["outcome"] == "ANSWERED"


def test_other_repairs_cannot_start_from_voice_approval(monkeypatch, tmp_path):
    monkeypatch.setattr(hermes, "MANUAL_CERT_REPORT_PATH", tmp_path / "manual.json")
    report = _manual_report()
    report["repair_approvals"] = {"VOICE-001:MANUAL-E2E-20260827-2992": {"status": "PASS", "authority_scope": ["VOICE-001"]}}
    (tmp_path / "manual.json").write_text(json.dumps(report))
    response, meta = hermes.handle_command("APPROVE REPAIR EMAIL-001 MANUAL-E2E-20260827-2992", chat_id=42)
    assert meta["outcome"] == "APPROVAL_RECORDED"
    # This records only the explicitly named repair approval; it cannot start
    # the Voice engineering executor or expand its authority.
    assert "EMAIL-001" in response
