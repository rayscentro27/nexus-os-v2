from datetime import datetime, timezone

from scripts.nexus_agent_platform import workflow_runtime_health as health


def test_fresh_health_keeps_only_recent_positive_observations():
    now = datetime(2026, 11, 17, 12, tzinfo=timezone.utc)
    observations = {
        "MAC_MINI": {"status": "HEALTHY", "observed_at": now.isoformat()},
        "MODAL_GPU": {"status": "HEALTHY", "observed_at": "2026-11-17T11:00:00+00:00"},
        "CONTABO": {"status": "DEGRADED", "observed_at": now.isoformat()},
        "ORACLE_HERMES": {"status": "HEALTHY"},
    }
    assert health.fresh_environment_health(observations, now=now, max_age_seconds=300) == {
        "MAC_MINI": "HEALTHY"
    }


def test_auth_challenge_is_not_reported_as_success():
    original = health.probe_http
    try:
        health.probe_http = lambda *_args, **_kwargs: {
            "status": "AUTH_REQUIRED", "http_status": 401, "observed_at": "now"
        }
        result = health.probe_mac_research()
    finally:
        health.probe_http = original
    assert result["checks"]["research_mcp"]["status"] == "AUTH_REQUIRED"
    assert result["status"] == "DEGRADED"
