from pathlib import Path

import pytest

from nexus_agent_platform.alpha_evidence_bridge import request_research_evidence
from nexus_agent_platform.remote_worker import build_remote_job


class FakeProvider:
    def __init__(self, status="SUCCESS"):
        self.status = status
        self.jobs = []

    def submit(self, job):
        self.jobs.append(job)
        if self.status != "SUCCESS":
            return {"status": self.status}
        return {
            "schema_version": "nexus.remote-result.v1", "job_id": job["job_id"],
            "capability": "evidence_ingestion", "worker_id": "worker-test", "provider": "modal",
            "status": "SUCCESS", "started_at": "2026-01-01T00:00:00+00:00", "completed_at": "2026-01-01T00:00:01+00:00",
            "tenant_context": job["tenant_context"], "evidence_result": {
                "schema_version": "nexus.evidence.v1", "evidence_id": "ev-alpha-bridge", "job_id": job["job_id"],
                "status": "SUCCESS", "receipt_id": "ev-receipt", "source": {"source_type": "public_url", "adapter": "crawl4ai", "original_reference": "https://example.com/", "retrieved_at": "2026-01-01T00:00:01+00:00"},
                "integrity": {"source_hash": "source", "material_hash": "material", "duplicate_status": "NEW"},
                "content": {"title": "Example", "normalized_text_or_markdown": "Public evidence"},
                "safety": {"redaction_status": "NO_REDACTION_NEEDED"}, "execution": {"tenant_context": job["tenant_context"]},
            },
        }


def test_bridge_submits_fixed_capability_and_accepts_canonical_evidence(tmp_path: Path):
    provider = FakeProvider()
    result = request_research_evidence(url="https://example.com/", job_id="alpha-bridge-1", tenant_context={"scope": "founder_admin", "tenant_id": None}, provider=provider, root=tmp_path / "runtime", receipt_dir=tmp_path / "receipts", handoff=tmp_path / "handoff.jsonl")
    assert result["status"] == "SUCCESS"
    assert provider.jobs[0]["capability"] == "evidence_ingestion"
    assert provider.jobs[0]["adapter"] == "crawl4ai"
    assert result["evidence"]["evidence_id"] == "ev-alpha-bridge"
    assert (tmp_path / "runtime" / "artifacts" / "ev-alpha-bridge.json").exists()


def test_bridge_has_no_arbitrary_capability_or_url_authority(tmp_path: Path):
    with pytest.raises(ValueError, match="public-http-url-required"):
        request_research_evidence(url="file:///etc/passwd", job_id="alpha-bridge-2", tenant_context={"scope": "founder_admin", "tenant_id": None}, provider=FakeProvider(), root=tmp_path)
    with pytest.raises(ValueError, match="bounded-tenant-context-required"):
        request_research_evidence(url="https://example.com/", job_id="alpha-bridge-3", tenant_context={"scope": "founder_admin", "secret": "bad"}, provider=FakeProvider(), root=tmp_path)


def test_bridge_returns_dependency_status_without_fabrication(tmp_path: Path):
    result = request_research_evidence(url="https://example.com/", job_id="alpha-bridge-4", tenant_context={"scope": "founder_admin", "tenant_id": None}, provider=FakeProvider("DEPENDENCY_UNAVAILABLE"), root=tmp_path)
    assert result["status"] == "DEPENDENCY_UNAVAILABLE"
    assert "evidence" not in result
