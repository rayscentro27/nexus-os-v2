import subprocess

from nexus_agent_platform.environment_drift_monitor import _git_status_snapshot, compare


def test_environment_drift_detected_without_autonomous_enablement():
    result = compare(
        {"repository": {"commit": "old"}, "launch_agents": [], "user_cron_sha256": "a"},
        {"repository": {"commit": "new"}, "launch_agents": [], "user_cron_sha256": "a"},
    )
    assert result["status"] == "DRIFT_DETECTED"
    assert result["action"] == "RECORD_INCIDENT_AND_FLAG_OPERATOR"
    assert result["autonomous_enablement"] is False
    assert result["can_create_business_work"] is False
    assert result["can_call_paid_provider"] is False
    assert result["can_enable_runtime"] is False
    assert result["can_restart_services"] is False


def test_matching_baseline_has_no_action():
    state = {"repository": {"commit": "same"}, "launch_agents": [], "user_cron_sha256": "a"}
    result = compare(state, state)
    assert result["status"] == "MATCH"
    assert result["differences"] == []
    assert result["action"] == "NO_ACTION"
    assert result["autonomous_enablement"] is False
    assert result["can_create_business_work"] is False
    assert result["can_call_paid_provider"] is False
    assert result["can_enable_runtime"] is False


def test_exact_authorized_freeze_commit_is_accepted_but_only_as_direct_child():
    expected = {
        "repository": {"path": "/canonical", "branch": "main", "commit": "parent"},
        "authorized_freeze_commit": {
            "parent_commit": "parent",
            "subject": "freeze certified Nexus integration baseline",
        },
    }
    exact_child = {
        "repository": {
            "path": "/canonical", "branch": "main", "commit": "freeze",
            "commit_parent": "parent", "commit_subject": "freeze certified Nexus integration baseline",
        }
    }
    assert compare(expected, exact_child)["status"] == "MATCH"
    wrong_parent = {"repository": {**exact_child["repository"], "commit_parent": "other"}}
    assert compare(expected, wrong_parent)["status"] == "DRIFT_DETECTED"
    wrong_subject = {"repository": {**exact_child["repository"], "commit_subject": "unreviewed change"}}
    assert compare(expected, wrong_subject)["status"] == "DRIFT_DETECTED"


def test_compare_includes_all_declared_local_fields():
    expected = {"provider_caller_registry_sha256": "old", "pm2_saved_state_sha256": "same"}
    actual = {"provider_caller_registry_sha256": "new", "pm2_saved_state_sha256": "same"}
    result = compare(expected, actual)
    assert result["status"] == "DRIFT_DETECTED"
    assert result["differences"] == [{"field": "provider_caller_registry_sha256", "expected": "old", "actual": "new"}]


def test_git_status_timeout_is_not_misreported_as_clean(monkeypatch, tmp_path):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs.get("timeout"))

    monkeypatch.setattr(subprocess, "run", timeout)
    state, output = _git_status_snapshot(tmp_path)
    assert state == "UNAVAILABLE_TIMEOUT"
    assert output == ""


def test_git_status_success_reports_available(monkeypatch, tmp_path):
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, " M tracked\n", ""))
    state, output = _git_status_snapshot(tmp_path)
    assert state == "AVAILABLE"
    assert output == " M tracked\n"
