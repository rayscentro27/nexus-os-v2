import json
from datetime import datetime, timezone
from pathlib import Path

from nexus_agent_platform.phase15.health_contract import _readiness_summary, _stripe_readiness


def _contract(**overrides):
    base = {
        "hermes": {"status": "BOUNDED_DEGRADED", "reason": "bridge not running"},
        "alpha": {"status": "DEGRADED", "reason": "Alpha not registered"},
        "nova": {"status": "DEGRADED", "reason": "Nova telegram worker not registered"},
        "loop_runtime": {"status": "HEALTHY", "reason": "loop records pass"},
        "daily_brief": {"status": "FRESH", "reason": "fresh"},
        "worker_pool": {"status": "PASS", "reason": "deterministic worker available"},
    }
    base.update(overrides)
    return base


def test_healthy_core_is_separate_from_disabled_optional_integrations(monkeypatch):
    monkeypatch.setenv("NEXUS_AUTONOMY_STRIPE_DISABLED", "1")
    summary = _readiness_summary(
        _contract(),
        _stripe_readiness({"live_key_present": True, "test_mode_confirmed": False}),
        mission_control_fresh=False,
    )
    assert summary["core_autonomy_runtime"]["status"] == "HEALTHY"
    assert summary["optional_integrations"]["alpha"]["status"] == "NOT_ENABLED"
    assert summary["optional_integrations"]["nova"]["status"] == "NOT_ENABLED"
    assert summary["optional_integrations"]["mission_control"]["status"] == "NOT_ENABLED"
    assert summary["safety_authority"]["stripe"]["state"] == "DISABLED"


def test_required_core_failure_fails_core_health(monkeypatch):
    monkeypatch.setenv("NEXUS_AUTONOMY_STRIPE_DISABLED", "1")
    summary = _readiness_summary(
        _contract(loop_runtime={"status": "DEGRADED", "reason": "missing ledger"}),
        _stripe_readiness({}),
        mission_control_fresh=True,
    )
    assert summary["core_autonomy_runtime"]["status"] == "FAIL"
    assert "loop_runtime" in summary["core_autonomy_runtime"]["failures"]


def test_live_stripe_proof_cannot_grant_autonomous_authority(monkeypatch):
    monkeypatch.delenv("NEXUS_AUTONOMY_STRIPE_DISABLED", raising=False)
    stripe = _stripe_readiness({"live_key_present": True, "test_mode_confirmed": True, "autonomous_execution_authorized": True})
    assert stripe["autonomous_execution_authorized"] is False
    assert stripe["safety_gate"] == "PASS"
    assert stripe["state"] == "DISABLED"


def test_optional_degradation_remains_visible(monkeypatch):
    monkeypatch.setenv("NEXUS_AUTONOMY_STRIPE_DISABLED", "1")
    summary = _readiness_summary(
        _contract(hermes={"status": "BOUNDED_DEGRADED", "reason": "bridge registered but idle"}),
        _stripe_readiness({}),
        mission_control_fresh=False,
    )
    assert summary["optional_integrations"]["hermes"]["status"] == "BOUNDED_DEGRADED"


def test_historical_stderr_is_not_a_current_health_input():
    summary = _readiness_summary(
        _contract(),
        _stripe_readiness({}),
        mission_control_fresh=True,
    )
    assert summary["core_autonomy_runtime"]["status"] == "HEALTHY"


def test_established_post_reboot_ledger_evidence_remains_valid():
    root = Path(__file__).resolve().parents[3]
    ledger = root / "data/runtime/nexus_loops/execution_ledger.jsonl"
    boot = datetime.fromisoformat("2026-08-21T11:29:40+00:00")
    rows = [
        json.loads(line)
        for line in ledger.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    post_boot = [
        row for row in rows
        if datetime.fromisoformat(row["completed_at"]) >= boot
    ]
    assert len(post_boot) >= 16
    assert all(row["result_status"] == "success" for row in post_boot)
    assert all(row["verifier_status"] == "pass" for row in post_boot)
    assert all(row["delta_status"] == "NO_CHANGE" for row in post_boot)
    assert all(row.get("scheduled_for") and row.get("input_hash") and row.get("material_hash") for row in post_boot)
