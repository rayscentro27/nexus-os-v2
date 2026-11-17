from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import oracle_lifecycle_cert_adapter as adapter
import oracle_lifecycle_cert_transport as transport
from release_lifecycle import FixedNovaHost, NovaReleasePolicy


def test_cert_policy_uses_only_certification_roots_and_fixed_service():
    policy = NovaReleasePolicy(mode="certification")
    cert_root = Path("/home/opc/.nexus/certification/nova-lifecycle").resolve()
    assert policy.service == "nova-release-lifecycle-cert.service"
    for root in (policy.release_root, policy.staging_root, policy.receipt_root,
                 policy.runtime_state_root):
        assert root.is_relative_to(cert_root)
    assert policy.dropin_root == Path(
        "/home/opc/.config/systemd/user/nova-release-lifecycle-cert.service.d").resolve()
    with pytest.raises(ValueError, match="NOVA_SERVICE_IS_FIXED"):
        NovaReleasePolicy(service="nova-telegram-oracle.service", mode="certification")


def test_adapter_rejects_production_or_arbitrary_target_inputs():
    with pytest.raises(ValueError, match="CERT_ARGUMENT_SCHEMA_INVALID"):
        adapter.invoke("nova.lifecycle.cert.status", {"service": "nova-telegram-oracle.service"})
    with pytest.raises(ValueError, match="CERT_RELEASE_NOT_ALLOWED"):
        adapter.invoke("nova.lifecycle.cert.validate", {"candidate_release": "/tmp/anything"})
    with pytest.raises(ValueError, match="CERT_CAPABILITY_NOT_ALLOWED"):
        adapter.invoke("shell.arbitrary", {"command": "id"})


def test_activation_without_test_approval_is_blocked_without_mutation():
    result = adapter.invoke("nova.lifecycle.cert.activate", {
        "deployment_id": "deploy_" + "a" * 32,
        "candidate_release": "cert-release-b",
        "candidate_hash": "b" * 64,
        "current_release": "cert-release-a",
    })
    assert result == {"status": "BLOCKED", "reason": "CERT_APPROVAL_REQUIRED", "mutations": 0}


def test_cert_approval_cannot_name_production_target(tmp_path):
    approvals = adapter.CertificationApprovalStore(tmp_path)
    with pytest.raises(PermissionError, match="TARGET_OR_OPERATION"):
        approvals.issue_test_approval("ACTIVATE", {
            "certification_target": "nova-telegram-oracle.service",
            "operation": "ACTIVATE", "candidate_release": "cert-release-b",
            "candidate_hash": "b" * 64, "deployment_id": "deploy_" + "a" * 32,
        })


def test_transport_never_accepts_service_path_or_command_arguments(monkeypatch):
    calls = []
    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        class Result:
            returncode = 0
            stdout = '{"service":"nova-release-lifecycle-cert.service"}\n'
            stderr = ""
        return Result()
    monkeypatch.setattr(transport, "_check_authority", lambda _runner: None)
    monkeypatch.setattr(transport, "_connection", lambda: ("opc", "161.153.40.41", Path("/identity")))
    transport.invoke("nova.lifecycle.cert.status", {}, runner=run)
    argv, kwargs = calls[0]
    assert argv[0] == "ssh" and "nova-release-lifecycle-cert.service" not in " ".join(argv)
    assert kwargs.get("shell") is not True
    with pytest.raises(ValueError, match="CERT_ARGUMENT_SCHEMA_INVALID"):
        transport.invoke("nova.lifecycle.cert.status", {"command": "systemctl restart"}, runner=run)
    with pytest.raises(ValueError, match="CERT_RELEASE_NOT_ALLOWED"):
        transport.invoke("nova.lifecycle.cert.stage", {"candidate_release": "nova-telegram-oracle.service"}, runner=run)


def test_fixed_host_systemd_actions_are_exact_and_service_scoped():
    calls = []
    def run(argv, **kwargs):
        calls.append(argv)
        class Result:
            returncode = 0
            stdout = "ok"
            stderr = ""
        return Result()
    host = FixedNovaHost(service="nova-release-lifecycle-cert.service", mode="certification", runner=run)
    for operation in ("daemon-reload", "restart", "status", "show"):
        host.systemctl(operation)
    assert calls == [
        ["systemctl", "--user", "daemon-reload"],
        ["systemctl", "--user", "restart", "nova-release-lifecycle-cert.service"],
        ["systemctl", "--user", "status", "nova-release-lifecycle-cert.service"],
        ["systemctl", "--user", "show", "nova-release-lifecycle-cert.service"],
    ]
