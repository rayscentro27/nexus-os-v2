"""Offline regression tests for the bounded market-heartbeat startup path."""
from __future__ import annotations

import traceback

from nexus_agent_platform import content_intelligence as content
from nexus_agent_platform.continuous_operating_kernel import idle_research_wake_requires_wait, market_wake_due
from research import run_market_intelligence_heartbeat as heartbeat


def _mock_source_reads(monkeypatch):
    calls = []
    inserts = 0

    def get(table, query):
        nonlocal calls
        if table == "research_sources":
            calls.append({"table": table, "query": query, "stack": traceback.extract_stack(limit=8)[-3].name})
            if "&id=eq." in query:
                return 200, [{"id": "fixture"}]
        return 200, []

    def insert(table, row, **kwargs):
        nonlocal inserts
        inserts += 1
        return 201, [{"id": f"fixture-{inserts}"}]

    monkeypatch.setattr(content.sb, "get", get)
    monkeypatch.setattr(content.sb, "insert", insert)
    monkeypatch.setattr(content.sb, "update", lambda *args, **kwargs: (204, []))
    monkeypatch.setattr(content, "_public_json", lambda _url: ["fixture", ["signal-a", "signal-b", "signal-c"]])
    return calls


def _count_signal_reads(monkeypatch, requested_topics):
    calls = _mock_source_reads(monkeypatch)
    selected = heartbeat.bounded_topics(requested_topics)
    heartbeat.sources("YOUTUBE_CONTENT_SIGNAL")
    heartbeat.trend_signals(selected, max_per_topic=3)
    return len(calls), calls


def test_heartbeat_topics_are_bounded_and_canonical_first():
    one = heartbeat.bounded_topics(["business funding"])
    five = heartbeat.bounded_topics(["legacy-1", "legacy-2", *heartbeat.TOPICS])
    fifteen = heartbeat.bounded_topics([*(f"legacy-{i}" for i in range(15))])

    assert one == ["business funding"]
    assert five == list(heartbeat.TOPICS)
    assert len(fifteen) == heartbeat.MAX_TOPICS_PER_WAKE


def test_related_candidate_volume_does_not_create_unbounded_source_reads(monkeypatch):
    counts = []
    for gap_count in (1, 5, 15):
        requested = ["business funding"] * gap_count
        count, calls = _count_signal_reads(monkeypatch, requested)
        counts.append(count)
        assert len(calls) == 2

    assert counts == [2, 2, 2]


def test_heartbeat_source_reads_are_bounded_for_one_three_and_ten_configured_topics(monkeypatch):
    one, _ = _count_signal_reads(monkeypatch, ["business funding"])
    three, _ = _count_signal_reads(monkeypatch, list(heartbeat.TOPICS))
    ten, _ = _count_signal_reads(monkeypatch, [f"configured-{i}" for i in range(10)])
    assert (one, three, ten) == (2, 2, 2)


def test_content_intelligence_batches_existing_signal_identity_lookup(monkeypatch):
    queries = []
    writes = []
    identities = ["google-related:business funding:signal-a",
                  "google-related:business funding:signal-b",
                  "google-related:business funding:signal-c"]

    def get(table, query):
        assert table == "research_sources"
        queries.append(query)
        return 200, [{"id": f"existing-{i}", "title": f"signal-{i}", "url": None,
                      "metadata": {"signal_identity": identity, "snapshots": []}}
                     for i, identity in enumerate(identities)]

    monkeypatch.setattr(content.sb, "get", get)
    monkeypatch.setattr(content.sb, "insert", lambda table, rows, **kwargs:
                        (writes.append((table, rows, kwargs)) or (204, [])))
    monkeypatch.setattr(content, "_public_json", lambda _url: ["fixture", ["signal-a", "signal-b", "signal-c"]])

    result = content.trend_signals(["business funding"], max_per_topic=3)

    assert result["related_queries_found"] == 3
    assert len(queries) == 1
    assert "metadata->>signal_identity=in." in queries[0]
    assert len(writes) == 1
    table, rows, options = writes[0]
    assert table == "research_sources?on_conflict=id"
    assert len(rows) == 3
    assert options["prefer"] == "resolution=merge-duplicates,return=minimal"


def test_legacy_topic_fanout_is_bounded_after_fix(monkeypatch):
    calls = _mock_source_reads(monkeypatch)
    legacy_topics = [f"legacy-topic-{i}" for i in range(17)]
    # Before the topic cap, 17 topics × 3 signals generated an identity lookup
    # and insert readback per signal, plus the initial source snapshot.
    heartbeat.sources("YOUTUBE_CONTENT_SIGNAL")
    heartbeat.trend_signals(legacy_topics, max_per_topic=3)
    assert len(calls) == 2

    calls.clear()
    bounded = heartbeat.bounded_topics(legacy_topics)
    heartbeat.sources("YOUTUBE_CONTENT_SIGNAL")
    heartbeat.trend_signals(bounded, max_per_topic=3)
    assert len(bounded) == 3
    assert len(calls) == 2


def test_startup_daemon_does_not_treat_process_start_as_market_schedule():
    # The production daemon initializes the last-run monotonic timestamp at
    # startup; no Market Intelligence wake is due until its normal interval.
    assert market_wake_due(100.0, 100.1, 1200) is False
    assert market_wake_due(100.0, 1299.9, 1200) is False
    assert market_wake_due(100.0, 1300.0, 1200) is True


def test_empty_research_queue_waits_after_one_bounded_wake():
    assert idle_research_wake_requires_wait(
        daemon=True, queue_work_ready=False, batch_started=1, batch_limit=3
    ) is True
    assert idle_research_wake_requires_wait(
        daemon=True, queue_work_ready=True, batch_started=1, batch_limit=3
    ) is False
    assert idle_research_wake_requires_wait(
        daemon=False, queue_work_ready=False, batch_started=1, batch_limit=3
    ) is False
