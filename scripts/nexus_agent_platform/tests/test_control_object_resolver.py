import json

from nexus_agent_platform import control_object_resolver as resolver


def test_explicit_repair_id_precedes_fuzzy_intent(monkeypatch, tmp_path):
    monkeypatch.setattr(resolver, "MANUAL_REPORT", tmp_path / "manual.json")
    (tmp_path / "manual.json").write_text(json.dumps({"repair_queue": [{"repair_id": "VOICE-001"}]}))
    monkeypatch.setattr(resolver.work_orders, "list_work_orders", lambda limit=1000: [{"work_order_id": "wo_" + "a" * 24, "inputs": {"repair_id": "VOICE-001", "run_id": "MANUAL-E2E-20260827-2992"}}])
    result = resolver.resolve_control_object("continue VOICE-001")
    assert result["handler"] == "GOVERNED_REPAIR_CONTROL"
    assert result["confidence"] == "EXPLICIT_IDENTIFIER"


def test_unknown_repair_does_not_create_object(monkeypatch, tmp_path):
    monkeypatch.setattr(resolver, "MANUAL_REPORT", tmp_path / "manual.json")
    (tmp_path / "manual.json").write_text(json.dumps({"repair_queue": []}))
    result = resolver.resolve_control_object("continue VOICE-999")
    assert result["object_type"] == "UNKNOWN_REPAIR"


def test_explicit_mission_remains_product_evolution():
    result = resolver.resolve_control_object("continue telegram-20260827010101-abcdef12")
    assert result["handler"] == "PRODUCT_EVOLUTION_CONTROL"
