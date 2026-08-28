from nexus_agent_platform.capabilities import shared
from nexus_agent_platform.agents import hermes


def _health(monkeypatch, processes, failures=None):
    monkeypatch.setattr(shared, "_nk_get_process_registry_live", lambda: {"status": "success", "processes": processes})
    monkeypatch.setattr(hermes, "_get_failure_report", lambda: {"working": "ok", "needs_attention": ""})
    monkeypatch.setattr(hermes, "_get_process_failures", lambda: {"status": "ok", "total": failures or 0, "by_status": {}})
    return shared._handle_system_health_inner(trace_id="test")


def test_manual_enabled_process_without_status_running_is_not_unknown(monkeypatch):
    result = _health(monkeypatch, [{"process_id": "system_health", "configuration_state": "enabled", "execution_mode": "ACTIVE_INTERNAL", "schedule": "manual", "runtime_state": "simulated", "last_run": None}])
    assert result["data"]["process_states"][0]["state"] == "CONFIGURED_ENABLED"
    assert result["data"]["overall_status"] == "HEALTHY"


def test_stale_scheduled_process_is_degraded_not_schema_unknown(monkeypatch):
    result = _health(monkeypatch, [{"process_id": "telegram_operator", "configuration_state": "enabled", "execution_mode": "TELEGRAM_OPERATOR", "schedule": "polling", "runtime_state": "skipped", "last_run": "2020-01-01T00:00:00+00:00"}])
    assert result["data"]["process_states"][0]["state"] == "STALE"
    assert result["data"]["overall_status"] == "DEGRADED"


def test_active_operator_pause_is_expected(monkeypatch):
    result = _health(monkeypatch, [{"process_id": "active_operator", "configuration_state": "enabled", "execution_mode": "ACTIVE_INTERNAL", "schedule": "manual", "runtime_state": "simulated", "last_run": None}])
    assert result["data"]["process_states"][0]["state"] == "PAUSED_EXPECTED"
