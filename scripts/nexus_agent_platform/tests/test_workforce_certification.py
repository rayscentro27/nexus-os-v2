from nexus_agent_platform.workforce.certification import (
    CLASSIFICATIONS,
    build_provider_adapters,
    build_workforce_report,
)


def test_provider_adapters_are_provider_specific_and_non_mutating():
    adapters = build_provider_adapters()
    assert set(adapters) >= {"codex", "opencode", "mimo", "kilo", "openhands", "local_python"}
    assert adapters["codex"].execution_command[1] == "exec"
    assert adapters["opencode"].execution_command[1] == "run"
    assert adapters["mimo"].execution_command[1] == "run"
    assert adapters["kilo"].execution_command is None
    assert adapters["kilo"].execution_probe is None
    assert adapters["codex"].supports_existing_login is True


def test_workforce_report_preserves_certification_boundaries():
    report = build_workforce_report()
    workers = {row["worker_id"]: row for row in report["workers"]}
    assert workers["codex"]["classification"] == "AVAILABLE"
    assert workers["opencode"]["classification"] == "UNAVAILABLE"
    assert workers["mimo"]["classification"] == "INSTALLED_UNPROVEN"
    assert workers["kilo"]["classification"] == "INSTALLED_UNPROVEN"
    assert workers["openhands"]["classification"] == "NOT_INSTALLED"
    assert workers["local_python"]["classification"] == "AVAILABLE"
    assert set(workers["codex"]["classification"]) <= set("ABCDEFGHIJKLMNOPQRSTUVWXYZ_")
    assert set(report["allowed_classifications"]) == CLASSIFICATIONS
    assert report["kilo_recommendation"]["decision"] == "DEFER"
    assert report["kilo_recommendation"]["registry_action"] == "DO_NOT_REGISTER_AS_EXECUTABLE"
    assert report["governance"]["software_installation"] == "DISABLED"
    assert report["governance"]["provider_login_mutation"] == "DISABLED"


def test_agent_certifications_keep_upstream_lab_separate():
    report = build_workforce_report()
    agents = {row["worker_id"]: row for row in report["agent_certifications"]}
    assert set(agents) == {"hermes_upstream", "nexus_hermes", "alpha", "hermes_nova"}
    assert agents["hermes_upstream"]["classification"] == "DEFERRED"
    assert agents["nexus_hermes"]["classification"] == "AVAILABLE"
    assert agents["alpha"]["classification"] == "AVAILABLE"
    assert agents["hermes_nova"]["classification"] == "AVAILABLE"
