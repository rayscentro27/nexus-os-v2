import json
from datetime import datetime, timezone

import pytest

from nexus_agent_platform.alpha_research import (
    AlphaResearchError,
    build_research_job,
    build_research_plan,
    run_alpha_research,
    validate_research_job,
)


def evidence(evidence_id="ev-1", *, title="Public source", material="A public finding"):
    return {
        "schema_version": "nexus.evidence.v1", "evidence_id": evidence_id, "status": "SUCCESS",
        "source": {"source_type": "public_url", "original_reference": "https://example.com/source", "final_url": "https://example.com/source", "retrieved_at": datetime.now(timezone.utc).isoformat(), "provenance": {"public_only": True}},
        "integrity": {"source_hash": "source-hash-1", "material_hash": f"material-{evidence_id}"},
        "content": {"title": title, "normalized_text_or_markdown": material},
    }


def test_research_job_is_versioned_bounded_and_planned():
    job = build_research_job(objective="Compare public competitor positioning", research_type="COMPETITOR_RESEARCH", limits={"max_sources": 3, "max_evidence_jobs": 1})
    assert job["schema_version"] == "nexus.alpha-research-job.v1"
    assert job["limits"]["max_sources"] == 3
    plan = build_research_plan(job)
    assert plan["stopping_conditions"]


def test_invalid_job_and_sensitive_context_are_rejected():
    with pytest.raises(AlphaResearchError, match="missing-research-objective"):
        validate_research_job({"schema_version": "nexus.alpha-research-job.v1", "objective": ""})
    with pytest.raises(AlphaResearchError, match="SAFETY_BLOCKED"):
        build_research_job(objective="Read this client credit report and decide", research_type="MARKET_RESEARCH")


def test_structured_pack_requires_evidence_refs_and_labels_advice(tmp_path):
    job = build_research_job(objective="Compare public competitor positioning", research_type="COMPETITOR_RESEARCH")
    result = run_alpha_research(job, [evidence()], claim_specs=[
        {"claim": "The public source describes a bounded offer.", "claim_type": "DIRECT_EVIDENCE", "evidence_refs": ["ev-1"], "confidence": "HIGH"},
        {"claim": "This claim has no source.", "evidence_refs": ["missing"]},
    ], opportunities=[{"opportunity_title": "Research candidate"}], unknowns=["Public pricing was not available."], runtime_root=tmp_path)
    assert result["pack"]["status"] == "PARTIAL"
    assert result["pack"]["findings"][0]["evidence_refs"] == ["ev-1"]
    assert result["pack"]["claims"][1]["confidence"] == "UNSUPPORTED"
    assert result["pack"]["opportunities"][0]["execution_status"] == "NOT_EXECUTED"
    assert result["receipt"]["status"] == "PARTIAL"


def test_no_evidence_is_honest_and_receipt_is_structured(tmp_path):
    job = build_research_job(objective="Research a public technology option", research_type="TECHNOLOGY_RESEARCH")
    result = run_alpha_research(job, [], runtime_root=tmp_path)
    assert result["pack"]["status"] == "INSUFFICIENT_EVIDENCE"
    assert result["receipt"]["error_classification"] == "INSUFFICIENT_EVIDENCE"
    json.dumps(result["receipt"])


def test_evidence_limit_and_tenant_context_are_preserved(tmp_path):
    job = build_research_job(objective="Compare public technology sources", research_type="OPEN_SOURCE_RESEARCH", limits={"max_sources": 1}, tenant_context={"scope": "founder_admin", "tenant_id": "tenant-a"})
    result = run_alpha_research(job, [evidence("ev-1"), evidence("ev-2")], runtime_root=tmp_path)
    assert len(result["pack"]["sources"]) == 1
    assert result["job"]["tenant_context"]["tenant_id"] == "tenant-a"
