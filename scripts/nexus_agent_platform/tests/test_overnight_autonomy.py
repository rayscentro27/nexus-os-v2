import json
from pathlib import Path

from nexus_agent_platform import overnight_autonomy as overnight


def test_decision_trace_is_fact_only_and_model_routing_is_deterministic(tmp_path, monkeypatch):
    monkeypatch.setattr(overnight, "TRACE_DIR", tmp_path / "traces")
    trace = overnight.record_decision_trace(surface="telegram", message="/portfolio", intent="status", goal="read portfolio", authority_result="READ_ONLY", evidence_sources=["portfolio"], ray_action_required="NONE")
    assert trace["input_fingerprint"]
    assert trace["ray_action_required"] == "NONE"
    assert list((tmp_path / "traces").glob("*.json"))
    assert overnight.route_model("status")["role"] == "DETERMINISTIC_LOCAL"
    assert overnight.route_model("research")["role"] == "RESEARCH_REASONER"
    assert overnight.route_model("implementation")["role"] == "CODING_WORKER"


def test_integrity_critic_has_firewall_and_zero_authority():
    assert overnight.integrity_critic_review({"summary": "public design"})["action_authority"] == "NONE"
    assert overnight.integrity_critic_review({"token": "secret"})["status"] == "BLOCKED_INPUT_SENSITIVITY"


def test_idea_inbox_capture_dedupes_without_execution(tmp_path, monkeypatch):
    monkeypatch.setattr(overnight, "IDEA_PATH", tmp_path / "ideas.jsonl")
    first = overnight.capture_idea("IDEA: Explore a clearer admin dashboard")
    second = overnight.capture_idea("idea explore a clearer admin dashboard")
    assert first["status"] == "CAPTURED"
    assert second["status"] == "DUPLICATE"
    assert second["portfolio_objective_id"] is None
    assert overnight.list_ideas()["count"] == 2


def test_notification_is_deduplicated(tmp_path, monkeypatch):
    monkeypatch.setattr(overnight, "NOTIFIER_PATH", tmp_path / "notifications.jsonl")
    sent = []
    gate = {"gate_type": "HUMAN_SUBJECTIVE_TEST", "objective_id": "voice", "state": "READY", "exact_action": "test microphone"}
    assert overnight.notify_true_gate(gate, lambda text: sent.append(text) or True)["status"] == "SENT"
    assert overnight.notify_true_gate(gate, lambda text: sent.append(text) or True)["status"] == "DUPLICATE_SUPPRESSED"
    assert len(sent) == 1


def test_campaign_and_completion_audit_are_bounded(tmp_path, monkeypatch):
    monkeypatch.setattr(overnight, "CAMPAIGN_PATH", tmp_path / "campaign.json")
    monkeypatch.setattr(overnight, "CERT_DIR", tmp_path / "certification")
    campaign = overnight.arm_overnight_campaign(now="2026-08-25T20:00:00+00:00")
    assert campaign["status"] == "ARMED"
    audit = overnight.build_completion_audit(root=tmp_path)
    assert audit["status"] == "PARTIAL"
    assert (tmp_path / "certification/nexus_completion_audit_latest.json").exists()
