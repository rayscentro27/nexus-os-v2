from nexus_agent_platform.task_request_eligibility import task_request_is_dispatch_eligible


def test_historical_task_request_never_becomes_eligible_from_status_alone():
    row = {"status": "requested", "approved_by_ray": "Ray", "payload": {}}
    assert task_request_is_dispatch_eligible(row) is False


def test_migration_requires_explicit_review_and_exact_current_v2_marker():
    row = {
        "status": "approved",
        "approved_by_ray": "Ray",
        "payload": {
            "nexus_dispatch_eligibility": "CURRENT_V2_MIGRATED",
            "nexus_dispatch_migration_id": "migration-1",
            "nexus_dispatch_migration_approved_by_ray": "Ray",
        },
    }
    assert task_request_is_dispatch_eligible(row) is True
    row["payload"]["nexus_dispatch_eligibility"] = "LEGACY_HISTORICAL"
    assert task_request_is_dispatch_eligible(row) is False
