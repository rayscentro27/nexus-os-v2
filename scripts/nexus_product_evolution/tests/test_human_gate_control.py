from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from nexus_product_evolution import telegram_control as control  # noqa: E402


MISSION_ID = "telegram-20260824172054-077bf5a7"
REAL_MESSAGE = """Nexus, update and resume existing Product Evolution mission
telegram-20260824172054-077bf5a7 with new human test evidence.
Do not create a new mission. The previous HUMAN_GATE was completed and FAILED.
Production Voice Listening now reaches the Voice service successfully:
OPTIONS returns 204 and preview/transcribe can return 200, but persistent
listening produces repeated 429 responses. This proves the previous human gate
did not pass. Record this evidence against the existing mission, move it out of
HUMAN_GATE, and resume Product Evolution on the same lineage."""


def _receipt(path: Path, *, status: str = "PARTIAL", stage: str = "HUMAN_GATE") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "contract": {"goal": "repair Voice transport", "human_only_gates": ["human microphone test"]},
        "created_at": "2026-08-24T17:20:54+00:00",
        "result": {"mission_id": MISSION_ID, "status": status, "current_stage": stage, "updated_at": "2026-08-24T22:22:10+00:00", "dispatch": {"adapter_id": "VOICE_PRODUCT_EVOLUTION"}, "execution_history": []},
    }, indent=2))


def test_exact_real_message_is_human_evidence_action_not_diagnostic(tmp_path, monkeypatch):
    monkeypatch.setattr(control, "RECEIPT_DIR", tmp_path / "product_evolution")
    path = control.RECEIPT_DIR / f"{MISSION_ID}.json"
    _receipt(path)

    assert control.classify_product_evolution_request(REAL_MESSAGE) == "RESUME_WITH_HUMAN_EVIDENCE"
    response = control.handle_product_evolution_intake(REAL_MESSAGE)
    assert response["route"] == "PRODUCT_EVOLUTION_HUMAN_EVIDENCE"
    assert response["status"] == "EVIDENCE_RECORDED"
    assert response["mission_id"] == MISSION_ID
    saved = json.loads(path.read_text())["result"]
    assert saved["status"] == "QUEUED"
    assert saved["current_stage"] == "RESUMED_AFTER_HUMAN_FAIL"
    assert saved["human_evidence"][0]["outcome"] == "FAIL"
    assert [item["event"] for item in saved["execution_history"]] == ["HUMAN_EVIDENCE_RECORDED", "RESUME_WITH_HUMAN_EVIDENCE"]
    assert len(list(control.RECEIPT_DIR.glob("*.json"))) == 1

    duplicate = control.handle_product_evolution_intake(REAL_MESSAGE)
    assert duplicate["status"] == "ALREADY_RECORDED"
    saved_again = json.loads(path.read_text())["result"]
    assert len(saved_again["human_evidence"]) == 1
    assert len(saved_again["execution_history"]) == 2


def test_human_pass_is_recorded_without_repair_queue(tmp_path, monkeypatch):
    monkeypatch.setattr(control, "RECEIPT_DIR", tmp_path / "product_evolution")
    path = control.RECEIPT_DIR / f"{MISSION_ID}.json"
    _receipt(path)
    result = control.handle_product_evolution_intake("Nexus, the Voice microphone test passed for mission telegram-20260824172054-077bf5a7.")
    assert result["status"] == "EVIDENCE_RECORDED"
    saved = json.loads(path.read_text())["result"]
    assert saved["human_evidence"][0]["outcome"] == "PASS"
    assert saved["status"] == "PARTIAL"
    assert saved["current_stage"] == "HUMAN_EVIDENCE_RECORDED"


def test_status_exact_mission_remains_diagnostic(tmp_path, monkeypatch):
    monkeypatch.setattr(control, "RECEIPT_DIR", tmp_path / "product_evolution")
    path = control.RECEIPT_DIR / f"{MISSION_ID}.json"
    _receipt(path)
    result = control.handle_product_evolution_intake(f"Nexus, what's the status of mission {MISSION_ID}?")
    assert result["route"] == "PRODUCT_EVOLUTION_DIAGNOSTIC"
    assert result["mission_id"] == MISSION_ID


def test_delta_query_with_failed_test_language_remains_diagnostic(tmp_path, monkeypatch):
    monkeypatch.setattr(control, "RECEIPT_DIR", tmp_path / "product_evolution")
    path = control.RECEIPT_DIR / f"{MISSION_ID}.json"
    _receipt(path)
    control.record_human_evidence(MISSION_ID, "Nexus, the Voice microphone test failed. Record this evidence and continue.")
    result = control.handle_product_evolution_intake(f"Nexus, what changed on the Voice mission since my failed test? Mission {MISSION_ID}.")
    assert result["route"] == "PRODUCT_EVOLUTION_DIAGNOSTIC"
    assert "Product Evolution delta" in result["response"]
    assert len(json.loads(path.read_text())["result"]["human_evidence"]) == 1
