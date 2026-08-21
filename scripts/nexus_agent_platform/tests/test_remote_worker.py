import json
import http.server
import threading
import time

from scripts.nexus_agent_platform import remote_worker
from scripts.nexus_agent_platform.remote_worker import (
    CapabilityRegistry, InProcessRemoteWorkerProvider, WorkerRuntime,
    build_remote_job, sign_request, validate_job, validate_result, validate_result_tenant, verify_request,
)


def test_remote_job_contract_and_allowlist_are_provider_neutral():
    job = build_remote_job(
        capability="evidence_ingestion", adapter="crawl4ai",
        source={"source_type": "public_url", "original_reference": "https://example.com"},
        tenant_context={"tenant_id": "tenant-a", "scope": "test"},
    )
    assert validate_job(job) == (True, "ok")
    assert json.loads(json.dumps(job))["tenant_context"]["tenant_id"] == "tenant-a"
    assert CapabilityRegistry.allows("evidence_ingestion", "crawl4ai")
    assert not CapabilityRegistry.allows("generic_shell", "shell")
    assert validate_job({**job, "schema_version": "nexus.remote-job.v0"})[0] is False
    assert validate_job({**job, "adapter": "unknown"})[0] is False


def test_authentication_has_timestamp_and_integrity_checks():
    job = build_remote_job(capability="evidence_ingestion", adapter="crawl4ai", source={"source_type": "public_url", "original_reference": "https://example.com"})
    secret = "test-only-worker-secret"
    timestamp = str(int(time.time()))
    signature = sign_request(job, secret, timestamp)
    assert verify_request(job, secret, timestamp, signature)
    assert not verify_request(job, "wrong", timestamp, signature)
    assert not verify_request(job, secret, str(int(time.time()) - 1000), signature)


def test_worker_executes_only_allowlisted_evidence_and_preserves_tenant(tmp_path, monkeypatch):
    def fake_ingest(url, **kwargs):
        return {"status": "SUCCESS", "receipt_ref": "receipt-1", "artifact_ref": "artifact-1",
                "integrity": {"source_hash": "source", "material_hash": "material"},
                "execution": {"completed_at": "2026-08-21T00:00:00+00:00"}, "source": {"original_reference": url},
                "tenant_context": kwargs["tenant_context"]}
    monkeypatch.setattr(remote_worker, "ingest_url", fake_ingest)
    runtime = WorkerRuntime(worker_id="worker-test", provider="test-provider", root=tmp_path, heartbeat_path=tmp_path / "heartbeat.json")
    provider = InProcessRemoteWorkerProvider(runtime)
    job = build_remote_job(capability="evidence_ingestion", adapter="crawl4ai", source={"source_type": "public_url", "original_reference": "https://example.com"}, tenant_context={"tenant_id": "tenant-a", "scope": "test"})
    result = provider.submit(job)
    assert result["status"] == "SUCCESS"
    assert result["tenant_context"]["tenant_id"] == "tenant-a"
    assert validate_result(result) == (True, "ok")
    assert validate_result_tenant(job, result) == (True, "ok")
    assert validate_result_tenant(job, {**result, "tenant_context": {"tenant_id": "other"}})[0] is False
    assert provider.submit(job)["status"] == "DUPLICATE"
    denied = provider.submit(build_remote_job(capability="generic_shell", adapter="shell", source={"source_type": "command", "original_reference": "id"}))
    assert denied["status"] == "SAFETY_BLOCKED"
    assert result["artifact_refs"] == ["artifact-1"]
    assert json.loads((tmp_path / "heartbeat.json").read_text())["arbitrary_shell"] == "UNAVAILABLE"


def test_remote_markitdown_does_not_gain_filesystem_authority(tmp_path):
    runtime = WorkerRuntime(worker_id="worker-test", provider="test-provider", root=tmp_path, heartbeat_path=tmp_path / "heartbeat.json")
    job = build_remote_job(capability="evidence_ingestion", adapter="markitdown", source={"source_type": "local_file", "original_reference": "/tmp/file.txt"})
    result = runtime.execute(job)
    assert result["status"] == "SAFETY_BLOCKED"


def test_worker_health_is_optional_and_cost_is_not_fabricated(tmp_path):
    runtime = WorkerRuntime(worker_id="worker-test", provider="test-provider", root=tmp_path, heartbeat_path=tmp_path / "heartbeat.json")
    health = runtime.health()
    assert health["status"] == "HEALTHY"
    assert health["core_health_dependency"] is False
    assert health["stripe"] == "UNAVAILABLE"


def test_http_provider_requires_authentication_and_returns_structured_result(tmp_path, monkeypatch):
    def fake_ingest(url, **kwargs):
        return {"status": "SUCCESS", "receipt_ref": "receipt-http", "artifact_ref": "artifact-http",
                "integrity": {"source_hash": "s", "material_hash": "m"}, "execution": {"completed_at": "now"},
                "source": {"original_reference": url}}
    monkeypatch.setattr(remote_worker, "ingest_url", fake_ingest)
    secret = "http-test-secret"
    runtime = WorkerRuntime(worker_id="worker-http", provider="linux-container", root=tmp_path,
                             shared_secret=secret, heartbeat_path=tmp_path / "heartbeat.json")
    handler = type("TestHandler", (remote_worker._WorkerHandler,), {"runtime": runtime})
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        provider = remote_worker.HttpRemoteWorkerProvider(f"http://127.0.0.1:{server.server_port}", secret)
        job = build_remote_job(capability="evidence_ingestion", adapter="crawl4ai", source={"source_type": "public_url", "original_reference": "https://example.com"})
        result = provider.submit(job)
        assert result["status"] == "SUCCESS"
        assert provider.health()["worker_id"] == "worker-http"
        unauthenticated = remote_worker.HttpRemoteWorkerProvider(f"http://127.0.0.1:{server.server_port}", "wrong")
        try:
            unauthenticated.submit(build_remote_job(capability="evidence_ingestion", adapter="crawl4ai", source={"source_type": "public_url", "original_reference": "https://example.com"}))
        except Exception as exc:
            assert "401" in str(exc)
        else:
            raise AssertionError("unauthenticated request was accepted")
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)
