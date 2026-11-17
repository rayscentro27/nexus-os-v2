import sys
from pathlib import Path

S1 = Path.home() / ".nexus/releases/nexus-systems-engine-s1-20261028"
sys.path.insert(0, str(S1))

import pytest
from systems_engine_s1.db import connect, create_approval, decide_approval, validate_approval
from systems_engine_s1_batch_d.bridge import validate_request


def request(operation, *, context=None, payload=None):
    return {
        "request_id": "test-request", "caller": "NOVA_NEXUS", "operation": operation,
        "environment_id": "MAC_MINI", "scope": "test", "idempotency_key": "test-idem",
        "approval_context": context or {}, "reason": "approval contract test", "payload": payload or {},
    }


def make_approval(db, **overrides):
    values = {"operation": "systems.install_technology", "target_component": "OpenCode / REA integration",
              "target_environment": "MAC_MINI", "target_scope": "/Users/raymonddavis/.config/opencode/opencode.jsonc",
              "requested_by": "test-ray-via-nova", "reason_or_summary": "Bounded approval contract test"}
    values.update(overrides)
    return create_approval(db, **values)


def test_pending_approval_rejected():
    with connect(":memory:") as db:
        row = make_approval(db)
        result = validate_approval(db, **{k: row[k] for k in ("approval_reference", "operation", "target_component", "target_environment", "target_scope")})
        assert result == {"valid": False, "reason": "APPROVAL_STATUS_PENDING"}


def test_matching_approved_reference_accepted():
    with connect(":memory:") as db:
        row = make_approval(db)
        decide_approval(db, row["approval_reference"], "APPROVE", decision_by="ray", explicit_ray_decision=True)
        result = validate_approval(db, **{k: row[k] for k in ("approval_reference", "operation", "target_component", "target_environment", "target_scope")})
        assert result["valid"] is True


@pytest.mark.parametrize("field,value", [("operation", "systems.rollback"), ("target_component", "Other"),
    ("target_environment", "ORACLE"), ("target_scope", "/tmp/other.json")])
def test_binding_mismatch_rejected(field, value):
    with connect(":memory:") as db:
        row = make_approval(db)
        decide_approval(db, row["approval_reference"], "APPROVE", decision_by="ray", explicit_ray_decision=True)
        bound = {k: row[k] for k in ("approval_reference", "operation", "target_component", "target_environment", "target_scope")}
        bound[field] = value
        assert validate_approval(db, **bound)["valid"] is False


def test_expired_reference_rejected():
    with connect(":memory:") as db:
        row = make_approval(db)
        db.execute("UPDATE approvals SET expires_at='2000-01-01T00:00:00+00:00' WHERE approval_reference=?", (row["approval_reference"],))
        decide_approval(db, row["approval_reference"], "APPROVE", decision_by="ray", explicit_ray_decision=True)
        result = validate_approval(db, **{k: row[k] for k in ("approval_reference", "operation", "target_component", "target_environment", "target_scope")})
        assert result["valid"] is False


def test_consumed_reference_rejected():
    with connect(":memory:") as db:
        row = make_approval(db)
        decide_approval(db, row["approval_reference"], "APPROVE", decision_by="ray", explicit_ray_decision=True)
        bound = {k: row[k] for k in ("approval_reference", "operation", "target_component", "target_environment", "target_scope")}
        assert validate_approval(db, **bound, consume=True)["valid"] is True
        assert validate_approval(db, **bound)["reason"] == "APPROVAL_STATUS_CONSUMED"


def test_denied_reference_rejected():
    with connect(":memory:") as db:
        row = make_approval(db)
        decide_approval(db, row["approval_reference"], "DENY", decision_by="ray", explicit_ray_decision=True)
        bound = {k: row[k] for k in ("approval_reference", "operation", "target_component", "target_environment", "target_scope")}
        assert validate_approval(db, **bound)["reason"] == "APPROVAL_STATUS_DENIED"


def test_non_ray_decision_rejected():
    with connect(":memory:") as db:
        row = make_approval(db)
        with pytest.raises(PermissionError, match="APPROVAL_DECISION_AUTHORITY_REQUIRED"):
            decide_approval(db, row["approval_reference"], "APPROVE", decision_by="nova", explicit_ray_decision=True)


def test_production_sentinel_rejected():
    payload = {"operation": "systems.install_technology", "target_component": "OpenCode / REA integration",
        "target_environment": "MAC_MINI", "target_scope": "/Users/raymonddavis/.config/opencode/opencode.jsonc",
        "requested_by": "ray", "reason_or_summary": "DISPOSABLE_TEST_APPROVED"}
    with pytest.raises(PermissionError, match="DISPOSABLE_APPROVAL_SENTINEL_DENIED_FOR_PRODUCTION"):
        validate_request(request("systems.approval_request", payload=payload))


def test_approval_reference_is_opaque_and_durable_shape():
    with connect(":memory:") as db:
        row = make_approval(db)
        assert row["approval_reference"].startswith("sysapproval_")
        assert len(row["approval_reference"].removeprefix("sysapproval_")) == 48
        assert db.execute("SELECT 1 FROM approvals WHERE approval_reference=?", (row["approval_reference"],)).fetchone()


def test_decision_requires_explicit_ray_boundary():
    with connect(":memory:") as db:
        row = make_approval(db)
        with pytest.raises(PermissionError):
            decide_approval(db, row["approval_reference"], "APPROVE", decision_by="ray", explicit_ray_decision=False)

