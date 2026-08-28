from pathlib import Path

from nexus_agent_platform.human_gate_router import create_gate, parse_response, route_response
from nexus_agent_platform.truth_kernel import TruthKernel


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


def kernel_gate(tmp_path: Path, gate_id="HG-001", **kwargs):
    kernel = TruthKernel(tmp_path / "truth.db")
    kernel.create_human_gate(gate_id=gate_id, exact_action=f"APPROVE {gate_id}", reason="test", risk="low", authority_requested="bounded-test", **kwargs)
    return kernel


def test_truth_kernel_gate_authorized_exact_approval_and_replay_are_durable(tmp_path: Path):
    kernel = kernel_gate(tmp_path)
    first = route_response("APPROVE HG-001", chat_id=42, authorized_chat_ids={42}, truth_kernel_db_path=kernel.db_path)
    assert first["outcome"] == "APPROVED"
    assert kernel.get_human_gate("HG-001")["status"] == "APPROVED"
    events = kernel._connect().execute("SELECT outcome FROM human_gate_events WHERE gate_id='HG-001'").fetchall()
    assert [row[0] for row in events] == ["APPROVED"]
    replay = route_response("APPROVE HG-001", chat_id=42, authorized_chat_ids={42}, truth_kernel_db_path=kernel.db_path)
    assert replay["outcome"] == "DENIED_REPLAY_OR_CLOSED"


def test_truth_kernel_gate_rejects_unauthorized_chat_and_wrong_gate(tmp_path: Path):
    kernel = kernel_gate(tmp_path)
    denied = route_response("APPROVE HG-001", chat_id=99, authorized_chat_ids={42}, truth_kernel_db_path=kernel.db_path)
    assert denied["outcome"] == "DENIED_UNAUTHORIZED_CHAT"
    assert kernel.get_human_gate("HG-001")["status"] == "PENDING"
    wrong = route_response("APPROVE UNKNOWN", chat_id=42, authorized_chat_ids={42}, truth_kernel_db_path=kernel.db_path)
    assert wrong["outcome"] == "DENIED_UNKNOWN_GATE"


def test_truth_kernel_gate_wrong_action_hold_and_malformed_fail_closed(tmp_path: Path):
    kernel = kernel_gate(tmp_path)
    wrong = route_response("APPROVE HG-001 extra", chat_id=42, authorized_chat_ids={42}, truth_kernel_db_path=kernel.db_path)
    assert wrong["outcome"] == "DENIED_MALFORMED"
    held = route_response("HOLD HG-001", chat_id=42, authorized_chat_ids={42}, truth_kernel_db_path=kernel.db_path)
    assert held["outcome"] == "HOLD_NOT_APPROVED"
    assert kernel.get_human_gate("HG-001")["status"] == "PENDING"
    malformed = route_response("APPROVE", chat_id=42, authorized_chat_ids={42}, truth_kernel_db_path=kernel.db_path)
    assert malformed["outcome"] == "DENIED_MALFORMED"


def test_truth_kernel_gate_expiry_and_exact_action_binding(tmp_path: Path):
    kernel = TruthKernel(tmp_path / "truth.db")
    kernel.create_human_gate(gate_id="HG-EXP", exact_action="APPROVE HG-EXP", reason="test", risk="low", authority_requested="bounded-test", expires_at="2000-01-01T00:00:00+00:00")
    expired = route_response("APPROVE HG-EXP", chat_id=42, authorized_chat_ids={42}, truth_kernel_db_path=kernel.db_path)
    assert expired["outcome"] == "DENIED_EXPIRED"
    kernel.create_human_gate(gate_id="HG-ACT", exact_action="APPROVE DIFFERENT", reason="test", risk="low", authority_requested="bounded-test")
    action = route_response("APPROVE HG-ACT", chat_id=42, authorized_chat_ids={42}, truth_kernel_db_path=kernel.db_path)
    assert action["outcome"] == "DENIED_WRONG_ACTION"
