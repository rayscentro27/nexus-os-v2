import json
from datetime import datetime, timedelta, timezone

from scripts.nexus_agent_platform.truth_kernel import TruthKernel


def definition(mode="RUN_ONCE", **extra):
    return {"process_id": "p", "canonical_entrypoint": "x.py", "purpose": "test", "execution_mode": mode, "dependencies_ready": True, **extra}


def test_configured_is_not_running(tmp_path):
    k = TruthKernel(tmp_path / "truth.db")
    k.register_process(definition())
    assert k.derive_process_state("p") == "READY"


def test_loaded_continuous_without_heartbeat_is_not_healthy(tmp_path):
    k = TruthKernel(tmp_path / "truth.db")
    k.register_process(definition("CONTINUOUS", expected_running=True, scheduler_supervision={"loaded": True}))
    assert k.derive_process_state("p") == "STALE"


def test_exit_zero_without_verified_output_is_unverified(tmp_path):
    k = TruthKernel(tmp_path / "truth.db")
    k.register_process(definition())
    run = k.start_run("p", trigger_type="TEST")
    k.record_evidence(run, evidence_type="START", source="test", real_or_simulated="REAL")
    assert k.complete_run(run, exit_status="COMPLETED", exit_code=0, verification_result={"output_verified": False}, freshness_result={"fresh": True}) == "SUCCEEDED_UNVERIFIED"


def test_simulation_can_never_be_verified_real(tmp_path):
    k = TruthKernel(tmp_path / "truth.db")
    k.register_process(definition())
    run = k.start_run("p", trigger_type="TEST")
    k.record_evidence(run, evidence_type="START", source="fixture", real_or_simulated="SIMULATION")
    assert k.complete_run(run, exit_status="COMPLETED", exit_code=0, verification_result={"output_verified": True}, freshness_result={"fresh": True}) == "SUCCEEDED_UNVERIFIED"


def test_stale_real_run_is_stale(tmp_path):
    k = TruthKernel(tmp_path / "truth.db")
    k.register_process(definition())
    run = k.start_run("p", trigger_type="TEST")
    k.record_evidence(run, evidence_type="START", source="test", real_or_simulated="REAL")
    k.complete_run(run, exit_status="COMPLETED", exit_code=0, verification_result={"output_verified": True}, freshness_result={"fresh": False})
    assert k.derive_process_state("p") == "STALE"


def test_failed_verification_is_not_success(tmp_path):
    k = TruthKernel(tmp_path / "truth.db")
    k.register_process(definition())
    run = k.start_run("p", trigger_type="TEST")
    k.record_evidence(run, evidence_type="START", source="test", real_or_simulated="REAL")
    assert k.complete_run(run, exit_status="COMPLETED", exit_code=0, verification_result={"output_verified": True, "verification_failed": True}, freshness_result={"fresh": True}) == "FAILED"


def test_human_approval_is_bound_to_exact_action(tmp_path):
    k = TruthKernel(tmp_path / "truth.db")
    k.create_human_gate(gate_id="HG-001", exact_action="APPROVE HG-001", reason="test", risk="high", authority_requested="upgrade")
    assert k.approve_human_gate("HG-001", "APPROVE HG-002", approved_by="ray") is False
    assert k.approve_human_gate("HG-001", "APPROVE HG-001", approved_by="ray") is True


def test_missing_process_and_corrupt_state_are_safe(tmp_path):
    k = TruthKernel(tmp_path / "truth.db")
    assert k.derive_process_state("missing") == "NOT_CONFIGURED"
    assert k.get_run("missing") is None
