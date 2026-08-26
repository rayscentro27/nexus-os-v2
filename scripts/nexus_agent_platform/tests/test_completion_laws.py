from nexus_agent_platform.completion_laws import close_exact_gate, enforce_cycle_laws, evaluate_event


def test_partial_is_never_terminal_and_failures_create_recovery_work():
    assert evaluate_event({"status": "PARTIAL", "objective_id": "x"})["status"] == "ACTIVE"
    decision = evaluate_event({"status": "FAIL", "objective_id": "x", "stage": "S4", "machine_solvable": True})
    assert decision["status"] == "RECOVERING"
    assert "create_recovery_work" in decision["work"]


def test_unknown_solution_research_and_repeated_failure_alternative():
    decision = evaluate_event({"status": "FAIL", "objective_id": "x", "machine_solvable": True, "solution_known": False, "same_signature_count": 2})
    assert decision["diagnosis"] == "ARCHITECTURE_ALTERNATIVE"
    assert "bounded_research" in decision["work"]
    assert "architecture_alternative" in decision["work"]


def test_human_delivery_and_exact_reply_resume():
    blocked = evaluate_event({"status": "WAITING_HUMAN", "objective_id": "x", "gate_id": "gate-1"})
    assert blocked["status"] == "COMMUNICATION_FAIL"
    delivered = evaluate_event({"status": "WAITING_HUMAN", "objective_id": "x"}, hermes_delivery_verified=True)
    assert delivered["communication"] == "HERMES_DELIVERED"
    closed = close_exact_gate({"gate_id": "gate-1", "checkpoint_sha": "abc"}, reply_gate_id="gate-1", reply_decision="PASS")
    assert closed["campaign_action"] == "RESUME_FROM_CHECKPOINT"


def test_cycle_receipt_is_persisted(tmp_path):
    receipt = enforce_cycle_laws([{"status": "PARTIAL", "objective_id": "x"}], receipt_path=tmp_path / "laws.json")
    assert receipt["status"] == "PASS"
    assert receipt["terminal_partial_forbidden"] is True
    assert (tmp_path / "laws.json").exists()


def test_waiting_human_invokes_sender_before_waiting(tmp_path):
    sent = []

    def sender(brief):
        sent.append(brief)
        return {"delivered": True, "transport": "test", "delivery_id": "msg-1"}

    receipt = enforce_cycle_laws(
        [{"status": "WAITING_HUMAN", "objective_id": "x", "gate_id": "gate-1", "exact_ray_action": "Reply PASS gate-1"}],
        receipt_path=tmp_path / "laws.json", hermes_sender=sender,
    )
    assert len(sent) == 1
    assert receipt["decisions"][0]["status"] == "WAITING_HUMAN"
    assert receipt["decisions"][0]["delivery_receipt"]["delivered"] is True


def test_undelivered_human_gate_is_communication_failure(tmp_path):
    receipt = enforce_cycle_laws(
        [{"status": "WAITING_HUMAN", "objective_id": "x", "gate_id": "gate-2"}],
        receipt_path=tmp_path / "laws.json", hermes_sender=lambda brief: {"delivered": False},
    )
    assert receipt["decisions"][0]["status"] == "COMMUNICATION_FAIL"
