import sqlite3
import pytest

from scripts.nexus_agent_platform.truth_kernel import TruthKernel


def definition(mode="RUN_ONCE", **extra):
    return {"process_id": "p", "canonical_entrypoint": "x.py", "purpose": "test",
            "execution_mode": mode, "dependencies_ready": True,
            "authority_contract": {"required": True}, **extra}


def base_run(k, *, output=(), authority=None, dependencies=None, side_expected=None, side_observed=None):
    run = k.start_run("p", trigger_type="TEST")
    k.mark_run_started(run, started_at="2026-08-28T00:00:00+00:00")
    k.record_authority_result(run, authority or {"authorized": True})
    k.record_dependency_result(run, dependencies or {"available": True})
    k.record_evidence(run, evidence_type="EXECUTION", source="test")
    state = k.complete_run(run, exit_status="COMPLETED", exit_code=0,
                           verification_result={"output_verified": bool(output)},
                           freshness_result={"fresh": True}, output_artifacts=output,
                           side_effect_expected=side_expected or {}, side_effect_observed=side_observed or {})
    return run, state


def test_configured_is_not_running(tmp_path):
    k = TruthKernel(tmp_path / "truth.db"); k.register_process(definition())
    assert k.derive_process_state("p") == "READY"
    assert k.get_process_status("p")["RUNNING"] is False


def test_requested_is_not_running_until_marked_started(tmp_path):
    k = TruthKernel(tmp_path / "truth.db"); k.register_process(definition())
    run = k.start_run("p", trigger_type="TEST")
    assert k.derive_process_state("p") == "PENDING_EXECUTION"
    k.mark_run_started(run, started_at="2026-08-28T00:00:00+00:00")
    assert k.derive_process_state("p") == "RUNNING"


def test_loaded_continuous_without_heartbeat_is_not_healthy(tmp_path):
    k = TruthKernel(tmp_path / "truth.db")
    k.register_process(definition("CONTINUOUS", expected_running=True, scheduler_supervision={"loaded": True}))
    assert k.derive_process_state("p") == "STALE"


def test_exit_zero_without_verified_output_is_unverified(tmp_path):
    k = TruthKernel(tmp_path / "truth.db"); k.register_process(definition())
    _, state = base_run(k)
    assert state == "SUCCEEDED_UNVERIFIED"


@pytest.mark.parametrize("realness", ["SIMULATION", "DRY_RUN", "SAFE_SYNTHETIC"])
def test_non_real_evidence_never_proves_real(tmp_path, realness):
    k = TruthKernel(tmp_path / "truth.db"); k.register_process(definition())
    run = k.start_run("p", trigger_type="TEST"); k.mark_run_started(run)
    k.record_authority_result(run, {"authorized": True}); k.record_dependency_result(run, {"available": True})
    k.record_evidence(run, evidence_type="EXECUTION", source="fixture", real_or_simulated=realness)
    assert k.complete_run(run, exit_status="COMPLETED", exit_code=0,
                          verification_result={"output_verified": True}, freshness_result={"fresh": True}) == "SUCCEEDED_UNVERIFIED"


def test_authority_denied_and_missing_block_success(tmp_path):
    for i, authority in enumerate(({"authorized": False}, {})):
        k = TruthKernel(tmp_path / f"authority{i}.db"); k.register_process(definition())
        run = k.start_run("p", trigger_type="TEST"); k.mark_run_started(run)
        k.record_authority_result(run, authority); k.record_dependency_result(run, {"available": True})
        k.record_evidence(run, evidence_type="EXECUTION", source="test")
        assert k.complete_run(run, exit_status="COMPLETED", exit_code=0,
                              verification_result={"output_verified": True}, freshness_result={"fresh": True}) == "BLOCKED_AUTHORITY"


def test_dependency_failure_blocks_success(tmp_path):
    k = TruthKernel(tmp_path / "truth.db"); k.register_process(definition())
    run = k.start_run("p", trigger_type="TEST"); k.mark_run_started(run)
    k.record_authority_result(run, {"authorized": True}); k.record_dependency_result(run, {"available": False})
    k.record_evidence(run, evidence_type="EXECUTION", source="test")
    assert k.complete_run(run, exit_status="COMPLETED", exit_code=0,
                          verification_result={"output_verified": True}, freshness_result={"fresh": True}) == "BLOCKED_DEPENDENCY"


def test_side_effect_mismatch_is_not_verified(tmp_path):
    k = TruthKernel(tmp_path / "truth.db"); k.register_process(definition())
    _, state = base_run(k, side_expected={"mutations": 0}, side_observed={"mutations": 1})
    assert state == "FAILED"


def test_required_output_missing_and_boolean_alone_not_enough(tmp_path):
    k = TruthKernel(tmp_path / "truth.db"); k.register_process(definition(output_contract={"artifacts": [str(tmp_path / "required.json")] }))
    _, state = base_run(k, output=())
    assert state == "SUCCEEDED_UNVERIFIED"


def test_real_verified_output_derives_success(tmp_path):
    k = TruthKernel(tmp_path / "truth.db")
    output = tmp_path / "out.json"; output.write_text("{}")
    k.register_process(definition(output_contract={"artifacts": [str(output)]}))
    run = k.start_run("p", trigger_type="TEST"); k.mark_run_started(run)
    k.record_authority_result(run, {"authorized": True}); k.record_dependency_result(run, {"available": True})
    hashes = k.record_output(run, [output])
    k.record_evidence(run, evidence_type="EXECUTION", source="test")
    k.record_evidence(run, evidence_type="OUTPUT", source="test", artifact=str(output), artifact_hash=hashes[str(output)])
    assert k.complete_run(run, exit_status="COMPLETED", exit_code=0,
                          verification_result={"output_verified": True}, freshness_result={"fresh": True},
                          output_artifacts=[output], side_effect_expected={"mutations": 0}, side_effect_observed={"mutations": 0}) == "SUCCEEDED_VERIFIED"


def test_dynamic_freshness_expires_at_read_time(tmp_path):
    k = TruthKernel(tmp_path / "truth.db"); k.register_process(definition(freshness_contract={"max_age_seconds": 300}))
    output = tmp_path / "out.txt"; output.write_text("ok")
    run = k.start_run("p", trigger_type="TEST"); k.mark_run_started(run, started_at="2026-08-28T00:00:00+00:00")
    k.record_authority_result(run, {"authorized": True}); k.record_dependency_result(run, {"available": True})
    hashes = k.record_output(run, [output]); k.record_evidence(run, evidence_type="EXECUTION", source="test")
    k.record_evidence(run, evidence_type="OUTPUT", source="test", artifact=str(output), artifact_hash=hashes[str(output)])
    assert k.complete_run(run, exit_status="COMPLETED", exit_code=0, verification_result={"output_verified": True}, freshness_result={"fresh": True}, output_artifacts=[output], completed_at="2026-08-28T00:00:10+00:00") == "SUCCEEDED_VERIFIED"
    assert k.derive_process_state("p", now="2026-08-28T00:02:00+00:00") == "SUCCEEDED_VERIFIED"
    assert k.derive_process_state("p", now="2026-08-28T00:06:00+00:00") == "STALE"


def test_continuous_heartbeat_is_dynamic(tmp_path):
    k = TruthKernel(tmp_path / "truth.db"); k.register_process(definition("CONTINUOUS", expected_running=True, heartbeat_interval_seconds=60))
    run = k.start_run("p", trigger_type="OBSERVED"); k.mark_run_started(run, started_at="2026-08-28T00:00:00+00:00")
    assert k.derive_process_state("p", now="2026-08-28T00:00:30+00:00") == "STALE"
    k.record_heartbeat(run, heartbeat_at="2026-08-28T00:00:20+00:00", cycle_count=1)
    assert k.derive_process_state("p", now="2026-08-28T00:00:30+00:00") == "RUNNING"
    assert k.derive_process_state("p", now="2026-08-28T00:02:00+00:00") == "STALE"


def test_expired_gate_cannot_be_approved(tmp_path):
    k = TruthKernel(tmp_path / "truth.db")
    k.create_human_gate(gate_id="HG-001", exact_action="APPROVE HG-001", reason="test", risk="high", authority_requested="upgrade", expires_at="2026-08-28T00:00:00+00:00")
    assert k.approve_human_gate("HG-001", "APPROVE HG-001", approved_by="ray", now="2026-08-28T00:00:01+00:00") is False


def test_human_approval_exact_action(tmp_path):
    k = TruthKernel(tmp_path / "truth.db")
    k.create_human_gate(gate_id="HG-001", exact_action="APPROVE HG-001", reason="test", risk="high", authority_requested="upgrade")
    assert k.approve_human_gate("HG-001", "APPROVE HG-002", approved_by="ray") is False
    assert k.approve_human_gate("HG-001", "APPROVE HG-001", approved_by="ray") is True


def test_foreign_keys_reject_orphans(tmp_path):
    k = TruthKernel(tmp_path / "truth.db")
    with pytest.raises(sqlite3.IntegrityError):
        with k._connect() as db:
            db.execute("INSERT INTO evidence VALUES ('e', 'missing', 'x', 'test', 'now', NULL, NULL, NULL, 'REAL', 'VERIFIED')")
    with pytest.raises(sqlite3.IntegrityError):
        with k._connect() as db:
            db.execute("INSERT INTO process_runs (run_id, process_id, trigger_type, requested_at) VALUES ('r', 'missing', 'TEST', 'now')")


def test_read_model_is_read_only_and_structured(tmp_path):
    k = TruthKernel(tmp_path / "truth.db"); k.register_process(definition())
    status = k.get_process_status("p")
    assert status["PROCESS_ID"] == "p"; assert status["CURRENT_STATE"] == "READY"
    assert status["FRESH"] is False; assert k.get_run("missing") is None


def test_missing_process_is_safe(tmp_path):
    k = TruthKernel(tmp_path / "truth.db")
    assert k.derive_process_state("missing") == "NOT_CONFIGURED"
