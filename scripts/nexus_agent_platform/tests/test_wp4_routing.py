import pytest

from nexus_agent_platform.loops.routing import resolve_route


def test_route_resolves_skill_worker_and_executor():
    route = resolve_route("system-operations", "NEXUS_OPERATIONS_WORKER", authority_class="internal_read_only", executor_id="daily_system_operations")
    assert route["profile"] == "nexusworker"
    assert route["model_policy"] == "LOCAL_PRIVATE"


def test_route_rejects_worker_skill_mismatch():
    with pytest.raises(ValueError, match="NO_SKILL_MATCH"):
        resolve_route("funding-readiness", "NEXUS_OPERATIONS_WORKER", authority_class="internal_review")


def test_route_rejects_executor_mismatch():
    with pytest.raises(ValueError, match="SKILL_EXECUTOR_NOT_ALLOWED"):
        resolve_route("system-operations", "NEXUS_OPERATIONS_WORKER", authority_class="internal_read_only", executor_id="arbitrary_shell")
