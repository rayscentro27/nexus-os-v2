from scripts.systems.environment_baseline import validate_baseline


def test_pre_certification_baseline_requires_secret_free_non_autonomous_state():
    baseline = {
        "BASELINE_ID": "test",
        "STATUS": "PRE_CERTIFICATION",
        "CANONICAL_REPO": "/repo",
        "CANONICAL_BRANCH": "main",
        "LOCAL_CANONICAL_COMMIT": "abc",
        "CANONICAL_PYTHON": {"version": "3.12"},
        "EXPECTED_LAUNCHD_LABELS": [],
        "EXPECTED_ENABLED_LAUNCHD": [],
        "EXPECTED_CRON": {},
        "EXPECTED_PM2": {},
        "EXPECTED_HERMES_SCHEDULES": {},
        "EXPECTED_OPENCLAW_SCHEDULES": {},
        "EXPECTED_LOCAL_PORTS": {},
        "EXPECTED_PROVIDER_CALLER_REGISTRY_HASH": "hash",
        "EXPECTED_SECRET_CONSUMER_REGISTRY_HASH": "hash",
        "EXPECTED_ENVIRONMENTS": {},
        "EXPECTED_RUNTIME_LIMITS": {},
        "CREATED_AT": "2026-10-09T00:00:00Z",
        "CERTIFICATION_CAMPAIGN_ID": "test",
        "AUTONOMOUS_ENABLEMENT": False,
        "SECRET_VALUES_INCLUDED": False,
    }
    assert validate_baseline(baseline) == []
    baseline["AUTONOMOUS_ENABLEMENT"] = True
    assert "AUTONOMOUS_ENABLEMENT_MUST_BE_FALSE" in validate_baseline(baseline)
