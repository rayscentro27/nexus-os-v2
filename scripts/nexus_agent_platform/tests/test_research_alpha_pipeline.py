import json

from nexus_agent_platform import research_alpha_pipeline as pipeline
from nexus_agent_platform.governed import persistence


def _append(path, rows):
    path.write_text("\n".join(json.dumps(row) for row in rows) + ("\n" if rows else ""), encoding="utf-8")


def test_persisted_output_is_evaluated_once_and_reloaded(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path / "governed"))
    persistence.append_record("alpha_content", {"content_id": "content-1", "research_item_id": "content-1", "title": "Real persisted source"})
    persistence.append_record("alpha_claims", {"claim_id": "claim-1", "content_id": "content-1", "claim": "Observed claim", "evidence_score": 0.82, "verification_status": "SUPPORTED"})
    persistence.append_record("alpha_research", {"research_id": "research-1", "claims": ["claim-1"], "theme": "AI_NEXUS"})
    first = pipeline.evaluate_pending()
    second = pipeline.evaluate_pending()
    assert first["evaluated_count"] == 1
    assert second["evaluated_count"] == 0
    rows = persistence.read_records("alpha_evaluations")
    assert rows[0]["research_item_id"] == "content-1"
    assert rows[0]["score"] == 82
    assert rows[0]["decision"] == "QUALIFIED"
    assert len(rows) == 1


def test_weak_candidate_is_persisted_but_not_routed(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path / "governed"))
    persistence.append_record("alpha_content", {"content_id": "content-2", "research_item_id": "content-2", "title": "Weak source"})
    persistence.append_record("alpha_claims", {"claim_id": "claim-2", "content_id": "content-2", "claim": "Unverified observation", "evidence_score": 0.0, "verification_status": "UNVERIFIED"})
    persistence.append_record("alpha_research", {"research_id": "research-2", "claims": ["claim-2"], "theme": "BUSINESS"})
    result = pipeline.evaluate_pending()
    evaluation = result["evaluations_created"][0]
    assert evaluation["decision"] == "REJECTED"
    assert evaluation["next_route"] is None
    assert not persistence.read_records("work_orders")


def test_collection_survives_reload(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path / "governed"))
    persistence.append_record("alpha_evaluations", {"evaluation_id": "eval-reload", "research_item_id": "item-reload", "score": 0, "decision": "REJECTED"})
    assert persistence.read_records("alpha_evaluations")[0]["evaluation_id"] == "eval-reload"
