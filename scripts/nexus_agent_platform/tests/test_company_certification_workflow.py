import json
import shutil
import uuid
from pathlib import Path

from nexus_agent_platform.company_certification_workflow import handle_job
from nexus_agent_platform.durable_jobs import DurableJobStore
from nexus_agent_platform.marketing_creative_workflow import _attach_handoff_receipt


def test_official_source_synthesis_creates_atlas_handoff_and_child(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[3]
    summary = root / "reports/runtime/research_artifacts/web/cert-sba-1.summary.json"
    provenance = root / "reports/runtime/research_artifacts/web/cert-sba-1.provenance.json"
    artifact_dir = root / "data/runtime" / f"test-company-cert-{uuid.uuid4().hex}"
    artifact_dir.mkdir(parents=True)
    payload_path = artifact_dir / "research.json"
    payload_path.write_text(json.dumps({
        "campaign_id": "test-company-cert",
        "source_summary_ref": str(summary),
        "source_provenance_ref": str(provenance),
    }))
    monkeypatch.setattr("nexus_agent_platform.company_certification_workflow.ARTIFACT_DIR", artifact_dir)
    store = DurableJobStore(tmp_path / "jobs.sqlite3")
    job = store.enqueue("RESEARCH", "CERTIFICATION_RESEARCH_SYNTHESIS",
                        payload_ref=str(payload_path), correlation_id="corr-test",
                        governance_context={"campaign_id": "test-company-cert", "providers_allowed": [],
                                            "spend_allowed": False, "resource_class": "LIGHTWEIGHT_INTERNAL"})
    result = handle_job(job, store)
    artifact = json.loads((root / result["artifact_ref"]).read_text())
    handoff = json.loads((root / result["handoff_ref"]).read_text())
    child = store.get(result["next_job_id"])
    assert artifact["confidence"] == "LOW_SOURCE_ONLY"
    assert "not customer demand" in artifact["customer_need"]
    assert handoff["to_department"] == "ATLAS"
    assert handoff["correlation_id"] == job.correlation_id
    assert child and child.department == "ATLAS" and child.correlation_id == job.correlation_id
    assert result["provider_calls"] == 0
    shutil.rmtree(artifact_dir)


def test_retry_receipt_is_not_attached_to_prior_attempt_handoff():
    handoff = {"job_id": "original-job", "receipt_id": "receipt-pending:original-job"}
    assert not _attach_handoff_receipt(handoff, "retry-job", "retry-receipt")
    assert handoff["receipt_id"] == "receipt-pending:original-job"
    assert _attach_handoff_receipt(handoff, "original-job", "original-receipt")
    assert handoff["receipt_id"] == "original-receipt"
