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
        "inventory": [{"loop_id": "telegram_operator", "loop_name": "Telegram Operator"}],
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


def test_real_delivery_certifies_telegram_loop_and_registry(tmp_path, monkeypatch):
    campaign_id = _seed(tmp_path, monkeypatch)
    result = campaign.record_delivery(campaign_id=campaign_id, update_id=123, outgoing_message_id=456, delivered=True)
    assert result["last_delivery_newly_certified"] is True
    assert result["state"] == campaign.WAITING_NEXT
    registry = json.loads(campaign.CERT_REGISTRY_PATH.read_text())
    row = registry["loops"][0]
    assert row["certification_state"] == "REAL_WORLD_CERTIFIED"
    assert row["real_world_certified"] is True
    assert json.loads(campaign.CAMPAIGN_PATH.read_text())["campaign_messages"][0]["outgoing_message_id"] == 456
