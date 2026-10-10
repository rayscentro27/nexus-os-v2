import pytest

from scripts.nexus_agent_platform.providers.modal_provider import ModalRemoteWorkerProvider, provider_from_environment
from scripts.nexus_agent_platform.remote_worker import build_remote_job, sign_request


class _Function:
    def __init__(self, value):
        self.value = value
        self.calls = []

    def remote(self, *args):
        self.calls.append(args)
        return self.value


def _job(tenant=None):
    return build_remote_job(
        capability="evidence_ingestion",
        adapter="crawl4ai",
        source={"source_type": "public_url", "original_reference": "https://example.com/"},
        tenant_context=tenant or {"scope": "founder_admin", "tenant_id": None},
    )


def _result(job):
    return {
        "schema_version": "nexus.remote-result.v1",
        "job_id": job["job_id"], "capability": job["capability"],
        "worker_id": "modal-test-worker", "provider": "modal", "status": "SUCCESS",
        "started_at": "2026-01-01T00:00:00+00:00", "completed_at": "2026-01-01T00:00:01+00:00",
        "tenant_context": job["tenant_context"],
    }


def _allow_mock_modal(monkeypatch, tmp_path):
    from nexus_agent_platform.resource_spend_governor import LocalGovernorStore
    path=tmp_path/"governor.sqlite3"
    monkeypatch.setenv("NEXUS_GOVERNOR_DB",str(path))
    monkeypatch.setenv("NEXUS_MODAL_ESTIMATED_COST_PER_JOB","0.01")
    monkeypatch.setenv("NEXUS_JOB_BUDGET",'{"max_estimated_cost":1,"max_runtime_seconds":1000}')
    LocalGovernorStore(path).set_policy("MODAL","remote_worker","evidence_ingestion","DAILY",
        autonomous_usage_allowed=True,autonomous_spend_allowed=True,
        hard_limits={"rate":{},"usage":{"requests":10,"operations":10,"runtime_seconds":1000},
                     "money":{"per_job":1,"per_day":10,"per_month":100}})


def test_modal_submit_uses_native_function_and_preserves_contract(monkeypatch, tmp_path):
    _allow_mock_modal(monkeypatch,tmp_path)
    secret = "test-secret"
    job = _job()
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID", job["job_id"])
    function = _Function(_result(job))
    provider = ModalRemoteWorkerProvider(shared_secret=secret)
    monkeypatch.setattr(provider, "_function", lambda name: function)

    result = provider.submit(job)

    assert result["provider"] == "modal"
    assert function.calls
    assert function.calls[0][0] == job
    assert function.calls[0][2] == sign_request(job, secret, function.calls[0][1])


def test_modal_submit_rejects_wrong_job_or_tenant(monkeypatch, tmp_path):
    _allow_mock_modal(monkeypatch,tmp_path)
    job = _job()
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID", job["job_id"])
    wrong_job = _job({"scope": "tenant", "tenant_id": "other"})
    function = _Function(_result(wrong_job))
    provider = ModalRemoteWorkerProvider(shared_secret="test-secret")
    monkeypatch.setattr(provider, "_function", lambda name: function)

    with pytest.raises(ValueError, match="job mismatch"):
        provider.submit(job)


def test_modal_cancel_is_explicitly_bounded():
    result = ModalRemoteWorkerProvider().cancel("job-1")
    assert result["status"] == "NOT_AVAILABLE"


def test_native_factory_does_not_require_endpoint_url(monkeypatch):
    monkeypatch.delenv("NEXUS_MODAL_WORKER_URL", raising=False)
    monkeypatch.setenv("MODAL_PROFILE", "goclearonline")
    monkeypatch.setenv("NEXUS_MODAL_APP", "nexus-remote-cpu-worker")
    monkeypatch.setenv("NEXUS_REMOTE_WORKER_SHARED_SECRET", "test-secret")
    provider = provider_from_environment()
    assert provider.endpoint_url == ""
    assert provider.profile == "goclearonline"
    assert provider.app_name == "nexus-remote-cpu-worker"
    assert provider.shared_secret == "test-secret"


def test_endpoint_remains_optional_curl_compatibility(monkeypatch):
    monkeypatch.setenv("NEXUS_MODAL_WORKER_URL", "https://example.modal.run")
    provider = provider_from_environment()
    assert provider.endpoint_url == "https://example.modal.run"


def test_missing_secret_fails_only_when_signed_job_is_submitted(monkeypatch):
    monkeypatch.delenv("NEXUS_REMOTE_WORKER_SHARED_SECRET", raising=False)
    monkeypatch.delenv("NEXUS_MODAL_WORKER_URL", raising=False)
    provider = provider_from_environment()
    with pytest.raises(RuntimeError, match="SHARED_SECRET"):
        provider.submit(_job())


def test_modal_submit_requires_matching_durable_job_identity(monkeypatch):
    provider = ModalRemoteWorkerProvider(shared_secret="test-secret")
    monkeypatch.delenv("NEXUS_DURABLE_JOB_ID", raising=False)
    from scripts.nexus_agent_platform.resource_spend_governor import GovernanceDenied
    with pytest.raises(GovernanceDenied, match="DURABLE_JOB_ID_REQUIRED_OR_MISMATCH"):
        provider.submit(_job())


def test_curl_transport_requires_endpoint(monkeypatch):
    monkeypatch.delenv("NEXUS_MODAL_WORKER_URL", raising=False)
    provider = provider_from_environment()
    with pytest.raises(RuntimeError, match="WORKER_URL"):
        provider._curl("GET", "/health")
