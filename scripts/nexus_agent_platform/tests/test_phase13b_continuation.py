from nexus_agent_platform.phase13b.continuation import build_continuation_assessment


def test_continuation_reruns_only_prior_gaps_and_closes_bounded_tasks():
    report = build_continuation_assessment()
    assert report["hermes"]["counts"] == {"certified": 12, "partial": 1, "failed": 0, "untested": 0}
    assert report["alpha"]["counts"] == {"certified": 11, "partial": 1, "failed": 0, "untested": 0}
    assert report["continuation"]["skipped_certified_tasks"]["hermes"] == ["H01", "H02", "H05", "H08", "H11", "H12"]
    assert report["continuation"]["skipped_certified_tasks"]["alpha"] == ["A02", "A03", "A04", "A08", "A09", "A10"]
    assert report["phase14_readiness"]["decision"] == "GO"


def test_continuation_preserves_unknown_historical_telemetry_and_real_new_telemetry():
    report = build_continuation_assessment()
    historical = next(task for task in report["hermes"]["tasks"] if task["task_id"] == "H01")
    new = next(task for task in report["hermes"]["tasks"] if task["task_id"] == "H03")
    assert historical["telemetry"]["input_tokens"] == "UNKNOWN"
    assert new["telemetry"]["input_tokens"] == 0
    assert new["telemetry"]["verifier_result"] != "UNKNOWN"


def test_opencode_explicit_probe_and_governance_boundaries_are_preserved():
    report = build_continuation_assessment()
    assert report["workers"]["opencode"]["status"] == "AVAILABLE"
    assert report["workers"]["opencode"]["probe_telemetry"]["model"] == "opencode/mimo-v2.5-free"
    assert report["workers"]["opencode"]["probe_telemetry"]["provider_cost_usd"] == 0
    assert report["governance"]["client_portal_changes"] == "NONE"
    assert report["governance"]["production_telegram_changes"] == "NONE"
    assert report["governance"]["nova_authority"] == "UNCHANGED"
