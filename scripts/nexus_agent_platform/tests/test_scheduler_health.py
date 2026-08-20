from __future__ import annotations

import json

from nexus_agent_platform.phase15 import scheduler_health


def test_scheduler_health_persists_required_fields(monkeypatch, tmp_path):
    path = tmp_path / "scheduler_health.json"
    monkeypatch.setattr(scheduler_health, "HEALTH_PATH", path)
    monkeypatch.setattr(scheduler_health, "_launchd_labels", lambda: {scheduler_health.SCHEDULER_LABEL})
    monkeypatch.setattr(scheduler_health, "_git_commit", lambda: "test-commit")
    monkeypatch.setattr(scheduler_health, "utc_now", lambda: "2026-08-20T00:00:00+00:00")

    context = scheduler_health.begin_dispatch()
    result = scheduler_health.complete_dispatch(context, success=True)

    assert result["status"] == "HEALTHY"
    assert result["scheduler_label"] == scheduler_health.SCHEDULER_LABEL
    assert result["scheduler_instance"] == context["scheduler_instance"]
    assert result["successful_dispatches"] == 1
    assert result["failed_dispatches"] == 0
    assert result["last_exit_code"] == 0
    assert result["duplicate_detected"] is False
    assert set(result["registered_loops"]) == {
        "open_source_scout_loop",
        "research_intake_loop",
        "revenue_opportunity_loop",
        "seo_opportunity_loop",
    }
    assert json.loads(path.read_text())["updated_at"] == "2026-08-20T00:00:00+00:00"
