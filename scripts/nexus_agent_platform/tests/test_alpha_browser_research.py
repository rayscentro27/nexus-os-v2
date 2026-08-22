from pathlib import Path

from nexus_agent_platform.alpha_research import run_alpha_browser_research
from nexus_agent_platform.tests.test_alpha_evidence_bridge import FakeProvider


def test_browser_research_consumes_accepted_evidence_and_persists_pack_receipt(tmp_path: Path):
    result = run_alpha_browser_research(
        objective="Evaluate a public technology capability from primary evidence",
        research_type="TECHNOLOGY_RESEARCH", url="https://example.com/", provider=FakeProvider(), runtime_root=tmp_path / "alpha",
    )
    assert result["pack"]["status"] == "COMPLETE"
    assert result["pack"]["claims"][0]["evidence_refs"] == ["ev-alpha-bridge"]
    assert result["receipt"]["evidence_count"] == 1
    assert result["heartbeat"]["browser_evidence_used"] is True
    assert result["bridge"]["artifact_ref"]


def test_browser_research_does_not_fabricate_on_worker_failure(tmp_path: Path):
    result = run_alpha_browser_research(
        objective="Evaluate a public technology capability from primary evidence",
        research_type="TECHNOLOGY_RESEARCH", url="https://example.com/", provider=FakeProvider("DEPENDENCY_UNAVAILABLE"), runtime_root=tmp_path / "alpha",
    )
    assert result["status"] == "DEPENDENCY_UNAVAILABLE"
    assert "pack" not in result
