import json
from pathlib import Path

from nexus_agent_platform.resume_consumer import consume_resume_receipt


def test_resume_consumer_proves_real_next_action(tmp_path: Path, monkeypatch):
    ledger = tmp_path / "ledger.json"
    receipt_dir = tmp_path / "receipts"
    monkeypatch.setattr("nexus_agent_platform.resume_consumer.RECEIPTS", receipt_dir)
    monkeypatch.setattr("nexus_agent_platform.resume_consumer.ROOT", tmp_path)
    (tmp_path / "data/runtime").mkdir(parents=True)
    (tmp_path / "data/runtime/nexus_completion_campaign.json").write_text(json.dumps({
        "campaign_id": "test-campaign", "current_wave": 18,
        "remaining_work": ["voice_access"], "checkpoint_sha": "a" * 40,
    }))
    ledger.write_text(json.dumps({"gates": [{
        "gate_id": "gate-resume", "status": "CLOSED",
        "resume_receipt": {"receipt_id": "resume-gate-resume", "checkpoint_sha": "a" * 40},
    }]}))
    def fake_run(*args, **kwargs):
        kwargs["receipt_dir"].mkdir(parents=True, exist_ok=True)
        (kwargs["receipt_dir"] / "rcpt-test.json").write_text("{}")
        return {"status": "PASS", "receipt_id": "rcpt-test"}
    monkeypatch.setattr("nexus_agent_platform.resume_consumer.run_capability", fake_run)
    result = consume_resume_receipt(ledger_path=ledger)
    assert result["status"] == "RECONCILED"
    assert result["receiver_ack"] == "PASS"
    assert result["verification"] == "PASS"
