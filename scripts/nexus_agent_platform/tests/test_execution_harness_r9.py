from pathlib import Path

from nexus_agent_platform.execution_harness import capability_readiness, material_delta, worker_environment_preflight


def test_engineering_preflight_uses_actual_worker_environment():
    result = worker_environment_preflight("engineering.portal_beta", Path(__file__).parents[3])
    assert result["ready"] is True
    assert result["executables"]["node"]["available"]
    assert result["executables"]["npm"]["available"]
    assert result["command_policy"]["arbitrary_shell"] is False


def test_readiness_distinguishes_worker_access_and_authority():
    result = capability_readiness("engineering.portal_beta", Path(__file__).parents[3])
    assert all(item["worker_accessible"] == item["unattended_runtime"] for item in result["matrix"])
    assert all(item["authorized"] for item in result["matrix"])


def test_retry_requires_material_delta():
    previous = {"strategy_fingerprint": "a", "environment_fingerprint": "b", "tools_used": ["npm"], "evidence": []}
    assert material_delta(previous, dict(previous)) == []
    current = {**previous, "environment_fingerprint": "c", "evidence": ["receipt.json"]}
    assert set(material_delta(previous, current)) == {"NEW_ENVIRONMENT", "NEW_EVIDENCE"}
