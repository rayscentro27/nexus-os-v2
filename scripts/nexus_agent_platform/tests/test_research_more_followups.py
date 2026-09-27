from __future__ import annotations

from nexus_agent_platform.research_followups import build_followup, persist_followup
from nexus_agent_platform.research_work_queue import ResearchWorkQueue


def test_research_more_followup_is_owned_and_lineage_is_durable(tmp_path, monkeypatch):
    import nexus_agent_platform.research_followups as module

    queue_path = tmp_path / "queue.json"
    requests_path = tmp_path / "research_requests.jsonl"
    monkeypatch.setattr(module, "default_queue", lambda: ResearchWorkQueue(queue_path))
    monkeypatch.setattr(module.persistence, "append_record", lambda name, row: requests_path.open("a").write(__import__("json").dumps(row) + "\n"))

    followup = build_followup(
        finding_id="finding-real",
        alpha_receipt_id="alpha_receipt-real",
        alpha_request_id="alpha_request-real",
        missing_evidence=["license and compatibility"],
        question="Verify the tool before a Systems test.",
        package={"department": "SYSTEMS", "lane_id": "GITHUB_TECHNOLOGY"},
        work_id="alpha-model-followup:alpha_eval-real",
    )
    persist_followup(followup)
    row = ResearchWorkQueue(queue_path).load()["items"][0]
    assert row["owner"] == "RESEARCH"
    assert row["department"] == "SYSTEMS"
    assert row["parent_alpha_receipt_id"] == "alpha_receipt-real"
    assert row["return_target"] == "ALPHA"
    assert row["fallback_sources"]


def test_followup_projection_is_duplicate_safe(tmp_path):
    queue = ResearchWorkQueue(tmp_path / "queue.json")
    queue.enqueue(work_id="alpha-model-followup:one", work_class="ASSIGNED", status="QUEUED", owner="RESEARCH")
    queue.upsert({"work_id": "alpha-model-followup:one", "work_class": "ASSIGNED", "status": "QUEUED", "owner": "RESEARCH", "alpha_followup_required": True})
    assert len(queue.load()["items"]) == 1


def test_research_more_fallback_preserves_alpha_return_contract():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "research"))
    from run_dispatched_research_job import strategy_changing_fallback

    result = strategy_changing_fallback({
        "work_id": "followup-one", "work_class": "ASSIGNED", "lane_id": "TRADING_MARKETS",
        "source_id": "failed", "source_candidates": [{"source_id": "next", "source_url": "https://example.com"}],
        "alpha_followup_required": True, "alpha_eligible": True, "alpha_review_required": True,
        "parent_finding_id": "finding-one", "parent_alpha_receipt_id": "receipt-one",
        "department_target": "TRADING", "owner": "RESEARCH", "research_mode": "NEXUS_DEPARTMENTAL_PROACTIVE",
    }, failure_class="HTTP_ERROR", error="source unavailable")
    assert result["objective_continues"] is True
    assert result["strategy_changed"] is True
