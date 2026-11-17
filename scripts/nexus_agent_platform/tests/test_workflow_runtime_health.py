from datetime import datetime, timezone

import pytest

from scripts.nexus_agent_platform import workflow_runtime_health as health
from scripts.nexus_agent_platform.agent_control_plane import AuthorizationDenied
from scripts.nexus_agent_platform.durable_jobs import DurableJobStore
from scripts.nexus_agent_platform.workflow_fabric import WorkflowController, WorkflowStateStore, new_workflow


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


def test_controller_rejects_stale_health_observation():
    old = {"MAC_MINI": {"status": "HEALTHY", "observed_at": "2026-11-17T10:00:00+00:00"}}
    controller = WorkflowController(WorkflowStateStore(DurableJobStore(":memory:")),
                                    runtime_health_observations=old)
    workflow = new_workflow(objective="Check GoClear funding readiness", owner="RAY", created_by="RAY")
    step = next(s for s in workflow["steps"] if s["step_id"] == "RESEARCH_PLAN")
    # The health adapter filters the old observation before the authorization router sees it.
    assert controller.runtime_health == {}
    with pytest.raises(AuthorizationDenied, match="CAPABILITY_UNAVAILABLE"):
        controller.authorize_step(workflow, step)
