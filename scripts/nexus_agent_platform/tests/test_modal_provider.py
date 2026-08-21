import pytest

from scripts.nexus_agent_platform.providers.modal_provider import ModalRemoteWorkerProvider
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


def test_modal_submit_uses_native_function_and_preserves_contract(monkeypatch):
    secret = "test-secret"
    job = _job()
    function = _Function(_result(job))
    provider = ModalRemoteWorkerProvider(shared_secret=secret)
    monkeypatch.setattr(provider, "_function", lambda name: function)

    result = provider.submit(job)

    assert result["provider"] == "modal"
    assert function.calls
    assert function.calls[0][0] == job
    assert function.calls[0][2] == sign_request(job, secret, function.calls[0][1])


def test_modal_submit_rejects_wrong_job_or_tenant(monkeypatch):
    job = _job()
    wrong_job = _job({"scope": "tenant", "tenant_id": "other"})
    function = _Function(_result(wrong_job))
    provider = ModalRemoteWorkerProvider(shared_secret="test-secret")
    monkeypatch.setattr(provider, "_function", lambda name: function)

    with pytest.raises(ValueError, match="job mismatch"):
        provider.submit(job)


def test_modal_cancel_is_explicitly_bounded():
    result = ModalRemoteWorkerProvider().cancel("job-1")
    assert result["status"] == "NOT_AVAILABLE"
