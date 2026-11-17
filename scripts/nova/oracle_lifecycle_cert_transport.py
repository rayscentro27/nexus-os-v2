"""Fixed-host, certification-only SSH/SFTP transport for typed lifecycle calls.

The read-only Oracle resolver is not imported or modified. All remote writes
are confined to the immutable adapter directory under the Nova lifecycle
certification root; all service operations happen inside that adapter.
"""
from __future__ import annotations

import json
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[2]
AUTHORITY_PATH = REPO_ROOT / "docs/architecture/NEXUS_ORACLE_CONNECTION_AUTHORITY.json"
RELEASE_NAME = "nexus-nova-oracle-lifecycle-cert-r8-20261029"
REMOTE_RELEASE_ROOT = f"/home/opc/.nexus/certification/nova-lifecycle/operator/{RELEASE_NAME}"
REMOTE_ADAPTER = REMOTE_RELEASE_ROOT + "/oracle_lifecycle_cert_adapter.py"
REMOTE_ROOT = "/home/opc/.nexus/certification/nova-lifecycle"
SERVICE = "nova-release-lifecycle-cert.service"
ALLOWED = {
    "nova.lifecycle.cert.status", "nova.lifecycle.cert.stage",
    "nova.lifecycle.cert.validate", "nova.lifecycle.cert.activate",
    "nova.lifecycle.cert.verify", "nova.lifecycle.cert.rollback",
    "nova.lifecycle.cert.receipt",
}
CERT_RELEASE_ALIASES = {"cert-release-a", "cert-release-b", "cert-release-bad", "cert-release-tampered"}
CAPABILITY_SCHEMAS: dict[str, tuple[set[str], set[str]]] = {
    "nova.lifecycle.cert.status": (set(), set()),
    "nova.lifecycle.cert.stage": ({"candidate_release"}, set()),
    "nova.lifecycle.cert.validate": ({"candidate_release"}, {"expected_hash"}),
    "nova.lifecycle.cert.activate": ({"deployment_id", "candidate_release", "candidate_hash", "current_release"}, {"approval_id"}),
    "nova.lifecycle.cert.verify": ({"expected_release"}, {"expected_hash"}),
    "nova.lifecycle.cert.rollback": ({"deployment_id", "target_release", "target_hash", "current_release", "source_deployment_id"}, {"approval_id"}),
    "nova.lifecycle.cert.receipt": ({"deployment_id"}, set()),
}
CAPABILITY_FILES = (
    "release_lifecycle.py", "lifecycle_fixture_worker.py",
    "oracle_lifecycle_cert_adapter.py", "oracle_lifecycle_cert_transport.py",
    "RELEASE_MANIFEST.sha256",
)


def _connection() -> tuple[str, str, Path]:
    payload = json.loads(AUTHORITY_PATH.read_text(encoding="utf-8"))
    current = payload.get("current") or {}
    if payload.get("current_connection_count") != 1 or current.get("status") != "VERIFIED":
        raise RuntimeError("ORACLE_CURRENT_AUTHORITY_NOT_VERIFIED")
    host, user = current.get("host"), current.get("user")
    if host != "161.153.40.41" or user != "opc":
        raise RuntimeError("ORACLE_CURRENT_TARGET_MISMATCH")
    identity_value = current.get("identity_path")
    if identity_value != "~/.ssh/oracle_vm":
        raise RuntimeError("ORACLE_CURRENT_IDENTITY_MISMATCH")
    identity = Path(identity_value).expanduser()
    if not identity.is_file():
        raise RuntimeError("ORACLE_CURRENT_IDENTITY_UNAVAILABLE")
    return user, host, identity


def _check_authority(runner: Callable[..., Any] = subprocess.run) -> None:
    result = runner(["python3", str(REPO_ROOT / "scripts/nexus_oracle_connection.py"), "--check"],
                    cwd=REPO_ROOT, capture_output=True, text=True, timeout=30, check=False)
    if result.returncode or "RESOLVER_CHECK=PASS" not in (result.stdout or ""):
        raise RuntimeError("ORACLE_CURRENT_CHECK_FAILED")


def _remote_process(*, request: dict[str, Any], runner: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    _check_authority(runner)
    user, host, identity = _connection()
    remote_command = f"/usr/bin/python3 {shlex.quote(REMOTE_ADAPTER)}"
    command = ["ssh", "-T", "-oBatchMode=yes", "-oIdentitiesOnly=yes",
               "-oStrictHostKeyChecking=yes", "-i", str(identity), f"{user}@{host}", remote_command]
    result = runner(command, cwd=REPO_ROOT, input=json.dumps(request, sort_keys=True),
                    capture_output=True, text=True, timeout=900, check=False)
    if result.returncode:
        raise RuntimeError("ORACLE_CERT_INVOCATION_FAILED:" + str(result.returncode))
    lines = [line for line in (result.stdout or "").splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("ORACLE_CERT_RESPONSE_EMPTY")
    payload = json.loads(lines[-1])
    if not isinstance(payload, dict):
        raise RuntimeError("ORACLE_CERT_RESPONSE_INVALID")
    return payload


def install_adapter(package_root: Path, *, runner: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    """SFTP only the five fixed package files to the one certification path."""
    package = Path(package_root).resolve()
    if package.name != RELEASE_NAME or package.is_symlink():
        raise ValueError("CERT_ADAPTER_PACKAGE_PATH_INVALID")
    if any(not (package / name).is_file() or (package / name).is_symlink() for name in CAPABILITY_FILES):
        raise ValueError("CERT_ADAPTER_PACKAGE_INCOMPLETE")
    manifest = (package / "RELEASE_MANIFEST.sha256").read_text(encoding="utf-8").splitlines()
    expected = {line.split("  ", 1)[1] for line in manifest if "  " in line}
    if expected != set(CAPABILITY_FILES) - {"RELEASE_MANIFEST.sha256"}:
        raise ValueError("CERT_ADAPTER_MANIFEST_FILE_SET_INVALID")
    _check_authority(runner)
    user, host, identity = _connection()
    batch = ["-mkdir /home/opc/.nexus", "-mkdir /home/opc/.nexus/certification",
             f"-mkdir {REMOTE_ROOT}", f"-mkdir {REMOTE_ROOT}/operator",
             f"mkdir {REMOTE_RELEASE_ROOT}"]
    for name in CAPABILITY_FILES:
        batch.append(f"put {shlex.quote(str(package / name))} {REMOTE_RELEASE_ROOT}/{name}")
    for name in CAPABILITY_FILES:
        batch.append(f"chmod 0444 {REMOTE_RELEASE_ROOT}/{name}")
    batch.append(f"chmod 0555 {REMOTE_RELEASE_ROOT}")
    command = ["sftp", "-b", "-", "-oBatchMode=yes", "-oIdentitiesOnly=yes",
               "-oStrictHostKeyChecking=yes", "-i", str(identity), f"{user}@{host}"]
    result = runner(command, cwd=REPO_ROOT, input="\n".join(batch) + "\n",
                    capture_output=True, text=True, timeout=120, check=False)
    if result.returncode:
        raise RuntimeError("CERT_ADAPTER_SFTP_INSTALL_FAILED:" + str(result.returncode))
    return {"status": "INSTALLED", "remote_release": REMOTE_RELEASE_ROOT,
            "files": list(CAPABILITY_FILES), "service": SERVICE}


def provision_certification_target(*, runner: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    """Create only the fixed inert certification service; production is not addressable."""
    return _remote_process(request={"bootstrap": True}, runner=runner)


def invoke(capability: str, arguments: dict[str, Any] | None = None,
           *, runner: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    if capability not in ALLOWED:
        raise ValueError("CERT_CAPABILITY_NOT_ALLOWED")
    args = dict(arguments or {})
    required, optional = CAPABILITY_SCHEMAS[capability]
    if set(args) - required - optional or not required.issubset(args):
        raise ValueError("CERT_ARGUMENT_SCHEMA_INVALID")
    for key, value in args.items():
        if key in {"candidate_release", "current_release", "target_release", "expected_release"}:
            if value not in CERT_RELEASE_ALIASES:
                raise ValueError("CERT_RELEASE_NOT_ALLOWED")
        if key in {"deployment_id", "source_deployment_id"} and not re.fullmatch(
                r"(?:deploy_[a-f0-9]{32}|stage_[a-f0-9]{32})" if capability == "nova.lifecycle.cert.receipt" and key == "deployment_id" else r"deploy_[a-f0-9]{32}", str(value)):
            raise ValueError("CERT_DEPLOYMENT_ID_INVALID")
        if key in {"candidate_hash", "target_hash", "expected_hash"} and not re.fullmatch(r"[a-f0-9]{64}", str(value)):
            raise ValueError("CERT_HASH_INVALID")
        if key == "approval_id" and not re.fullmatch(r"cert_appr_[a-f0-9]{32}", str(value)):
            raise ValueError("CERT_APPROVAL_ID_INVALID")
    return _remote_process(request={"capability": capability, "arguments": args}, runner=runner)


def issue_test_approval(operation: str, arguments: dict[str, Any], *,
                        runner: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    if operation not in {"ACTIVATE", "ROLLBACK"}:
        raise ValueError("CERT_APPROVAL_OPERATION_NOT_ALLOWED")
    required = {"deployment_id", "candidate_release", "candidate_hash", "current_release"}
    if operation == "ROLLBACK":
        required.add("source_deployment_id")
    if set(arguments) != required:
        raise ValueError("CERT_APPROVAL_ARGUMENT_SCHEMA_INVALID")
    for key in ("candidate_release", "current_release"):
        if arguments[key] not in CERT_RELEASE_ALIASES:
            raise ValueError("CERT_RELEASE_NOT_ALLOWED")
    if not re.fullmatch(r"deploy_[a-f0-9]{32}", str(arguments["deployment_id"])):
        raise ValueError("CERT_DEPLOYMENT_ID_INVALID")
    if not re.fullmatch(r"[a-f0-9]{64}", str(arguments["candidate_hash"])):
        raise ValueError("CERT_HASH_INVALID")
    request = {"approval_operation": operation, "arguments": arguments}
    return _remote_process(request=request, runner=runner)


def run_certification_probe(name: str, *, runner: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    if name not in {"tamper-candidate", "mixed-release", "security"}:
        raise ValueError("CERTIFICATION_PROBE_NOT_ALLOWED")
    return _remote_process(request={"certification_probe": name}, runner=runner)


def cert_status(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    return invoke("nova.lifecycle.cert.status", arguments)


def cert_stage(arguments: dict[str, Any]) -> dict[str, Any]:
    return invoke("nova.lifecycle.cert.stage", arguments)


def cert_validate(arguments: dict[str, Any]) -> dict[str, Any]:
    return invoke("nova.lifecycle.cert.validate", arguments)


def cert_activate(arguments: dict[str, Any]) -> dict[str, Any]:
    return invoke("nova.lifecycle.cert.activate", arguments)


def cert_verify(arguments: dict[str, Any]) -> dict[str, Any]:
    return invoke("nova.lifecycle.cert.verify", arguments)


def cert_rollback(arguments: dict[str, Any]) -> dict[str, Any]:
    return invoke("nova.lifecycle.cert.rollback", arguments)


def cert_receipt(arguments: dict[str, Any]) -> dict[str, Any]:
    return invoke("nova.lifecycle.cert.receipt", arguments)
