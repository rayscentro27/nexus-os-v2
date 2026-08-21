import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts.operations import nexus_recovery_check as recovery


def _now():
    return datetime.now(timezone.utc)


def _healthy_inputs(now):
    stamp = now.isoformat()
    return ([{"process_id": "idle", "enabled": True, "last_status": "simulated", "schedule_type": "hourly"}],
            {"status": "HEALTHY", "last_exit_code": 0, "last_heartbeat": stamp, "cadence_seconds": 3600},
            {"operator_health": "HEALTHY", "last_successful_run": stamp},
            {"optional_integrations": {"alpha": {"status": "NOT_ENABLED"}, "nova": {"status": "NOT_ENABLED"}, "hermes": {"status": "DEGRADED"}, "mission_control": {"status": "NOT_ENABLED"}}})


def test_healthy_core_and_disabled_optionals_are_not_actionable():
    now = _now()
    findings = recovery.inspect_components(now=now, registry=_healthy_inputs(now)[0], scheduler=_healthy_inputs(now)[1], operator_heartbeat=_healthy_inputs(now)[2], live_status=_healthy_inputs(now)[3])
    assert all(item["status"] == "HEALTHY" for item in findings if item["required"])
    assert {item["component"] for item in findings if item["status"] == "NOT_ENABLED"} >= {"alpha", "nova", "mission_control"}
    assert recovery.classify_action("stripe.live_charge") == "NOT_AUTHORIZED"
    assert recovery.classify_action("restart_component") == "APPROVAL_REQUIRED"


def test_required_failure_is_classified_without_execution():
    now = _now()
    registry, scheduler, heartbeat, optional = _healthy_inputs(now)
    scheduler["status"] = "FAILED"
    findings = recovery.inspect_components(now=now, registry=registry, scheduler=scheduler, operator_heartbeat=heartbeat, live_status=optional)
    loop = next(item for item in findings if item["component"] == "continuous_loop")
    assert loop["status"] == "FAILED" and loop["required"]
    assert recovery.classify_action("restart_component") == "APPROVAL_REQUIRED"


def test_hourly_idle_and_historical_stderr_do_not_become_stale(tmp_path, monkeypatch):
    now = _now()
    registry, scheduler, heartbeat, optional = _healthy_inputs(now)
    registry[0]["last_status"] = "simulated"
    findings = recovery.inspect_components(now=now, registry=registry, scheduler=scheduler, operator_heartbeat=heartbeat, live_status=optional)
    assert next(item for item in findings if item["component"] == "process_registry")["status"] == "HEALTHY"
    assert recovery.inspect_components(now=now, registry=registry, scheduler=scheduler, operator_heartbeat=heartbeat, live_status=optional)


def test_duplicate_condition_is_suppressed(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path / "governed"))
    finding = {"component": "continuous_loop", "status": "FAILED", "reason": "test failure", "required": True, "artifact": "scheduler.json"}
    first = recovery.create_escalation(finding)
    second = recovery.create_escalation(finding)
    assert first["status"] == "CREATED"
    assert second["status"] == "DUPLICATE_SUPPRESSED"


def test_environment_and_unauthorized_boundaries(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "must-not-survive")
    recovery._sanitize_autonomy_environment()
    assert "STRIPE_SECRET_KEY" not in os.environ
    assert os.environ["NEXUS_AUTONOMY_STRIPE_DISABLED"] == "1"
    for action in ("stripe.live_charge", "funded_trade", "external_message.send", "shell.arbitrary", "approval.bypass"):
        assert recovery.classify_action(action) == "NOT_AUTHORIZED"


def test_corrupt_state_fails_safe():
    findings = recovery.inspect_components(now=_now(), registry={"bad": True}, scheduler={}, operator_heartbeat={}, live_status={})
    assert any(item["status"] == "FAILED" for item in findings if item["required"])


def test_overlapping_run_is_skipped(tmp_path):
    lock = tmp_path / "recovery.lock"
    with recovery.single_run_lock(lock) as acquired:
        assert acquired
        with recovery.single_run_lock(lock) as second:
            assert second is False
