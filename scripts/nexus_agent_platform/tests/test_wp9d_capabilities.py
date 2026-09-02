from nexus_agent_platform.wp9d_capabilities import (
    Blocker, attempt_recovery, detect_blocker, foundry_capture,
    placement, prepare_auth_checkpoint, run_synthetic_self_resolution,
)


def test_blocker_lifecycle_resolves_with_verification():
    row = run_synthetic_self_resolution()
    assert row["current_status"] == "RESOLVED"
    assert row["verification_evidence"]


def test_auth_checkpoint_has_smallest_human_gate():
    row = prepare_auth_checkpoint("Example", "read-only", ["read"], "https://example.com/oauth", "test")
    assert row["status"] == "WAITING_HUMAN_CONSENT"
    assert row["resume_step"]
    assert row["cost_review"] == "$0 new spend"


def test_placement_moves_gpu_work_off_mac():
    assert placement("gpu", gpu="REQUIRED", ram="HIGH")["run_location"] == "REMOTE_GPU_OPTIONAL"
    assert placement("small", gpu="NONE", ram="LOW")["run_location"] == "MAC_CONTROL_PLANE"


def test_foundry_is_bounded_and_authority_explicit():
    row = foundry_capture("blocker", "repair", "INTERNAL_ONLY")
    assert row["next_stage"] == "CLASSIFY"
    assert "bounded" in row["stopping_rule"]
