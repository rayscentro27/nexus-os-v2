from datetime import datetime, timedelta, timezone

import nexus_agent_platform.research_lane_scheduler as scheduler


class _EmptyQueue:
    def load(self):
        return {"items": []}

    def enqueue(self, **_fields):
        return None

    def claim_next_for_objective(self, **_kwargs):
        return None


def test_monitored_fallback_does_not_select_recent_unchanged_source(monkeypatch):
    now = datetime(2026, 9, 28, tzinfo=timezone.utc)
    monkeypatch.setattr(scheduler, "_now", lambda: now)
    monkeypatch.setattr(scheduler, "_hydrate_refresh_state_from_history", lambda: None)
    monkeypatch.setattr(scheduler, "ensure_live_program_work", lambda: {})
    monkeypatch.setattr(scheduler, "ensure_permanent_source_work", lambda: {})
    monkeypatch.setattr(scheduler, "ensure_registry", lambda: [{
        "lane_id": "YOUTUBE_CONTENT", "name": "YouTube", "enabled": True,
        "selection_count": 10, "priority": "P2", "last_source_id": "duplicate-video",
    }])
    monkeypatch.setattr(scheduler, "select_priority_work", lambda **_kwargs: None)
    monkeypatch.setattr(scheduler, "_select_live_service_work", lambda *_args: None)
    monkeypatch.setattr(scheduler, "default_queue", lambda: _EmptyQueue())
    monkeypatch.setattr(scheduler, "_read_governed", lambda _name: [])
    monkeypatch.setattr(scheduler, "_lane_context", lambda *_args: {
        "high": 0, "medium": 0, "questions": 0, "investigations": 0,
        "followups": 0, "theses": 0, "oldest_age_seconds": 0,
        "watched_sources": 1, "mission_pending": 0,
    })
    monkeypatch.setattr(scheduler, "_read_source_refresh_state", lambda: {
        "YOUTUBE_CONTENT:duplicate-video": {
            "lane_id": "YOUTUBE_CONTENT", "source_id": "duplicate-video",
            "last_status": "DUPLICATE_UNCHANGED", "consecutive_duplicate_count": 1,
            "next_eligible_refresh_at": (now + timedelta(hours=1)).isoformat(),
        }
    })
    result = scheduler.select_lane(blocked_buckets=set())
    assert result["no_source_selected"] is True
    assert result["selection_reason"] == "queue_empty_no_nonterminal_source"
