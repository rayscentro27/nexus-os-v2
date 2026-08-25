from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from nexus_product_evolution import telegram_control as control


MISSION_ID = "telegram-20260824172054-077bf5a7"
RELEASE_ID = "rel-telegram-20260824172054-077bf5a7-0a85d39bfed0"
COMMIT = "0a85d39bfed0cc74e318c40219a6b333b8779860"

REAL_INSPECTION_MESSAGE = f"""Nexus, inspect the existing release {RELEASE_ID} for mission {MISSION_ID}.

Do not create a new mission.
Do not record new human evidence.
Do not redeploy anything.

Report:
- current release approval state
- current mission stage
- whether RELEASE_DISPATCH_CLAIMED occurred
- whether production deployment occurred
- Netlify production deploy ID
- observed production build SHA
- production verification checks
- whether rollback occurred
- whether the mission is now at HUMAN_GATE

Give me deployment truth only."""


def test_exact_identifiers_do_not_overlap():
    assert control.exact_mission_id(f"for mission {MISSION_ID}") == MISSION_ID
    assert control.exact_mission_id(RELEASE_ID) is None
    assert control.exact_release_id(RELEASE_ID) == RELEASE_ID


def test_ray_release_inspection_routes_read_only(monkeypatch):
    writes = []
    monkeypatch.setattr(control, "_write_receipt", lambda *args: writes.append(args))
    result = control.handle_product_evolution_intake(REAL_INSPECTION_MESSAGE)
    assert result["handled"] is True
    assert result["route"] == "PRODUCT_EVOLUTION_RELEASE_INSPECTION"
    assert result["mission_id"] == MISSION_ID
    assert result["release_id"] == RELEASE_ID
    assert result["deployment"]["approval_state"] == "APPROVED"
    assert isinstance(result["deployment"]["release_dispatch_claimed"], bool)
    assert result["deployment"]["deployment_occurred"] is False
    assert result["deployment"]["production_verification"] == "NOT_RUN"
    assert result["deployment"]["rollback_occurred"] is False
    assert result["deployment"]["human_gate"] is False
    assert result["deployment"]["retry_count"] == 1
    assert result["deployment"]["release_dispatch_claim_count"] == 2
    assert result["deployment"]["release_retry_ready"] is True
    assert result["deployment"]["blocker"] == "NETLIFY_AUTH_UNAVAILABLE"
    assert result["deployment"]["deployment_result_status"] == "FAILED"
    assert result["deployment"]["deployment_result_reason"] == "NETLIFY_AUTH_UNAVAILABLE"
    assert writes == []


def test_release_inspection_reports_latest_claim_and_retry_timestamp(monkeypatch):
    history = [
        {"event": "RELEASE_RETRY_READY", "at": "2026-08-25T16:48:04+00:00"},
        {"event": "RELEASE_DISPATCH_CLAIMED", "at": "2026-08-25T16:20:25+00:00"},
        {"event": "RELEASE_DISPATCH_CLAIMED", "at": "2026-08-25T17:20:30+00:00"},
    ]
    monkeypatch.setattr(control, "ROOT", Path("/path/does/not/exist"))
    truth = control.release_inspection({"result": {"mission_id": MISSION_ID, "status": "BLOCKED", "current_stage": "BLOCKED", "execution_history": history, "release": {"release_id": RELEASE_ID, "retry_count": 1, "retry_ready_at": "2026-08-25T16:48:04+00:00", "deployment_result": {"status": "FAILED", "reason": "NETLIFY_AUTH_UNAVAILABLE", "phase": "auth", "outcome": {"status": "BLOCKED", "reason": "NETLIFY_AUTH_UNAVAILABLE"}}}}})
    assert truth["release_dispatch_claim_count"] == 2
    assert truth["release_dispatch_claimed_at"] == "2026-08-25T17:20:30+00:00"
    assert truth["release_retry_ready_at"] == "2026-08-25T16:48:04+00:00"
    assert truth["scheduler_ran_after_retry_ready"] == "UNKNOWN"


def test_malformed_deployment_result_is_safe_and_read_only(monkeypatch):
    writes = []
    monkeypatch.setattr(control, "_write_receipt", lambda *args: writes.append(args))
    truth = control.release_inspection({"result": {"mission_id": MISSION_ID, "release": {"release_id": RELEASE_ID, "deployment_result": "bad"}}})
    text = control.release_inspection_text(truth)
    assert truth["deployment_result_status"] == "UNKNOWN"
    assert truth["deployment_result_reason"] == "UNKNOWN"
    assert "Deployment result: UNKNOWN / UNKNOWN / UNKNOWN" in text
    assert writes == []


def test_matching_and_conflicting_identifiers(monkeypatch):
    receipt = {"result": {"mission_id": MISSION_ID, "release": {"release_id": RELEASE_ID, "release_candidate_commit": COMMIT}}}
    monkeypatch.setattr(control, "_receipt_files", lambda: [])
    monkeypatch.setattr(control, "_load_release_by_id", lambda _release: receipt)
    assert control._resolve_release_or_mission(f"inspect {RELEASE_ID} for mission {MISSION_ID}")[1] is None
    _, error = control._resolve_release_or_mission(f"inspect {RELEASE_ID} for mission telegram-20260824172054-aaaaaaaa")
    assert error == "RELEASE_MISSION_ID_MISMATCH"


def test_unknown_release_and_malformed_receipt_are_truthful(monkeypatch, tmp_path):
    monkeypatch.setattr(control, "RECEIPT_DIR", tmp_path)
    assert control._load_release_by_id(RELEASE_ID) is None
    bad = tmp_path / f"{MISSION_ID}.json"
    bad.write_text("{not-json", encoding="utf-8")
    assert control._load_mission_by_id(MISSION_ID) is None


def test_malformed_exact_mission_receipt_is_not_reported_missing(monkeypatch, tmp_path):
    bad = tmp_path / f"{MISSION_ID}.json"
    bad.write_text("{not-json", encoding="utf-8")
    monkeypatch.setattr(control, "RECEIPT_DIR", tmp_path)
    message = f"inspect mission {MISSION_ID} and report deployment truth"
    resolved, error = control._resolve_release_or_mission(message)
    assert resolved is None
    assert error == "RECEIPT_PARSE_ERROR"


def test_long_inspection_message_preserves_exact_ids():
    text = ("context " * 150) + f" inspect release {RELEASE_ID} for mission {MISSION_ID}; report only"
    assert control.exact_mission_id(text) == MISSION_ID
    assert control.exact_release_id(text) == RELEASE_ID
    assert control.classify_product_evolution_request(text) == "RELEASE_INSPECTION"
