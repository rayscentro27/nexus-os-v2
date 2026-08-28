import json

from nexus_agent_platform import loop_certification_campaign as campaign
from scripts.operations import nexus_hermes_telegram_worker as hermes


def _seed(tmp_path, monkeypatch, state="ACTIVE"):
    monkeypatch.setattr(campaign, "CAMPAIGN_PATH", tmp_path / "campaign.json")
    monkeypatch.setattr(campaign, "CERT_REGISTRY_PATH", tmp_path / "registry.json")
    monkeypatch.setattr(campaign, "RECEIPTS_PATH", tmp_path / "receipts.jsonl")
    value = {
        "campaign_id": "LOOP-CERT-20260828T114525Z", "state": state,
        "current_loop": "telegram_operator", "current_stage": "01_REAL_TRIGGER",
        "current_loop_blocker": "NONE", "current_loop_evidence": {},
        "current_loop_stages": {}, "completed_loops": [], "certified_loops": [],
        "human_waiting_loops": [], "loop_order": ["telegram_operator", "hermes_router"],
        "inventory": [{"loop_id": "telegram_operator", "loop_name": "Telegram Operator"}, {"loop_id": "hermes_router", "loop_name": "Hermes Router"}],
        "outstanding_repairs": [{"repair_id": "VOICE-001", "state": "WAITING_WORKER"}],
    }
    campaign._write(campaign.CAMPAIGN_PATH, value)
    campaign._write(campaign.CERT_REGISTRY_PATH, {"campaign_id": value["campaign_id"], "loops": [{"campaign_id": value["campaign_id"], "loop_id": "telegram_operator", "certification_state": "NOT_TESTED"}]})
    return value["campaign_id"]


def test_explicit_commands_resolve_objects_and_arguments():
    assert campaign.parse_campaign_command("STATUS CAMPAIGN LOOP-CERT-20260828T114525Z") == {"action": "STATUS", "object_type": "CAMPAIGN", "campaign_id": "LOOP-CERT-20260828T114525Z"}
    assert campaign.parse_campaign_command("status campaign LOOP-CERT-20260828T114525Z")["campaign_id"] == "LOOP-CERT-20260828T114525Z"
    assert campaign.parse_campaign_command("STATUS LOOP telegram_operator")["loop_id"] == "TELEGRAM_OPERATOR"
    assert campaign.parse_campaign_command("SKIP LOOP telegram_operator LOOP-CERT-20260828T114525Z")["campaign_id"] == "LOOP-CERT-20260828T114525Z"


def test_unknown_explicit_campaign_never_falls_back(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch)
    response, metadata = hermes.handle_command("STATUS CAMPAIGN LOOP-CERT-UNKNOWN")
    assert metadata["route"] == "LOOP_CERTIFICATION_CONTROL"
    assert metadata["outcome"] == "UNKNOWN_CAMPAIGN"
    assert "could not find campaign" in response
    assert json.loads(campaign.CAMPAIGN_PATH.read_text())["state"] == "ACTIVE"


def test_natural_campaign_context_and_next_loop_gate(tmp_path, monkeypatch):
    campaign_id = _seed(tmp_path, monkeypatch)
    response, metadata = hermes.handle_command("what are you working on")
    assert metadata["campaign_id"] == campaign_id
    assert "Current loop: telegram_operator" in response
    assert "Outstanding unrelated repair: VOICE-001" in response
    assert "Current blocker: NONE" in response
    for command in ("Move to the next loop", f"NEXT LOOP {campaign_id}"):
        denied, denied_meta = hermes.handle_command(command)
        assert denied_meta["outcome"] == "NOT_READY"
        assert "not complete" in denied


def test_campaign_status_is_read_only_for_hermes_router(tmp_path, monkeypatch):
    campaign_id = _seed(tmp_path, monkeypatch)
    value = campaign.load_campaign()
    value["current_loop"] = "hermes_router"
    campaign._write(campaign.CAMPAIGN_PATH, value)
    response, metadata = hermes.handle_command(f"STATUS CAMPAIGN {campaign_id}")
    assert metadata["campaign_control_action"] == "STATUS"
    assert campaign.load_campaign()["certified_loops"] == []
    assert "Hermes Router" not in response


def test_real_router_event_satisfies_hermes_contract_and_registry(tmp_path, monkeypatch):
    campaign_id = _seed(tmp_path, monkeypatch)
    value = campaign.load_campaign()
    value["current_loop"] = "hermes_router"
    campaign._write(campaign.CAMPAIGN_PATH, value)
    result = campaign.observe_runtime_event(campaign_id=campaign_id, current_loop="hermes_router", incoming_update_id=123, route="GOVERNED_REPAIR_CONTROL", outcome="ANSWERED", metadata={"control_object": {"object_type": "REPAIR", "object_id": "VOICE-001"}, "repair_id": "VOICE-001", "work_order_id": "wo_b5a3b90892804ec79164159997caf264", "state": "WAITING_WORKER", "read_only": True, "repair_executed": False}, response_text="VOICE-001\nState: WAITING_WORKER\nNo repair was executed by this status request.", outgoing_message_id=456, delivered=True)
    assert result["newly_certified"] is True
    assert result["state"] == campaign.WAITING_NEXT
    registry = json.loads(campaign.CERT_REGISTRY_PATH.read_text())
    row = registry["loops"][0]
    assert row["certification_state"] == "NOT_TESTED"
    router = registry["loops"][1]
    assert router["certification_state"] == "REAL_WORLD_CERTIFIED"
    assert router["incoming_update_id"] == 123
    assert router["outgoing_message_id"] == 456


def test_campaign_status_delivery_does_not_certify_hermes_router(tmp_path, monkeypatch):
    campaign_id = _seed(tmp_path, monkeypatch)
    value = campaign.load_campaign(); value["current_loop"] = "hermes_router"; campaign._write(campaign.CAMPAIGN_PATH, value)
    result = campaign.record_delivery(campaign_id=campaign_id, update_id=123, outgoing_message_id=456, delivered=True)
    assert result["newly_certified"] is False
    assert campaign.load_campaign()["certified_loops"] == []
