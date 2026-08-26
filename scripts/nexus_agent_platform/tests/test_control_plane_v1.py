import json
from pathlib import Path

import pytest

from nexus_agent_platform.capability_broker import load_manifest, run_capability, run_safe_canaries
from nexus_agent_platform.hermes_operator import operate, resolve
from nexus_agent_platform.process_broker import read_processes
from nexus_agent_platform.proof_watchdog import audit


def test_manifest_is_unique_and_arbitrary_shell_prohibited():
    manifest = load_manifest()
    ids = [row["capability_id"] for row in manifest["capabilities"]]
    assert len(ids) == len(set(ids))
    assert manifest["arbitrary_shell"] == "PROHIBITED"
    assert any(row["availability"] == "PROHIBITED" for row in manifest["capabilities"])


def test_cli_broker_rejects_injection_and_absolute_paths(tmp_path):
    manifest = load_manifest()
    with pytest.raises(ValueError):
        run_capability("tests.run", {"test_path": "x; rm -rf tmp"}, manifest=manifest, receipt_dir=tmp_path)
    with pytest.raises(ValueError):
        run_capability("tests.run", {"test_path": "/tmp/test"}, manifest=manifest, receipt_dir=tmp_path)


def test_cli_broker_runs_fixed_template_and_writes_receipt(tmp_path):
    manifest = load_manifest()
    result = run_capability("tests.run", {"test_path": "scripts/nexus_agent_platform/tests/test_python_registry.py"}, manifest=manifest, receipt_dir=tmp_path)
    assert result["status"] in {"PASS", "FAIL"}
    assert result["command"][:3] == ["npm", "run", "test"]
    assert list(tmp_path.glob("rcpt_*.json"))


def test_hermes_routes_only_registered_capabilities():
    assert resolve("Run the system health audit") == "system.health"
    assert resolve("Run the Forex research process") == "forex.research"
    assert operate("do something unsupported") ["status"] == "UNKNOWN"
    assert operate("show me what tools you can use")["status"] == "PASS"


def test_process_registry_does_not_claim_pid_without_fresh_heartbeat(tmp_path):
    path = tmp_path / "processes.json"
    path.write_text(json.dumps([{"process_id": "old", "pid": 999999, "last_heartbeat": "2020-01-01T00:00:00+00:00"}]))
    result = read_processes(path)
    assert result["running_count"] == 0
    assert result["processes"][0]["runtime_state"] == "UNKNOWN"


def test_proof_watchdog_diagnoses_first_missing_stage():
    result = audit([{"objective_id": "voice", "executor": "voice", "health": "RUNNING", "last_confirmed_stage": "S3_RECEIVER_ACKNOWLEDGED", "next_expected_stage": "S4_EXECUTOR_STARTED", "proof_refs": ["S0_SCHEDULED", "S1_SELECTED", "S2_HANDOFF_CREATED", "S3_RECEIVER_ACKNOWLEDGED"]}])
    assert result["proof_watchdog"] == "PASS"
    assert result["objectives"][0]["failure_stage"] == "S4_EXECUTOR_STARTED"
    assert result["objectives"][0]["health"] == "STALLED"


def test_safe_preflight_excludes_production_and_prohibited(tmp_path):
    result = run_safe_canaries(receipt_dir=tmp_path)
    rows = {row["capability_id"]: row for row in result["matrix"]}
    assert rows["release.production_promote"]["canary"] == "NOT_RUN"
    assert rows["trading.funded"]["canary"] == "NOT_RUN"
    assert result["arbitrary_shell"] == "PROHIBITED"
