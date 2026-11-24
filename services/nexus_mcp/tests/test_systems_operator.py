from __future__ import annotations

from services.nexus_mcp.systems_operator import _job_summary, _public_state, _strip_internal_ids, _latest_nova_job_id, resolve_action_target


def test_action_target_is_manifest_bound_and_component_specific():
    manifest = {"systems_managed_work": {"action_targets": {
        "UPGRADE_REVIEW": {"component": "opencode", "requested_files": ["~/.config/opencode/opencode.jsonc"]}
    }}}
    assert resolve_action_target(manifest, "UPGRADE_REVIEW", "opencode")["requested_files"]
    assert resolve_action_target(manifest, "UPGRADE_REVIEW", "research") is None
    assert resolve_action_target(manifest, "SHELL", "opencode") is None


def test_user_safe_job_summary_hides_internal_id_by_default():
    row = {"id": "sysjob_0123456789abcdef01234567",
           "order": {"objective": "Review OpenCode", "component": "opencode",
                     "execution_agent": "SYSTEMS_LOCAL", "approval_requirement": "NONE_READ_ONLY",
                     "status": "READY_FOR_AGENT"}, "latest": {"status": "READY_FOR_AGENT"}}
    summary = _job_summary(row)
    assert summary["state"] == "READY"
    assert "systems_job_id" not in summary
    assert _job_summary(row, include_internal_id=True)["systems_job_id"] == row["id"]


def test_managed_state_normalization_is_small_and_meaningful():
    assert _public_state("EXECUTING") == "RUNNING"
    assert _public_state("TARGET_UNRESOLVED") == "FAILED_RECOVERABLE"
    assert _public_state("COMPLETED_WITH_LIMITATIONS") == "COMPLETED_WITH_LIMITATIONS"


def test_internal_identifiers_are_hidden_in_submission_running_completion_and_result_presentations():
    job_id = "sysjob_0123456789abcdef01234567"
    receipt = "sysrcpt_0123456789abcdef01234567"
    cases = {
        "submitted": {"status": "READY", "systems_job_id": job_id, "receipt_id": receipt,
                       "summary": f"Submitted {job_id}; receipt {receipt}"},
        "running": {"state": "RUNNING", "claim_id": "claim-12345678", "worker_id": "worker-12345678",
                    "summary": f"Running {job_id}"},
        "completed": {"state": "COMPLETED", "database_id": "db-12345678", "summary": f"Completed {receipt}"},
        "result": {"status": "COMPLETED", "approval_reference": "sysapproval_" + "a" * 48,
                   "summary": f"Result for {job_id}"},
    }
    for stage, payload in cases.items():
        rendered = repr(_strip_internal_ids(payload))
        for forbidden in (job_id, receipt, "claim-12345678", "worker-12345678", "db-12345678", "sysapproval_"):
            assert forbidden not in rendered, stage


def test_latest_nova_job_lookup_stays_internal(monkeypatch):
    import services.nexus_mcp.systems_operator as operator
    rows = [
        {"id": "sysjob_" + "1" * 24, "order": {"requested_by": "SYSTEMS_TECHNICAL_CERTIFICATION"}},
        {"id": "sysjob_" + "2" * 24, "order": {"requested_by": "NOVA_VIA_NEXUS_MCP"}},
    ]
    monkeypatch.setattr(operator, "_work_rows", lambda: rows)
    assert _latest_nova_job_id() == rows[-1]["id"]
    rows[-1]["order"]["objective"] = "bounded validation run"
    assert _latest_nova_job_id("validation") == rows[-1]["id"]


def test_user_result_view_preserves_validation_evidence_without_internal_ids():
    payload = {"status": "COMPLETED_WITH_LIMITATIONS", "checked_at": "2026-11-04T00:00:00Z",
        "systems_s1_health": {"status": "PASS"}, "research_r10_health": {"status": "PASS"},
        "stored_vs_direct_health_reconciliation": {"status": "UNKNOWN"},
        "findings": [{"name": "systems_s1_health", "status": "PASS"}],
        "next_action": "REVIEW_DEGRADED_CHECKS", "systems_job_id": "sysjob_0123456789abcdef01234567",
        "receipt_id": "sysrcpt_0123456789abcdef01234567"}
    rendered = _strip_internal_ids(payload)
    assert rendered["systems_s1_health"]["status"] == "PASS"
    assert rendered["research_r10_health"]["status"] == "PASS"
    assert rendered["stored_vs_direct_health_reconciliation"]["status"] == "UNKNOWN"
    assert rendered["checked_at"] and rendered["next_action"]
    assert "systems_job_id" not in rendered and "receipt_id" not in rendered
