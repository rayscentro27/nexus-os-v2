from nexus_agent_platform.wp9e_capabilities import browser_limits, browser_placement, talent_cost_card


def test_browser_limits_are_conservative_for_measured_oracle():
    limits = browser_limits(available_ram_gib=20, cpu_count=4)
    assert limits.max_browser_sessions == 2
    assert limits.max_tabs_per_session == 5
    assert limits.cleanup_on_exit is True


def test_heavy_browser_work_goes_remote_when_oracle_healthy():
    row = browser_placement(estimated_ram_mb=1600, duration_seconds=240, tabs=4,
                             auth_required=False, privacy="INTERNAL", oracle_health="HEALTHY")
    assert row["run_location"] == "ORACLE_REMOTE"


def test_heavy_work_defers_when_oracle_unavailable():
    row = browser_placement(estimated_ram_mb=1600, duration_seconds=240, tabs=4,
                             auth_required=False, privacy="INTERNAL", oracle_health="UNAVAILABLE")
    assert row["run_location"] == "DEFER"


def test_talent_cost_card_does_not_call_open_source_free_runtime():
    row = talent_cost_card("Aider", license_cost="$0 Apache-2.0", model_cost="UNKNOWN",
                           compute_cost="existing host only", free_tier="none bundled",
                           unknown_costs=["model provider pricing", "task token volume"],
                           recommendation="research only; no install without route")
    assert row["cost_class"] == "USAGE_DEPENDENT"
    assert row["unknown_costs"]
