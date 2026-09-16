from datetime import datetime, timezone, timedelta

from scripts.operations import productivity_monitor as monitor


def test_process_alive_with_repeated_wakes_is_degraded_or_stalled():
    hb = {"last_real_output": "2026-09-16T00:00:00+00:00"}
    events = [{"status": "FAILED_RETRYABLE"}, {"status": "FAILED_RETRYABLE"}, {"status": "FAILED_RETRYABLE"}]
    result = monitor.evaluate_research(
        process_running=True,
        heartbeat=hb,
        execution_events=events,
        now_dt=datetime(2026, 9, 16, 0, 1, tzinfo=timezone.utc),
    )
    assert result["process_health"] == "HEALTHY"
    assert result["productivity_health"] == "STALLED"
    assert result["classification"] == "SCHEDULED_WAKE_FAILED"


def test_future_scheduled_wake_is_not_stale():
    hb = {"last_real_output": "2026-09-16T02:01:18+00:00", "next_wake": "2026-09-16T02:21:18+00:00"}
    result = monitor.evaluate_research(
        process_running=True,
        heartbeat=hb,
        now_dt=datetime(2026, 9, 16, 2, 14, tzinfo=timezone.utc),
    )
    assert result["process_health"] == "HEALTHY"
    assert result["productivity_health"] == "IDLE_LEGITIMATE"


def test_healthy_output_is_not_incident(tmp_path, monkeypatch):
    monkeypatch.setattr(monitor, "INCIDENTS", tmp_path / "incidents.jsonl")
    monkeypatch.setattr(monitor, "NOTIFICATIONS", tmp_path / "notifications.jsonl")
    incident = monitor.record_incident(worker="Research Worker", classification="SCHEDULED_WAKE_FAILED", severity="CRITICAL", details={"summary": "test"}, recovery_action="retry")
    assert incident["incident_id"]
    recovered = monitor.close_incident(incident["incident_id"], reason="healthy wake resumed")
    assert recovered["state"] == "RECOVERED"


def test_delivery_is_idempotent_by_pending_event(tmp_path, monkeypatch):
    monkeypatch.setattr(monitor, "NOTIFICATIONS", tmp_path / "notifications.jsonl")
    monkeypatch.setattr(monitor, "DELIVERIES", tmp_path / "deliveries.jsonl")
    monitor._append(monitor.NOTIFICATIONS, {"notification_id": "notif_1", "incident_id": "inc_1", "state": "PENDING", "text": "test"})
    result = monitor.deliver_pending(lambda _chat, _text: {"ok": True}, {123})
    assert result["delivered"] == 1
