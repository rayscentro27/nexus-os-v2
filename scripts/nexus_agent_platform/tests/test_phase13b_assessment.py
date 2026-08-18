from nexus_agent_platform.phase13b.assessment import build_phase13b_assessment


def test_phase13b_counts_are_evidence_backed_and_gate_phase14():
    report = build_phase13b_assessment()
    assert report["hermes"]["counts"] == {"certified": 6, "partial": 5, "failed": 0, "untested": 2}
    assert report["alpha"]["counts"] == {"certified": 6, "partial": 4, "failed": 0, "untested": 2}
    assert report["phase14_readiness"]["decision"] == "NO-GO"
    assert report["secondary_ai_worker"]["status"] == "NOT_AVAILABLE"


def test_phase13b_preserves_worker_and_installation_boundaries():
    report = build_phase13b_assessment()
    assert report["workers"]["codex"]["status"] == "AVAILABLE"
    assert report["workers"]["mimo"]["status"] == "INSTALLED_UNPROVEN"
    assert report["workers"]["kilo"]["status"] == "INSTALLED_UNPROVEN"
    assert report["workers"]["opencode"]["status"] == "UNAVAILABLE"
    assert report["crawl4ai"]["installed"] is False
    assert report["crawl4ai"]["pilot"] == "NOT_RUN"
    assert report["openhands"]["installed"] is False
    assert report["openhands"]["decision"] == "DEFER"


def test_phase13b_certification_does_not_use_client_pii_or_promote_gaps():
    report = build_phase13b_assessment()
    serialized = str(report).lower()
    assert "client_pii" not in serialized
    assert "ray's approval" not in serialized
    assert all(task["status"] != "PROMOTED" for subject in (report["hermes"], report["alpha"]) for task in subject["tasks"])
    assert report["fallback_routing"]["status"] == "PASS"
