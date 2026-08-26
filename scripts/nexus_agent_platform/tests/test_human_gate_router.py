from pathlib import Path

from nexus_agent_platform.human_gate_router import create_gate, parse_response, route_response


def test_parse_is_bounded():
    assert parse_response("ACK TEST gate-1") == {"action": "ACK_TEST", "gate_id": "gate-1", "explanation": ""}
    assert parse_response("please approve gate-1") is None


def test_exact_gate_closes_and_resumes(tmp_path: Path):
    ledger = tmp_path / "ledger.json"
    create_gate("gate-1", objective_id="communication", candidate_sha="a" * 40, path=ledger)
    sent = []
    result = route_response("ACK TEST gate-1", path=ledger, sender=lambda text: sent.append(text) or {"delivered": True, "delivery_id": "m1"})
    assert result["outcome"] == "CLOSED"
    assert result["resume"]["campaign_action"] == "RESUME_FROM_CHECKPOINT"
    assert result["confirmation_delivered"] is True
    assert "gate-1" in sent[0]
    again = route_response("ACK TEST gate-1", path=ledger)
    assert again["outcome"] == "ALREADY_CLOSED"


def test_unknown_and_wrong_gate_do_not_mutate(tmp_path: Path):
    ledger = tmp_path / "ledger.json"
    create_gate("gate-2", objective_id="communication", candidate_sha="b" * 40, path=ledger)
    assert route_response("ACK TEST unknown", path=ledger)["outcome"] == "UNKNOWN_GATE"
    assert route_response("PASS gate-2", path=ledger)["outcome"] == "WRONG_RESPONSE_TYPE"
