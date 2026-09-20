from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from nexus_agent_platform.demand_discovery import discover_from_questions
from nexus_agent_platform.research_work_queue import ResearchWorkQueue, concurrency_limits, worker_bucket


def test_assigned_work_drains_before_monitor_and_discovery(tmp_path):
    queue = ResearchWorkQueue(tmp_path / "queue.json")
    queue.enqueue(work_id="assigned-1", work_class="ASSIGNED", priority=1, source_type="WEB_PAGE", source_id="a")
    queue.enqueue(work_id="assigned-2", work_class="ASSIGNED", priority=2, source_type="WEB_PAGE", source_id="b")
    queue.enqueue(work_id="monitored-1", work_class="MONITORED", priority=1, source_type="WEB_PAGE", source_id="m")
    queue.enqueue(work_id="discovery-1", work_class="DEMAND_DISCOVERY", priority=1, source_type="WEB_PAGE", source_id="d")

    first = queue.claim_next(worker_id="test")
    assert first["work_id"] == "assigned-1"
    queue.settle(first["work_id"], "COMPLETE", result={"ok": True})
    second = queue.claim_next(worker_id="test")
    assert second["work_id"] == "assigned-2"
    queue.settle(second["work_id"], "COMPLETE", result={"ok": True})
    third = queue.claim_next(worker_id="test")
    assert third["work_id"] == "monitored-1"


def test_expired_lease_is_recoverable(tmp_path):
    now = datetime(2026, 9, 18, tzinfo=timezone.utc)
    queue = ResearchWorkQueue(tmp_path / "queue.json", now_fn=lambda: now)
    queue.enqueue(work_id="lease", work_class="ASSIGNED", source_id="x")
    claimed = queue.claim_next(worker_id="dead-worker", lease_seconds=30)
    store = queue.load()
    store["items"][0]["lease_expires_at"] = (now - timedelta(seconds=1)).isoformat()
    queue.path.write_text(json.dumps(store), encoding="utf-8")
    recovered = queue.claim_next(worker_id="recovery")
    assert recovered["work_id"] == claimed["work_id"]
    assert recovered["claimed_by"] == "recovery"


def test_need_projection_deduplicates_by_audience_and_problem(tmp_path, monkeypatch):
    import nexus_agent_platform.research_work_queue as module

    needs = tmp_path / "needs.jsonl"
    monkeypatch.setattr(module, "NEEDS_PATH", needs)
    queue = ResearchWorkQueue(tmp_path / "queue.json")
    first = queue.create_need(audience="new LLC owners", problem="funding documentation", question="What documents are required?", desired_outcome="prepare a lender-ready packet", source_refs=["https://www.sba.gov/"], where_customers_congregate=["search demand"], demand_signals=["repeated funding-document question"], evidence_gaps=["query-volume evidence"])
    second = queue.create_need(audience="new LLC owners", problem="funding documentation", question="What documents are required?", desired_outcome="prepare a lender-ready packet", source_refs=["https://www.sba.gov/"], where_customers_congregate=["search demand"], demand_signals=["repeated funding-document question"], evidence_gaps=["query-volume evidence"])
    assert first["need_id"] == second["need_id"]
    assert len(needs.read_text().splitlines()) == 1


def test_worker_caps_are_bounded_and_classified():
    assert concurrency_limits() == {"total": 3, "youtube": 1, "web": 1, "discovery": 1}
    assert worker_bucket({"source_type": "YOUTUBE_VIDEO", "work_class": "ASSIGNED"}) == "youtube"
    assert worker_bucket({"source_type": "DEMAND_QUERY", "work_class": "DEMAND_DISCOVERY"}) == "discovery"
    assert worker_bucket({"source_type": "WEB_PAGE", "work_class": "ASSIGNED"}) == "web"


def test_claim_skips_full_worker_bucket(tmp_path):
    queue = ResearchWorkQueue(tmp_path / "queue.json")
    queue.enqueue(work_id="youtube", work_class="ASSIGNED", source_type="YOUTUBE_VIDEO", priority=1)
    queue.enqueue(work_id="web", work_class="ASSIGNED", source_type="WEB_PAGE", priority=2)
    claimed = queue.claim_next(worker_id="worker", blocked_buckets={"youtube"})
    assert claimed["work_id"] == "web"


def test_priority_quantum_allows_lower_classes_to_progress(tmp_path):
    queue = ResearchWorkQueue(tmp_path / "queue.json")
    for index in range(6):
        queue.enqueue(work_id=f"assigned-{index}", work_class="ASSIGNED", priority=1, source_type="WEB_PAGE")
    queue.enqueue(work_id="monitored", work_class="MONITORED", priority=50, source_type="WEB_PAGE")
    queue.enqueue(work_id="demand", work_class="DEMAND_DISCOVERY", priority=50, source_type="DEMAND_QUERY")
    queue.enqueue(work_id="general", work_class="GENERAL_DISCOVERY", priority=50, source_type="WEB_PAGE")

    selected = []
    for index in range(20):
        item = queue.claim_next(worker_id=f"fair-{index}")
        selected.append(item["work_class"])
        queue.release(item["work_id"], reason="fairness_test")

    assert selected[:5] == ["ASSIGNED"] * 5
    assert {"MONITORED", "DEMAND_DISCOVERY", "GENERAL_DISCOVERY"}.issubset(selected)


def test_superseded_is_terminal_and_not_reclaimable(tmp_path):
    queue = ResearchWorkQueue(tmp_path / "queue.json")
    queue.enqueue(work_id="superseded", work_class="ASSIGNED")
    queue.settle("superseded", "SUPERSEDED", result={"reason": "duplicate"})
    assert queue.claim_next(worker_id="test") is None
    assert queue.summary()["by_status"]["SUPERSEDED"] == 1


def test_one_time_completion_is_not_requeued(tmp_path):
    queue = ResearchWorkQueue(tmp_path / "queue.json")
    queue.enqueue(work_id="one-time", work_class="ASSIGNED", source_type="YOUTUBE_VIDEO",
                  source_id="video-1", lifecycle="ONE_TIME")
    item = queue.claim_next(worker_id="worker")
    queue.settle(item["work_id"], "COMPLETE", result={"processed": True})
    assert queue.claim_next(worker_id="worker") is None
    assert queue.summary()["by_status"]["COMPLETE"] == 1


def test_demand_discovery_requires_aggregated_evidence(tmp_path, monkeypatch):
    import nexus_agent_platform.research_work_queue as module
    monkeypatch.setattr(module, "NEEDS_PATH", tmp_path / "needs.jsonl")
    queue = ResearchWorkQueue(tmp_path / "queue.json")
    rows = [
        {"question": "What credit score is needed for a new LLC?", "source_id": "search-1"},
        {"question": "What credit score is needed for a new LLC?", "source_id": "reddit-1"},
    ]
    needs = discover_from_questions(rows, queue=queue)
    assert len(needs) == 1
    assert needs[0]["alpha_review_required"] is True
