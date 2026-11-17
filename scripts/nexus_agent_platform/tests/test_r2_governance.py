from __future__ import annotations

import pytest

from nexus_agent_platform.creative import r2_governance
from nexus_agent_platform.resource_spend_governor import GovernanceDenied, LocalGovernorStore


def test_r2_cost_estimate_is_bounded_advisory_and_does_not_subtract_unknown_free_tier():
    estimate = r2_governance.operation_estimate("OBJECT_PUT", byte_count=1024)
    assert estimate["cost_estimate_mode"] == "BOUNDED_ADVISORY"
    assert estimate["cost"] > 0
    assert estimate["class_a_count"] == 1
    assert estimate["upload_bytes"] == 1024


def test_r2_small_head_signed_read_and_bounded_get_are_estimable():
    assert r2_governance.operation_estimate("OBJECT_GET_METADATA")["class_b_count"] == 1
    assert r2_governance.operation_estimate("SIGNED_READ_URL")["cost"] == 0
    assert r2_governance.operation_estimate("OBJECT_GET_VERIFICATION", byte_count=100)["download_bytes"] == 100


def test_r2_oversized_put_and_unapproved_operations_fail_closed():
    with pytest.raises(r2_governance.R2PolicyError, match="SINGLE_OBJECT_LIMIT"):
        r2_governance.operation_estimate("OBJECT_PUT", byte_count=50 * 1024 * 1024 + 1)
    with pytest.raises(r2_governance.R2PolicyError, match="OPERATION_NOT_ALLOWED"):
        r2_governance.operation_estimate("BUCKET_DELETE")


def test_unknown_rates_fail_closed(monkeypatch):
    monkeypatch.setattr(r2_governance, "COST_POLICY_PATH", r2_governance.ROOT / "missing-r2-cost-policy.json")
    with pytest.raises(r2_governance.R2PolicyError, match="CONFIGURATION_UNAVAILABLE"):
        r2_governance.operation_estimate("OBJECT_HEAD")


def test_r2_policy_definitions_bound_certification_and_disable_unapproved_production():
    cert, prod = r2_governance.policy_definitions()
    assert cert["state"] == "NORMAL"
    assert cert["hard_limits"]["money"]["per_job"] == 0.10
    assert cert["hard_limits"]["usage"]["object_count"] == 10
    assert cert["hard_limits"]["usage"]["upload_bytes"] == 100 * 1024 * 1024
    assert prod["state"] == "HUMAN_APPROVAL_REQUIRED"
    assert prod["autonomous_usage_allowed"] is False
    assert prod["hard_limits"]["usage"]["delete_operations"] == 0
    assert prod["hard_limits"]["money"]["per_job"] == 0


def test_missing_r2_policy_denies_without_calling_provider(tmp_path):
    store = LocalGovernorStore(str(tmp_path / "governor.sqlite3"))
    with pytest.raises(GovernanceDenied, match="UNKNOWN_PAID_PROVIDER"):
        store.reserve("CLOUDFLARE_R2", "creative_canonical_storage", "NEXUS_R2_LIVE_CERTIFICATION",
                      "missing-policy-job", r2_governance.governor_estimate("OBJECT_GET_METADATA"))


def test_certification_policy_enforces_cost_and_byte_ceiling(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_JOB_BUDGET", '{"max_estimated_cost":0.1,"max_response_bytes":157286400,"max_requests":150}')
    store = LocalGovernorStore(str(tmp_path / "governor.sqlite3"))
    cert, _ = r2_governance.policy_definitions()
    store.ensure_policy(cert["provider"], cert["service"], cert["job_type"], cert["budget_period"],
        autonomous_usage_allowed=True, autonomous_spend_allowed=True,
        soft_limits=cert["soft_limits"], hard_limits=cert["hard_limits"],
        state="NORMAL", approval_required=False, concurrency_limit=1)
    limits = r2_governance.governor_estimate("OBJECT_PUT", byte_count=1024)
    limits["job_budget"] = {"max_estimated_cost": 0.1, "max_response_bytes": 157286400, "max_requests": 150}
    store.reserve("CLOUDFLARE_R2", "creative_canonical_storage", cert["job_type"], "cert-1",
        limits, purpose="put-1")
    too_large = {**limits, "upload_bytes": 101 * 1024 * 1024, "bytes": 101 * 1024 * 1024}
    with pytest.raises(GovernanceDenied):
        store.reserve("CLOUDFLARE_R2", "creative_canonical_storage", cert["job_type"], "cert-2",
            too_large, purpose="put-2")
    too_costly = {**limits, "cost": 0.11}
    with pytest.raises(GovernanceDenied):
        store.reserve("CLOUDFLARE_R2", "creative_canonical_storage", cert["job_type"], "cert-3",
            too_costly, purpose="put-3")


def test_certification_process_guard_denies_operation_count_overflow():
    cert = r2_governance.policy_definitions()[0]
    limits = cert["hard_limits"]["usage"]
    detail = r2_governance.operation_estimate("OBJECT_GET_METADATA")
    for _ in range(limits["class_b_count"]):
        r2_governance.reserve_process_run_usage("cert-overflow-test", "OBJECT_GET_METADATA", detail,
                                               r2_governance._read(r2_governance.GOVERNOR_POLICY_PATH)["certification_limits"])
    with pytest.raises(r2_governance.R2PolicyError, match="RUN_OPERATION_LIMIT"):
        r2_governance.reserve_process_run_usage("cert-overflow-test", "OBJECT_GET_METADATA", detail,
                                               r2_governance._read(r2_governance.GOVERNOR_POLICY_PATH)["certification_limits"])


def test_asset_persistence_adapter_uses_governed_boundary(monkeypatch):
    from nexus_agent_platform.creative.r2_storage import CloudflareR2StorageAdapter

    captured = {}
    def governed(provider, service, action, estimate, operation, **kwargs):
        captured.update(provider=provider, service=service, action=action, estimate=estimate)
        return operation()
    monkeypatch.setattr("nexus_agent_platform.provider_enforcement.execute", governed)
    monkeypatch.setattr("nexus_agent_platform.governed.persistence.append_record", lambda *args, **kwargs: None)
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID", "unit-r2-governed-adapter")
    adapter = object.__new__(CloudflareR2StorageAdapter)
    adapter.bucket = "test-private"
    adapter._governed("OBJECT_GET_METADATA", {}, lambda: {"ok": True}, object_key="a/b")
    assert captured["provider"] == "CLOUDFLARE_R2"
    assert captured["service"] == "creative_canonical_storage"
    assert captured["estimate"]["cost"] > 0


def test_certification_delete_requires_certification_job_and_existing_approval(monkeypatch):
    from nexus_agent_platform.creative.r2_storage import CloudflareR2StorageAdapter

    monkeypatch.setenv("NEXUS_JOB_TYPE", "CREATIVE_ASSET_PERSISTENCE")
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID", "unit-r2-delete-denied")
    adapter = object.__new__(CloudflareR2StorageAdapter)
    adapter.bucket = "private"
    adapter.approval_verifier = lambda *_: True
    adapter.client = type("Client", (), {"delete_object": lambda *_args, **_kwargs: pytest.fail("must not call")})()
    with pytest.raises(PermissionError, match="CERTIFICATION_DELETE_ONLY"):
        adapter.delete("cert/test", approval_id="approved")
