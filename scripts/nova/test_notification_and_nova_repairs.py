from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "nova"))

from nexus_agent_platform.company_objective_router import build_root_objective, route_company_objective
from nova.notification_policy import event_fingerprint, executive_message


def load_proactive():
    spec = importlib.util.spec_from_file_location("proactive_test_module", ROOT / "scripts/nova/proactive_communications.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_semantic_audit_dedup_and_material_change(monkeypatch, tmp_path):
    proactive = load_proactive()
    monkeypatch.setattr(proactive, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(proactive, "trusted_ray_chat", lambda: "dry-run")
    sent = []
    monkeypatch.setattr(proactive, "tg_send_message", lambda chat, text: sent.append(text) or ["dry-run"])
    base = {"kind": "SUPERVISOR_UNHEALTHY", "affected_system": "Research", "state": "DEGRADED", "blocker": "provider unavailable", "summary": "Research needs recovery."}
    for idx in range(4):
        event = {**base, "audit_id": f"audit-{idx}", "receipt_id": f"receipt-{idx}", "timestamp": f"2026-09-26T00:0{idx}:00Z"}
        result = proactive.process_once(terminal_event=event)
        assert result["status"] == "PASS" if idx == 0 else "NO_SEND"
    assert len(sent) == 1
    changed = {**base, "state": "CRITICAL", "required_action": "Review the outage."}
    assert proactive.process_once(terminal_event=changed)["status"] == "PASS"
    assert len(sent) == 2
    assert proactive.process_once(terminal_event=changed)["status"] == "NO_SEND"


def test_one_message_one_root_and_simple_objective():
    long_message = """MISSION\nRepair notification behavior.\nBUSINESS EVENT\nDo not send messages.\nSUCCESS CRITERIA\nOne root only.\nFINAL OUTPUT\nSave a report.\nBEGIN"""
    root = build_root_objective(long_message, conversation_message_id=42)
    assert root["parent_objective_id"] is None
    assert root["explicit_intent"] is True
    assert len(root["requirements"]) >= 3
    plan = route_company_objective("Research current funding requirements.", conversation_message_id=43)
    assert plan["root_objective"]["objective_id"]
    assert plan["root_objective"]["parent_objective_id"] is None
    assert plan["objective"] == "Research current funding requirements."


def test_executive_rendering_has_business_language_only():
    message = executive_message({
        "kind": "MATERIAL_COMPLETION",
        "summary": "Research identified two funding-related findings.",
        "why_it_matters": "The findings can inform the next client review.",
        "required_action": "Approve the proposed review scope.",
        "next": "Research will continue the evidence check.",
        "audit_id": "secret-audit-id",
        "receipt_id": "secret-receipt-id",
    }, "MATERIAL")
    assert "What happened:" in message and "Needs you:" in message and "Next:" in message
    for forbidden in ("state_assessment_written", "ledger_snapshot_written", "internal output recorded", "audit_id", "receipt_id"):
        assert forbidden not in message


def test_cycle_summary_is_executive_and_not_a_transport_action():
    scheduler_path = ROOT / "scripts/wp9_company_scheduler.py"
    source = scheduler_path.read_text(encoding="utf-8")
    assert "send_telegram(cycle_summary(record)" not in source
