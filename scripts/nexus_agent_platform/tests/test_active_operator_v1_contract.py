import json

import scripts.operations.nexus_active_operator_runner as runner


def test_capability_registry_preserves_hard_gates():
    caps = runner.capability_snapshot()
    assert caps["searxng.research"]["status"] == "READY"
    assert caps["meta.inbound"]["status"] == "NOT_READY"
    assert caps["meta.publish"]["status"] == "GATED"
    assert caps["payments"]["authority"] == "NONE"


def test_canonical_work_order_is_stable_and_gated():
    finding = {"finding_id": "meta-inbound", "summary": "Webhook remediation", "reason": "missing", "category": "COMMUNICATION_STATE", "priority": "P2", "dedupe_key": "meta:inbound:v1", "approval_required": True, "action_class": "APPROVAL_REQUIRED", "proposed_action": "meta.inbound"}
    one = runner._canonical_work_order(finding, "meta.inbound", blocked=True)
    two = runner._canonical_work_order(finding, "meta.inbound", blocked=True)
    assert one["work_order_id"] == two["work_order_id"]
    assert one["status"] == "BLOCKED"
    assert one["execution_mode"] == "HUMAN_APPROVAL_REQUIRED"


def test_safe_receipt_has_no_external_side_effects():
    receipt = runner._safe_receipt("run", "read_operational_state", {"status": "COMPLETED"})
    assert receipt["external_side_effects"] is False
    assert "secret" not in json.dumps(receipt).lower()


def test_priority_is_deterministic_and_unready_is_lower():
    assert runner.priority_score({"priority": "P0", "capability_ready": True}) > runner.priority_score({"priority": "P2", "capability_ready": True})
    assert runner.priority_score({"priority": "P2", "capability_ready": False}) < runner.priority_score({"priority": "P2", "capability_ready": True})


def test_unknown_actions_are_never_auto_executed():
    assert runner.classify_action("llm.generated.shell") == "APPROVAL_REQUIRED"
    assert runner.classify_action("place_trade") == "NOT_AUTHORIZED"
