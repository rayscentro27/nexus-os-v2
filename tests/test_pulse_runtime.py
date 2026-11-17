from __future__ import annotations

import datetime as dt

from scripts.research import pulse_runtime as pulse


def test_pulse_schedule_uses_existing_due_registry_and_caps_one_job(monkeypatch):
    due = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=1)).isoformat()
    monkeypatch.setattr(pulse, "bootstrap", lambda: {"status": "PASS"})
    monkeypatch.setattr(pulse, "_rows", lambda table, query: [
        {"job_id": "PULSE_FLASH_SCAN", "cadence_seconds": 7200, "next_run_at": due},
        {"job_id": "PULSE_GENERAL_SCAN", "cadence_seconds": 14400, "next_run_at": due},
    ] if table == "pulse_schedule_registry" else [])
    ran = []
    monkeypatch.setattr(pulse, "_run_job", lambda job, run_id: ran.append(job) or {"status": "NO_MATERIAL_TREND_CHANGE"})
    monkeypatch.setattr(pulse.sb, "update", lambda *args, **kwargs: (204, None))
    monkeypatch.setattr(pulse.sb, "health", lambda *args, **kwargs: (201, None))
    monkeypatch.setattr(pulse, "_upsert", lambda *args, **kwargs: (True, {}))
    monkeypatch.setattr(pulse.sb, "get", lambda *args, **kwargs: (200, [{"run_id": "persisted"}]))
    result = pulse.tick(max_jobs=1)
    assert ran == ["PULSE_FLASH_SCAN"]
    assert result["status"] == "PASS"
    assert result["run_receipts"][0]["receipt_readback"] is True


def test_trend_scores_keep_unobserved_growth_fields_null():
    score = pulse._score({"title": "Small business automation", "views": 2500, "likes": 100,
                          "comments": 20, "url": "https://www.youtube.com/watch?v=example",
                          "metrics": {"views_per_hour": 50, "age_days": 1}}, 1)
    assert score["components"]["VELOCITY_SCORE"] > 0
    assert score["components"]["ACCELERATION_SCORE"] is None
    assert score["components"]["SEARCH_GROWTH_SCORE"] is None
    assert score["components"]["SOURCE_CONFIDENCE_SCORE"] == 95


def test_flash_rss_storage_batches_identity_lookup_and_upsert(monkeypatch):
    from nexus_agent_platform import content_intelligence as content
    calls = []
    def lookup(identities):
        calls.append(("lookup", tuple(identities)))
        return {}
    def persist(source_type, candidates, *, existing_by_identity):
        calls.append(("upsert", source_type, len(candidates)))
        return {"readback": True, "persisted": len(candidates),
                "by_identity": {identity: {"source_id": f"id-{i}", "readback": True}
                                for i, (_, identity, *_rest) in enumerate(candidates)}}
    monkeypatch.setattr(content, "_source_lookup_many", lookup)
    monkeypatch.setattr(content, "persist_signals_batch", persist)
    monkeypatch.setattr(content, "persist_signal", lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError("per-item signal persistence must not be used")))
    items = [{"source": "GOOGLE_NEWS", "url": f"https://example.test/{i}",
              "title": f"Signal {i}", "publisher": "Reuters"} for i in range(10)]
    assert pulse._store_rss(items) == 10
    assert [call[0] for call in calls] == ["lookup", "upsert"]
    assert calls[1][2] == 10


def test_snapshot_delta_uses_real_prior_platform_observations(monkeypatch):
    observed = dt.datetime(2026, 10, 7, 12, tzinfo=dt.timezone.utc)
    monkeypatch.setattr(pulse, "_rows", lambda *args: [{
        "observed_at": (observed - dt.timedelta(hours=2)).isoformat(),
        "views": 1000,
        "observed_data": {"interval_views_per_hour": 100},
    }])
    delta = pulse._snapshot_delta("trend_test", 1400, observed)
    assert delta["view_growth"] == 40
    assert delta["interval_views_per_hour"] == 200
    assert delta["acceleration"] == 50


def test_campaign_handoff_requires_human_approval_and_never_publishes(monkeypatch):
    payloads = []
    monkeypatch.setattr(pulse, "_upsert", lambda table, key, row: payloads.append((table, row)) or (True, row))
    trend = {"trend_id": "trend_example", "title": "Observed trend", "status": "VERIFIED", "trend_class": "SHORT_TREND",
             "expected_half_life": "DAYS_TO_WEEKS", "confidence": 0.8, "notebook_id": "notebook-id",
             "observed_data": {"video": {"url": "https://www.youtube.com/watch?v=example", "views": 1234}}}
    result = pulse._make_campaign(trend)
    assert result and result["state"] == "READY_FOR_MARKETING_REVIEW"
    brief = next(row for table, row in payloads if table == "pulse_campaign_briefs")
    handoff = next(row for table, row in payloads if table == "pulse_handoffs")
    assert brief["publish_state"] == "NOT_PUBLISHED"
    assert brief["ray_approval_required"] is True
    assert handoff["to_department"] == "MARKETING"
