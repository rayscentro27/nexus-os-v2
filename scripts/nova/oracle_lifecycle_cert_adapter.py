"""Certification-only, typed Oracle adapter for the Nova lifecycle controller.

This module has no production mode. Paths, service identity, release aliases,
systemd actions, and capabilities are fixed here; request JSON cannot override
any of them. It is intended to run on the Oracle user account through the
bounded operator transport, not through the read-only Oracle resolver.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any

from release_lifecycle import NovaReleaseController, NovaReleasePolicy, create_manifest


CERT_ROOT = Path("/home/opc/.nexus/certification/nova-lifecycle")
OPERATOR_ROOT = Path(__file__).resolve().parent
UNIT_FILE = Path("/home/opc/.config/systemd/user/nova-release-lifecycle-cert.service")
DROPIN_NAME = "90-cert-lifecycle.conf"
SERVICE = "nova-release-lifecycle-cert.service"
ALIAS_TO_RELEASE = {
    "cert-release-a": "nova-operator-v1-20261029-r101-cert-release-a",
    "cert-release-b": "nova-operator-v1-20261029-r102-cert-release-b",
    "cert-release-bad": "nova-operator-v1-20261029-r103-cert-release-bad",
    "cert-release-tampered": "nova-operator-v1-20261029-r104-cert-release-tampered",
}
CAPABILITIES = {
    "nova.lifecycle.cert.status", "nova.lifecycle.cert.stage",
    "nova.lifecycle.cert.validate", "nova.lifecycle.cert.activate",
    "nova.lifecycle.cert.verify", "nova.lifecycle.cert.rollback",
    "nova.lifecycle.cert.receipt",
}
DEPLOYMENT_RE = re.compile(r"deploy_[a-f0-9]{32}\Z")
APPROVAL_RE = re.compile(r"cert_appr_[a-f0-9]{32}\Z")


class CertificationApprovalStore:
    """Single-use approval records scoped to this certification service only."""

    def __init__(self, root: Path = CERT_ROOT / "approvals") -> None:
        self.root = root

    def issue_test_approval(self, operation: str, inputs: dict[str, Any]) -> str:
        if operation not in {"ACTIVATE", "ROLLBACK"}:
            raise ValueError("CERT_APPROVAL_OPERATION_NOT_ALLOWED")
        if inputs.get("certification_target") != SERVICE or inputs.get("operation") != operation:
            raise PermissionError("CERT_APPROVAL_TARGET_OR_OPERATION_MISMATCH")
        if inputs.get("candidate_release") not in ALIAS_TO_RELEASE:
            raise ValueError("CERT_APPROVAL_RELEASE_NOT_ALLOWED")
        if not re.fullmatch(r"[a-f0-9]{64}", str(inputs.get("candidate_hash", ""))):
            raise ValueError("CERT_APPROVAL_HASH_INVALID")
        if not DEPLOYMENT_RE.fullmatch(str(inputs.get("deployment_id", ""))):
            raise ValueError("CERT_APPROVAL_DEPLOYMENT_INVALID")
        self.root.mkdir(parents=True, exist_ok=True)
        approval_id = "cert_appr_" + uuid.uuid4().hex
        record = {"approval_id": approval_id, "certification_target": SERVICE,
                  "operation": operation, "inputs": inputs, "approved": True,
                  "consumed": False}
        _atomic_json(self.root / (approval_id + ".json"), record, 0o600)
        return approval_id

    def request(self, action_id: str, inputs: dict[str, Any], detail: dict[str, Any]) -> dict[str, Any]:
        return {"id": "", "action_id": action_id, "status": "approval_required",
                "input_summary": inputs, "detail": detail,
                "certification_target": SERVICE}

    def consume(self, approval_id: str, action_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
        if not APPROVAL_RE.fullmatch(str(approval_id)):
            raise PermissionError("CERT_APPROVAL_REQUIRED")
        path = self.root / (approval_id + ".json")
        if not path.is_file() or path.is_symlink():
            raise PermissionError("CERT_APPROVAL_NOT_FOUND")
        row = json.loads(path.read_text(encoding="utf-8"))
        expected_op = "ACTIVATE" if action_id == "nova.release.activate" else "ROLLBACK"
        if expected_op == "ACTIVATE":
            bound = {"deployment_id": inputs.get("deployment_id"),
                     "candidate_release": _alias_from_internal(inputs.get("candidate_release")),
                     "candidate_hash": inputs.get("candidate_hash"),
                     "current_release": _alias_from_internal(inputs.get("current_release")),
                     "dropin_name": inputs.get("dropin_name"),
                     "automatic_rollback_on_failure": inputs.get("automatic_rollback_on_failure"),
                     "certification_target": SERVICE, "operation": expected_op}
        else:
            bound = {"deployment_id": inputs.get("deployment_id"),
                     "candidate_release": _alias_from_internal(inputs.get("target_release")),
                     "candidate_hash": inputs.get("target_hash"),
                     "current_release": _alias_from_internal(inputs.get("current_release")),
                     "source_deployment_id": inputs.get("source_deployment_id"),
                     "certification_target": SERVICE, "operation": expected_op}
        if (row.get("certification_target") != SERVICE or row.get("operation") != expected_op
                or row.get("inputs") != bound or not row.get("approved") or row.get("consumed")):
            raise PermissionError("CERT_APPROVAL_BINDING_MISMATCH")
        row["consumed"] = True
        _atomic_json(path, row, 0o600)
        return row


def _alias_from_internal(value: Any) -> str:
    for alias, release in ALIAS_TO_RELEASE.items():
        if value == release:
            return alias
    raise ValueError("CERT_RELEASE_NOT_ALLOWED")


def _atomic_json(path: Path, value: dict[str, Any], mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp." + uuid.uuid4().hex)
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _release(alias: str) -> str:
    try:
        return ALIAS_TO_RELEASE[alias]
    except (KeyError, TypeError):
        raise ValueError("CERT_RELEASE_NOT_ALLOWED") from None


def _controller() -> NovaReleaseController:
    policy = NovaReleasePolicy(mode="certification")
    # Fail closed if a future policy edit moves any write root outside the
    # certification tree or changes the fixed systemd target.
    roots = (policy.release_root, policy.staging_root, policy.receipt_root,
             policy.runtime_state_root)
    resolved_cert_root = CERT_ROOT.resolve()
    if policy.service != SERVICE or any(not p.is_relative_to(resolved_cert_root) for p in roots):
        raise RuntimeError("CERTIFICATION_SCOPE_POLICY_MISMATCH")
    if policy.dropin_root != (UNIT_FILE.parent / (UNIT_FILE.name + ".d")).resolve():
        raise RuntimeError("CERTIFICATION_DROPIN_SCOPE_MISMATCH")
    return NovaReleaseController(policy=policy, approval_store=CertificationApprovalStore())


def _fixture_source(alias: str) -> str:
    # The deliberately bad candidate exits during startup, allowing the real
    # service verification branch to exercise automatic rollback.
    if alias == "cert-release-bad":
        return ("import os\\n"
                "print('RELEASE_ID=' + os.environ.get('NOVA_CERT_RELEASE_ID','UNKNOWN'), flush=True)\\n"
                "raise SystemExit(23)\\n").replace("\\n", "\n")
    return ("import argparse,os,signal,time\\n"
            "print('RELEASE_ID=' + os.environ.get('NOVA_CERT_RELEASE_ID','UNKNOWN'), flush=True)\\n"
            "p=argparse.ArgumentParser(); p.add_argument('--hold',action='store_true'); a=p.parse_args()\\n"
            "running=True\\n"
            "def stop(*_):\\n global running; running=False\\n"
            "signal.signal(signal.SIGTERM,stop); signal.signal(signal.SIGINT,stop)\\n"
            "if not a.hold: raise SystemExit(2)\\n"
            "while running: time.sleep(.2)\\n").replace("\\n", "\n")


def _stage(controller: NovaReleaseController, alias: str) -> dict[str, Any]:
    release = _release(alias)
    bundle = controller.policy.staging_root / release
    if bundle.exists():
        raise FileExistsError("CERT_FIXTURE_BUNDLE_ALREADY_EXISTS")
    worker = bundle / "scripts/nova/lifecycle_fixture_worker.py"
    worker.parent.mkdir(parents=True, exist_ok=False)
    worker.write_text(_fixture_source(alias), encoding="utf-8")
    digest, _ = create_manifest(bundle)
    for path in sorted(bundle.rglob("*"), reverse=True):
        path.chmod(0o555 if path.is_dir() else 0o444)
    bundle.chmod(0o555)
    result = controller.stage(candidate_release=release, bundle_id=release)
    result["status"] = "STAGED"
    result["external_release_id"] = alias
    result["manifest_hash"] = digest
    return result


def provision() -> dict[str, Any]:
    """Create the inert cert service and baseline A release; never prod Nova."""
    controller = _controller()
    release = _release("cert-release-a")
    release_path = controller.policy.release_root / release
    if not release_path.is_dir():
        _stage(controller, "cert-release-a")
    unit_text = ("[Unit]\\nDescription=Isolated Nova lifecycle certification fixture\\n"
                 "After=default.target\\n\\n[Service]\\nType=simple\\n"
                 f"WorkingDirectory={controller.policy.runtime_state_root}\\n"
                 f"ExecStart=/usr/bin/python3 {release_path}/scripts/nova/lifecycle_fixture_worker.py --hold\\n"
                 "Restart=always\\nRestartSec=1\\nNoNewPrivileges=yes\\nPrivateTmp=yes\\n\\n"
                 "[Install]\\nWantedBy=default.target\\n").replace("\\n", "\n")
    validation = controller.validate(candidate_release=release)
    if not validation["valid"]:
        raise RuntimeError("CERTIFICATION_BASELINE_RELEASE_INVALID")
    if UNIT_FILE.exists():
        if UNIT_FILE.is_symlink() or UNIT_FILE.read_text(encoding="utf-8") != unit_text:
            raise FileExistsError("CERTIFICATION_UNIT_NOT_ISOLATED")
    else:
        _atomic_bytes(UNIT_FILE, unit_text.encode("utf-8"), 0o600)
    controller.policy.runtime_state_root.mkdir(parents=True, exist_ok=True)
    controller.policy.dropin_root.mkdir(parents=True, exist_ok=True)
    active = controller.policy.dropin_root / DROPIN_NAME
    dropin_text = ("[Service]\\nExecStart=\\n"
                   f"ExecStart=/usr/bin/python3 {release_path}/scripts/nova/lifecycle_fixture_worker.py --hold\\n"
                   "Environment=\\n"
                   f"Environment=NOVA_CODE_ROOT={release_path}\\n"
                   f"Environment=PYTHONPATH={release_path}/scripts\\n"
                   f"Environment=NOVA_CERT_RELEASE_ID={release}\\n"
                   "Environment=NOVA_LIFECYCLE_CERTIFICATION=1\\n").replace("\\n", "\n")
    entries = list(controller.policy.dropin_root.iterdir())
    if active.exists():
        if active.is_symlink() or active.read_text(encoding="utf-8") != dropin_text:
            raise FileExistsError("CERTIFICATION_DROPIN_NOT_ISOLATED")
        if len(entries) != 1:
            raise FileExistsError("CERTIFICATION_DROPIN_DIRECTORY_NOT_EXCLUSIVE")
    else:
        if entries:
            raise FileExistsError("CERTIFICATION_DROPIN_DIRECTORY_NOT_EMPTY")
        controller._install_single_dropin(release_path, DROPIN_NAME, "deploy_" + "0" * 32)
    controller.host.systemctl("daemon-reload")
    controller.host.systemctl("restart")
    verification = controller.verify(expected_release=release)
    if not verification["pass"]:
        raise RuntimeError("CERTIFICATION_BASELINE_NOT_HEALTHY")
    return {"status": "PASS", "service": SERVICE, "release": "cert-release-a",
            "unit_file": str(UNIT_FILE), "dropin": str(active), "verification": verification}


def _atomic_bytes(path: Path, data: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp." + uuid.uuid4().hex)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def issue_test_approval(operation: str, *, deployment_id: str,
                        candidate_release: str, candidate_hash: str,
                        current_release: str, source_deployment_id: str = "") -> str:
    controller = _controller()
    candidate_internal = _release(candidate_release)
    if operation == "ACTIVATE":
        inputs = {"deployment_id": deployment_id, "candidate_release": candidate_release,
                  "candidate_hash": candidate_hash, "current_release": current_release,
                  "dropin_name": DROPIN_NAME, "automatic_rollback_on_failure": True,
                  "certification_target": SERVICE, "operation": operation}
    elif operation == "ROLLBACK":
        if not DEPLOYMENT_RE.fullmatch(source_deployment_id):
            raise ValueError("CERT_ROLLBACK_SOURCE_INVALID")
        inputs = {"deployment_id": deployment_id, "candidate_release": candidate_release,
                  "candidate_hash": candidate_hash, "current_release": current_release,
                  "source_deployment_id": source_deployment_id,
                  "certification_target": SERVICE, "operation": operation}
    else:
        raise ValueError("CERT_APPROVAL_OPERATION_NOT_ALLOWED")
    if not controller.validate(candidate_release=candidate_internal,
                                expected_manifest_hash=candidate_hash)["valid"]:
        raise ValueError("CERT_APPROVAL_CANDIDATE_INVALID")
    return CertificationApprovalStore().issue_test_approval(operation, inputs)


def certification_probe(name: str) -> dict[str, Any]:
    """Fixed certification harness probes; not exposed as operator capabilities."""
    controller = _controller()
    if name == "tamper-candidate":
        staged = _stage(controller, "cert-release-tampered")
        worker = controller.policy.release_root / _release("cert-release-tampered") / "scripts/nova/lifecycle_fixture_worker.py"
        worker.chmod(0o644)
        worker.write_text(worker.read_text(encoding="utf-8") + "# intentional certification tamper\n", encoding="utf-8")
        worker.chmod(0o444)
        checked = controller.validate(candidate_release=_release("cert-release-tampered"),
                                      expected_manifest_hash=staged["manifest_hash"])
        return {"tampered_candidate_rejected": not checked["valid"],
                "manifest_mismatches": checked["mismatches"]}
    if name == "mixed-release":
        active = controller.policy.dropin_root / DROPIN_NAME
        original = active.read_bytes()
        text = original.decode("utf-8")
        release_a = str(controller.policy.release_root / _release("cert-release-a"))
        release_b = str(controller.policy.release_root / _release("cert-release-b"))
        needle = f"Environment=NOVA_CODE_ROOT={release_a}"
        if needle not in text:
            raise RuntimeError("CERT_MIXED_PROBE_BASELINE_MISMATCH")
        try:
            controller._atomic_write(active, text.replace(needle,
                f"Environment=NOVA_CODE_ROOT={release_b}", 1).encode("utf-8"), 0o644)
            result = controller.verify(expected_release=_release("cert-release-a"))
            return {"mixed_release_rejected": not result["pass"], "verification": result}
        finally:
            controller._atomic_write(active, original, 0o644)
    if name == "security":
        probes: dict[str, bool] = {}
        for label, service in (
            ("production_nova", "nova-telegram-oracle.service"),
            ("hermes", "nexus-hermes-0225.service"),
            ("mcp", "nexus-mcp.service"),
            ("research", "nexus-research.service"),
            ("systems", "nexus-systems.service"),
            ("gateway", "nexus-gateway.service"),
            ("system_service", "sshd.service"),
            ("arbitrary_service", "arbitrary-user.service"),
        ):
            try:
                invoke("nova.lifecycle.cert.status", {"service": service})
            except (ValueError, PermissionError):
                probes[label] = True
            else:
                probes[label] = False
        for label, cap, args in (
            ("arbitrary_path", "nova.lifecycle.cert.stage", {"candidate_release": "cert-release-b", "path": "/etc/passwd"}),
            ("arbitrary_command", "shell.arbitrary", {"command": "id"}),
            ("production_dropin", "nova.lifecycle.cert.activate", {"deployment_id": "deploy_" + "a" * 32,
             "candidate_release": "cert-release-b", "candidate_hash": "0" * 64,
             "current_release": "cert-release-a", "approval_id": "cert_appr_" + "b" * 32,
             "dropin_name": "nova-telegram-oracle.service.d/unsafe.conf"}),
        ):
            try:
                invoke(cap, args)
            except (ValueError, PermissionError):
                probes[label] = True
            else:
                probes[label] = False
        try:
            CertificationApprovalStore(CERT_ROOT / "test-approval-probe").issue_test_approval(
                "ACTIVATE", {"certification_target": "nova-telegram-oracle.service",
                "operation": "ACTIVATE", "candidate_release": "cert-release-b",
                "candidate_hash": "0" * 64, "deployment_id": "deploy_" + "a" * 32})
            probes["production_approval"] = False
        except (ValueError, PermissionError):
            probes["production_approval"] = True
        return {"rejections": probes, "pass": all(probes.values()), "service": SERVICE}
    raise ValueError("CERTIFICATION_PROBE_NOT_ALLOWED")


def invoke(capability: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    if capability not in CAPABILITIES:
        raise ValueError("CERT_CAPABILITY_NOT_ALLOWED")
    args = dict(arguments or {})
    controller = _controller()
    if capability == "nova.lifecycle.cert.status":
        if args:
            raise ValueError("CERT_ARGUMENT_SCHEMA_INVALID")
        result = controller.status()
        result["active_cert_release"] = _alias_from_internal(
            result.get("active_configuration", {}).get("release")) if result.get("active_configuration", {}).get("release") else ""
        return result
    if capability == "nova.lifecycle.cert.stage":
        if set(args) != {"candidate_release"}:
            raise ValueError("CERT_ARGUMENT_SCHEMA_INVALID")
        return _stage(controller, args["candidate_release"])
    if capability == "nova.lifecycle.cert.validate":
        if set(args) - {"candidate_release", "expected_hash"} or "candidate_release" not in args:
            raise ValueError("CERT_ARGUMENT_SCHEMA_INVALID")
        return controller.validate(candidate_release=_release(args["candidate_release"]),
                                   expected_manifest_hash=args.get("expected_hash", ""))
    if capability == "nova.lifecycle.cert.verify":
        if set(args) - {"expected_release", "expected_hash"} or "expected_release" not in args:
            raise ValueError("CERT_ARGUMENT_SCHEMA_INVALID")
        result = controller.verify(expected_release=_release(args["expected_release"]),
                                   expected_hash=args.get("expected_hash"))
        result["active_cert_release"] = next((alias for alias, release in ALIAS_TO_RELEASE.items()
                                                if result.get("code_root", "").endswith("/" + release)), "")
        return result
    if capability == "nova.lifecycle.cert.activate":
        required = {"deployment_id", "candidate_release", "candidate_hash", "current_release"}
        if set(args) - required - {"approval_id"} or not required.issubset(args):
            raise ValueError("CERT_ARGUMENT_SCHEMA_INVALID")
        if not args.get("approval_id"):
            return {"status": "BLOCKED", "reason": "CERT_APPROVAL_REQUIRED", "mutations": 0}
        candidate = _release(args["candidate_release"])
        current = _release(args["current_release"])
        return controller.activate(deployment_id=args["deployment_id"], candidate_release=candidate,
            candidate_hash=args["candidate_hash"], previous_release=current,
            dropin_name=DROPIN_NAME, approval_id=args["approval_id"])
    if capability == "nova.lifecycle.cert.rollback":
        required = {"deployment_id", "target_release", "target_hash", "current_release", "source_deployment_id"}
        if set(args) - required - {"approval_id"} or not required.issubset(args):
            raise ValueError("CERT_ARGUMENT_SCHEMA_INVALID")
        if not args.get("approval_id"):
            return {"status": "BLOCKED", "reason": "CERT_APPROVAL_REQUIRED", "mutations": 0}
        return controller.rollback(deployment_id=args["deployment_id"],
            target_release=_release(args["target_release"]), target_hash=args["target_hash"],
            current_release=_release(args["current_release"]), approval_id=args["approval_id"],
            source_deployment_id=args["source_deployment_id"])
    if capability == "nova.lifecycle.cert.receipt":
        if set(args) != {"deployment_id"} or not re.fullmatch(r"(?:deploy_[a-f0-9]{32}|stage_[a-f0-9]{32})", str(args["deployment_id"])):
            raise ValueError("CERT_ARGUMENT_SCHEMA_INVALID")
        return controller.receipt(deployment_id=args["deployment_id"])
    raise ValueError("CERT_CAPABILITY_NOT_ALLOWED")


def _main() -> int:
    _validate_adapter_package()
    request = json.loads(sys.stdin.read() or "{}")
    if not isinstance(request, dict):
        raise SystemExit("CERT_REQUEST_SCHEMA_INVALID")
    try:
        if request == {"bootstrap": True}:
            result = provision()
        elif set(request) == {"certification_probe"} and request["certification_probe"] in {
                "tamper-candidate", "mixed-release", "security"}:
            result = certification_probe(request["certification_probe"])
        elif set(request) == {"approval_operation", "arguments"}:
            arguments = request["arguments"]
            if not isinstance(arguments, dict):
                raise SystemExit("CERT_REQUEST_SCHEMA_INVALID")
            result = {"approval_id": issue_test_approval(request["approval_operation"], **arguments),
                      "certification_target": SERVICE}
        elif set(request) == {"capability", "arguments"}:
            result = invoke(request["capability"], request["arguments"])
        else:
            raise SystemExit("CERT_REQUEST_SCHEMA_INVALID")
    except (ValueError, PermissionError) as exc:
        result = {"status": "REJECTED", "reason": str(exc), "mutations": 0,
                  "service": SERVICE}
    print(json.dumps(result, sort_keys=True))
    return 0


def _validate_adapter_package() -> None:
    manifest = OPERATOR_ROOT / "RELEASE_MANIFEST.sha256"
    if not manifest.is_file() or manifest.is_symlink() or manifest.stat().st_mode & 0o222:
        raise RuntimeError("CERT_ADAPTER_MANIFEST_UNAVAILABLE")
    listed: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([a-f0-9]{64})  ([A-Za-z0-9_./-]{1,300})", line)
        if not match:
            raise RuntimeError("CERT_ADAPTER_MANIFEST_INVALID")
        digest, name = match.groups()
        if name in listed or Path(name).name != name or name.startswith("."):
            raise RuntimeError("CERT_ADAPTER_MANIFEST_PATH_INVALID")
        listed[name] = digest
    expected = {"release_lifecycle.py", "lifecycle_fixture_worker.py",
                "oracle_lifecycle_cert_adapter.py", "oracle_lifecycle_cert_transport.py"}
    if set(listed) != expected:
        raise RuntimeError("CERT_ADAPTER_MANIFEST_FILE_SET_INVALID")
    for name, digest in listed.items():
        path = OPERATOR_ROOT / name
        if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o222:
            raise RuntimeError("CERT_ADAPTER_PACKAGE_FILE_INVALID")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise RuntimeError("CERT_ADAPTER_PACKAGE_HASH_MISMATCH")


if __name__ == "__main__":
    raise SystemExit(_main())
