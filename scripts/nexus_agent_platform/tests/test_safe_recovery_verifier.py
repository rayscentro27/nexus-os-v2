from __future__ import annotations

import json
import plistlib
from pathlib import Path

from scripts.systems import verify_safe_recovery as recovery


def test_recovery_definition_audit_requires_canonical_disabled_plists(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    for folder in ("ops/launchd", "configs/launchd"):
        (root / folder).mkdir(parents=True)
    for folder in ("ops/launchd", "configs/launchd"):
        for label in ("scheduler", "dispatcher"):
            item = {
                "Label": f"com.nexus.{label}",
                "ProgramArguments": [str(root / ".venv/bin/python"), str(root / "scripts" / f"{label}.py")],
                "RunAtLoad": False,
                "KeepAlive": False,
                "Disabled": True,
            }
            (root / folder / f"com.nexus.{label}.plist").write_bytes(plistlib.dumps(item))
    monkeypatch.setattr(recovery, "REPO", root)
    assert recovery._definitions_are_canonical() == (True, [])
    path = root / "configs/launchd/com.nexus.scheduler.plist"
    item = plistlib.loads(path.read_bytes())
    item["ProgramArguments"][0] = "/Users/raymonddavis/nexus-os-v2/.venv/bin/python"
    path.write_bytes(plistlib.dumps(item))
    ok, problems = recovery._definitions_are_canonical()
    assert not ok and any(value.startswith("NONCANONICAL_PATH") for value in problems)


def test_historical_request_without_migration_authority_is_never_eligible():
    from nexus_agent_platform.task_request_eligibility import task_request_is_dispatch_eligible
    for status in ("requested", "assigned", "approved"):
        assert not task_request_is_dispatch_eligible({"status": status, "payload": {}})
    assert not task_request_is_dispatch_eligible({
        "status": "approved", "approved_by_ray": True,
        "payload": {"nexus_dispatch_eligibility": "CURRENT_V2_MIGRATED"},
    })


def test_recovery_command_has_no_mutating_or_execution_authority():
    source = Path(recovery.__file__).read_text(encoding="utf-8")
    assert '"mutates_state": False' in source
    assert '"creates_business_work": False' in source
    assert '"calls_paid_providers": False' in source
    assert '"starts_services": False' in source


def test_frozen_recovery_baseline_is_pre_activation_and_secret_free():
    path = recovery.REPO / "reports/recovery/NEXUS_RECOVERY_BASELINE_20261009.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["STATUS"] == "PRE_ACTIVATION_RECOVERY_BASELINE"
    assert data["CANONICAL_REPO"] == str(recovery.REPO)
    assert data["EXPECTED_SCHEDULER_STATE"] == "OFF"
    assert data["EXPECTED_DISPATCHER_STATE"] == "OFF"
    assert data["AUTONOMOUS_ENABLEMENT"] is False
    assert data["SECRET_VALUES_INCLUDED"] is False
    assert len(data["RECOVERY_CRITICAL_FILE_HASHES"]) >= 8
    assert recovery.verify.__module__ == "scripts.systems.verify_safe_recovery"
    assert data["CANONICAL_SOURCE_PATHS"] == recovery.CANONICAL_SOURCE_PATHS


def test_supabase_recovery_health_uses_bounded_timeout_and_read_only_select(tmp_path, monkeypatch):
    ref_path = tmp_path / "project-ref"
    ref_path.write_text("iqjwgpnujbeoyaeuwehj\n", encoding="utf-8")
    monkeypatch.setattr(recovery, "PROJECT_REF_PATH", ref_path)
    captured = {}

    def query(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return recovery.subprocess.CompletedProcess(
            args, 0, json.dumps({"rows": [{"health": 1}]}), ""
        )

    monkeypatch.setattr(recovery.subprocess, "run", query)
    assert recovery._supabase_readonly_health() == "READ_ONLY_SELECT_PASS"
    assert captured["kwargs"]["timeout"] == 45.0
    assert captured["args"][-1] == "select 1 as health;"
