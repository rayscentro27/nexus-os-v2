"""Approval-gated, Nova-only immutable release lifecycle controller.

This module has no general command or path interface. Production paths and
service identity are fixed by ``NovaReleasePolicy``; tests inject temporary
roots and a fake host. Importing the module never mutates the runtime.
"""
from __future__ import annotations

import hashlib
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol


SERVICE = "nova-telegram-oracle.service"
CERT_SERVICE = "nova-release-lifecycle-cert.service"
SERVICES = {"production": SERVICE, "certification": CERT_SERVICE}
ACTIVATE_ACTION = "nova.release.activate"
ROLLBACK_ACTION = "nova.release.rollback"
RELEASE_RE = re.compile(r"nova-operator-v1-[0-9]{8}-r[0-9]+-[a-z0-9-]{3,64}\Z")
DEPLOYMENT_RE = re.compile(r"deploy_[a-f0-9]{32}\Z")
STAGE_RE = re.compile(r"stage_[a-f0-9]{32}\Z")
MAX_BUNDLE_FILES = 12000
MAX_BUNDLE_BYTES = 256 * 1024 * 1024
REQUIRED_FILES = (
    "scripts/nova/nova_telegram_worker.py",
    "scripts/nova/release_lifecycle.py",
    "scripts/nova/acceptance_telemetry.py",
    "scripts/nova/langfuse_runtime.py",
    "scripts/nova/semantic_orchestration.py",
    "scripts/nova/operator_v1.py",
    "scripts/nova/context_authority.py",
    "scripts/nova/approved_mcp_registry.py",
    "scripts/nova/nexus_mcp_status.py",
    "scripts/nova/proactive_communications.py",
    "scripts/nova/tests/test_r10_completion_events.py",
    "scripts/nova/tests/test_proactive_poll_loop.py",
    "scripts/nova/tests/test_nexus_mcp_status.py",
    "scripts/nexus_agent_platform/governed/approvals.py",
    "scripts/nexus_agent_platform/governed/action_registry.py",
    "scripts/nexus_agent_platform/governed/persistence.py",
)
CERT_REQUIRED_FILES = ("scripts/nova/lifecycle_fixture_worker.py",)
FORBIDDEN_MUTABLE_PATH_PARTS = {"data", "reports", "__pycache__"}


@dataclass(frozen=True)
class NovaReleasePolicy:
    release_root: Path | None = None
    staging_root: Path | None = None
    dropin_root: Path | None = None
    receipt_root: Path | None = None
    runtime_state_root: Path | None = None
    service: str | None = None
    mode: str = "production"
    source_root: Path | None = None
    test_paths: tuple[str, ...] = (
        "scripts/nova/tests/test_r10_completion_events.py",
        "scripts/nova/tests/test_proactive_poll_loop.py",
        "scripts/nova/tests/test_nexus_mcp_status.py",
    )

    def __post_init__(self) -> None:
        if self.mode not in SERVICES:
            raise ValueError("NOVA_RELEASE_MODE_NOT_ALLOWED")
        expected_service = SERVICES[self.mode]
        if self.service not in {None, expected_service}:
            raise ValueError("NOVA_SERVICE_IS_FIXED")
        defaults = ({"release_root": "/home/opc/.nexus/releases", "staging_root": "/home/opc/.nexus/staging/nova",
            "dropin_root": "/home/opc/.config/systemd/user/nova-telegram-oracle.service.d",
            "receipt_root": "/home/opc/.nexus/state/nova/deployments",
            "runtime_state_root": "/home/opc/nexus-os-v2-source/data/runtime"} if self.mode == "production" else {
            "release_root": "/home/opc/.nexus/certification/nova-lifecycle/releases",
            "staging_root": "/home/opc/.nexus/certification/nova-lifecycle/staging",
            "dropin_root": "/home/opc/.config/systemd/user/nova-release-lifecycle-cert.service.d",
            "receipt_root": "/home/opc/.nexus/certification/nova-lifecycle/receipts",
            "runtime_state_root": "/home/opc/.nexus/certification/nova-lifecycle/runtime"})
        for field, default in defaults.items():
            value = getattr(self, field)
            object.__setattr__(self, field, Path(value or default).resolve())
        object.__setattr__(self, "service", expected_service)
        source_default = (self.runtime_state_root.parents[1] if self.source_root is None
                          else Path(self.source_root))
        object.__setattr__(self, "source_root", Path(source_default).resolve())

    @property
    def required_files(self) -> tuple[str, ...]:
        return REQUIRED_FILES if self.mode == "production" else CERT_REQUIRED_FILES


class Host(Protocol):
    def systemctl(self, action: str) -> str: ...
    def pollers(self) -> list[dict[str, Any]]: ...


class FixedNovaHost:
    """Only the three contract-listed user systemd actions are callable."""
    def __init__(self, service: str = SERVICE, mode: str = "production",
                 runner: Callable[..., Any] = subprocess.run):
        if mode not in SERVICES or service != SERVICES[mode]:
            raise ValueError("NOVA_SERVICE_IS_FIXED")
        self.service = service
        self.mode = mode
        self._runner = runner

    def systemctl(self, action: str) -> str:
        if action not in {"daemon-reload", "restart", "status", "show"}:
            raise ValueError("NOVA_SYSTEMD_ACTION_NOT_ALLOWED")
        argv = ["systemctl", "--user", action]
        if action != "daemon-reload":
            argv.append(self.service)
        result = self._runner(argv, capture_output=True, text=True, timeout=30, check=False)
        if result.returncode and action != "status":
            raise RuntimeError(f"NOVA_SYSTEMD_{action.upper()}_FAILED")
        return (result.stdout or "") + (result.stderr or "")

    def pollers(self) -> list[dict[str, Any]]:
        rows = []
        proc = Path("/proc")
        for entry in proc.iterdir():
            if not entry.name.isdigit():
                continue
            try:
                argv = [part.decode(errors="replace") for part in (entry / "cmdline").read_bytes().split(b"\0") if part]
                worker = "nova_telegram_worker.py" if self.mode == "production" else "lifecycle_fixture_worker.py"
                argument = "--poll" if self.mode == "production" else "--hold"
                command = " ".join(argv)
                if worker not in command or argument not in argv:
                    continue
                if self.mode == "certification" and "/.nexus/certification/nova-lifecycle/releases/" not in command:
                    continue
                env: dict[str, str] = {}
                for part in (entry / "environ").read_bytes().split(b"\0"):
                    if b"=" not in part:
                        continue
                    key, value = part.split(b"=", 1)
                    if key in {b"NOVA_CODE_ROOT", b"PYTHONPATH", b"NOVA_CERT_RELEASE_ID"}:
                        env[key.decode()] = value.decode(errors="replace")[:2048]
                stat = (entry / "stat").read_text().rpartition(")")[2].split()
                rows.append({"pid": int(entry.name), "argv": argv, "code_root": env.get("NOVA_CODE_ROOT", ""),
                             "pythonpath": env.get("PYTHONPATH", ""), "cert_release_id": env.get("NOVA_CERT_RELEASE_ID", ""),
                             "start_ticks": int(stat[19])})
            except (OSError, ValueError, IndexError):
                continue
        return rows


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (ValueError, OSError):
        return False


def _release_id(value: str) -> str:
    if not RELEASE_RE.fullmatch(str(value)):
        raise ValueError("INVALID_NOVA_RELEASE_ID")
    return str(value)


def _deployment_id(value: str) -> str:
    if not DEPLOYMENT_RE.fullmatch(str(value)):
        raise ValueError("INVALID_DEPLOYMENT_ID")
    return str(value)


def create_manifest(root: Path) -> tuple[str, int]:
    """Create a sorted SHA256 manifest. Caller must pass a fresh staged tree."""
    rows: list[str] = []
    total = 0
    entries = list(root.rglob("*"))
    if any(path.is_symlink() for path in entries):
        raise ValueError("NOVA_RELEASE_SYMLINK_OR_PATH_ESCAPE")
    files = sorted(path for path in entries if path.is_file() and path.name != "RELEASE_MANIFEST.sha256")
    if len(files) > MAX_BUNDLE_FILES:
        raise ValueError("NOVA_RELEASE_FILE_LIMIT_EXCEEDED")
    for path in files:
        if path.is_symlink() or not _under(path, root):
            raise ValueError("NOVA_RELEASE_SYMLINK_OR_PATH_ESCAPE")
        size = path.stat().st_size
        total += size
        if total > MAX_BUNDLE_BYTES:
            raise ValueError("NOVA_RELEASE_SIZE_LIMIT_EXCEEDED")
        relative = path.relative_to(root).as_posix()
        if relative.startswith("/") or ".." in Path(relative).parts:
            raise ValueError("NOVA_RELEASE_PATH_INVALID")
        parts = Path(relative).parts
        if (parts and parts[0] in FORBIDDEN_MUTABLE_PATH_PARTS) or "__pycache__" in parts or Path(relative).name.startswith(".env"):
            raise ValueError("MUTABLE_OR_SECRET_STATE_IN_RELEASE")
        rows.append(f"{_sha256(path)}  {relative}")
    manifest = root / "RELEASE_MANIFEST.sha256"
    manifest.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return _sha256(manifest), len(rows)


def validate_release(root: Path, *, expected_manifest_hash: str | None = None,
                     required_files: tuple[str, ...] = REQUIRED_FILES) -> dict[str, Any]:
    """Verify exact file set, hashes, and required worker modules."""
    root_input = Path(root)
    if root_input.is_symlink():
        return {"valid": False, "reason": "RELEASE_ROOT_SYMLINK", "manifest_hash": "", "mismatches": ["release_root_symlink"]}
    root = root_input.resolve()
    manifest = root / "RELEASE_MANIFEST.sha256"
    if not root.is_dir() or not manifest.is_file() or manifest.is_symlink():
        return {"valid": False, "reason": "RELEASE_OR_MANIFEST_MISSING", "manifest_hash": "", "mismatches": ["manifest"]}
    manifest_hash = _sha256(manifest)
    if manifest.stat().st_mode & 0o222:
        return {"valid": False, "reason": "WRITABLE_MANIFEST", "manifest_hash": manifest_hash,
                "manifest_entries": 0, "mismatches": ["writable_manifest"]}
    if expected_manifest_hash and not re.fullmatch(r"[a-f0-9]{64}", expected_manifest_hash):
        return {"valid": False, "reason": "EXPECTED_HASH_INVALID", "manifest_hash": manifest_hash, "mismatches": ["expected_hash"]}
    mismatches: list[str] = []
    listed: set[str] = set()
    try:
        lines = manifest.read_text(encoding="utf-8").splitlines()
        if len(lines) > MAX_BUNDLE_FILES:
            raise ValueError("manifest too large")
        for line in lines:
            match = re.fullmatch(r"([a-f0-9]{64})  ([A-Za-z0-9_./-]{1,300})", line)
            if not match:
                mismatches.append("malformed_manifest_line")
                continue
            digest, relative = match.groups()
            rel = Path(relative)
            if rel.is_absolute() or ".." in rel.parts or relative in listed:
                mismatches.append(relative)
                continue
            listed.add(relative)
            if ((rel.parts and rel.parts[0] in FORBIDDEN_MUTABLE_PATH_PARTS) or
                    "__pycache__" in rel.parts or rel.name.startswith(".env")):
                mismatches.append("mutable_or_secret_state:" + relative)
                continue
            target = root / rel
            if target.is_symlink() or not _under(target, root) or not target.is_file() or target.stat().st_mode & 0o222 or _sha256(target) != digest:
                mismatches.append(relative)
    except (OSError, ValueError):
        mismatches.append("manifest_unreadable")
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p != manifest}
    mismatches.extend(sorted(actual - listed))
    mismatches.extend(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_symlink())
    if root.stat().st_mode & 0o222:
        mismatches.append("release_root_writable")
    for directory in (p for p in root.rglob("*") if p.is_dir()):
        if directory.stat().st_mode & 0o222:
            mismatches.append("writable_directory:" + directory.relative_to(root).as_posix())
    for required in required_files:
        if not (root / required).is_file():
            mismatches.append(required)
    if expected_manifest_hash and manifest_hash != expected_manifest_hash:
        mismatches.append("manifest_hash")
    mismatches = list(dict.fromkeys(mismatches))
    return {"valid": not mismatches, "reason": "OK" if not mismatches else "MANIFEST_MISMATCH",
            "manifest_hash": manifest_hash, "manifest_entries": len(listed), "mismatches": mismatches}


class NovaReleaseController:
    """Typed Nova release operations. Only activate/rollback can change service state."""
    def __init__(self, policy: NovaReleasePolicy = NovaReleasePolicy(), host: Host | None = None,
                 approval_store: Any = None, test_runner: Callable[..., dict[str, Any]] | None = None,
                 provenance_provider: Callable[[Path, str], dict[str, Any]] | None = None):
        self.policy = policy
        self.host = host or FixedNovaHost(policy.service, policy.mode)
        self.approval_store = approval_store
        self.test_runner = test_runner or self._run_candidate_tests
        self.provenance_provider = provenance_provider or self._source_provenance

    def _validate_release(self, root: Path, expected_manifest_hash: str | None = None) -> dict[str, Any]:
        return validate_release(root, expected_manifest_hash=expected_manifest_hash,
                                required_files=self.policy.required_files)

    def status(self) -> dict[str, Any]:
        status_text = self.host.systemctl("status")
        show_text = self.host.systemctl("show")
        pollers = self.host.pollers()
        config = self.inspect_effective_config()
        release = config.get("release", "")
        validation = self._validate_release(self.policy.release_root / release) if release and RELEASE_RE.fullmatch(release) else {
            "valid": False, "manifest_hash": "", "mismatches": ["release_identity_unavailable"]}
        return {"service": self.policy.service, "service_status": status_text[-4000:], "poller_count": len(pollers),
                "service_show": show_text[-4000:],
                "pollers": pollers, "active_configuration": config,
                "active_release_hash": validation.get("manifest_hash"),
                "release_manifest_valid": validation.get("valid"), "read_only": True}

    def receipt(self, *, deployment_id: str) -> dict[str, Any]:
        deployment = str(deployment_id)
        if not (DEPLOYMENT_RE.fullmatch(deployment) or STAGE_RE.fullmatch(deployment)):
            raise ValueError("INVALID_DEPLOYMENT_ID")
        path = self.policy.receipt_root / (deployment + ".json")
        if not path.is_file() or path.is_symlink() or not _under(path, self.policy.receipt_root):
            return {"status": "NOT_FOUND", "deployment_id": deployment, "read_only": True}
        if path.stat().st_size > 1024 * 1024:
            raise ValueError("NOVA_DEPLOYMENT_RECEIPT_TOO_LARGE")
        return {"status": "FOUND", "receipt": json.loads(path.read_text(encoding="utf-8")), "read_only": True}

    def stage(self, *, candidate_release: str, bundle_id: str) -> dict[str, Any]:
        release = _release_id(candidate_release)
        bundle = _release_id(bundle_id)
        source = (self.policy.staging_root / bundle)
        destination = self.policy.release_root / release
        if source.is_symlink() or not _under(source, self.policy.staging_root) or not source.is_dir():
            raise ValueError("NOVA_BUNDLE_NOT_FOUND_IN_STAGING_ROOT")
        if destination.exists():
            raise FileExistsError("IMMUTABLE_NOVA_RELEASE_ALREADY_EXISTS")
        for path in source.rglob("*"):
            if path.is_symlink() or not _under(path, source):
                raise ValueError("NOVA_BUNDLE_SYMLINK_OR_PATH_ESCAPE")
        self.policy.release_root.mkdir(parents=True, exist_ok=True)
        # Copy into a private temp sibling, validate, then atomically publish.
        temporary = self.policy.release_root / f".{release}.{uuid.uuid4().hex}.staging"
        try:
            shutil.copytree(source, temporary, symlinks=False)
            for path in temporary.rglob("*"):
                if path.is_symlink() or not _under(path, temporary):
                    raise ValueError("NOVA_BUNDLE_SYMLINK_OR_PATH_ESCAPE")
            if (temporary / "RELEASE_MANIFEST.sha256").is_file():
                manifest_hash = _sha256(temporary / "RELEASE_MANIFEST.sha256")
            else:
                manifest_hash, _ = create_manifest(temporary)
            for path in sorted(temporary.rglob("*"), reverse=True):
                path.chmod(0o555 if path.is_dir() else 0o444)
            temporary.chmod(0o555)
            validation = self._validate_release(temporary, expected_manifest_hash=manifest_hash)
            if not validation["valid"]:
                raise ValueError("STAGED_NOVA_RELEASE_INVALID")
            temporary.chmod(0o755)
            os.replace(temporary, destination)
            destination.chmod(0o555)
        except Exception:
            if temporary.exists():
                try: temporary.chmod(0o700)
                except OSError: pass
                for path in sorted(temporary.rglob("*"), reverse=True):
                    try: path.chmod(0o700 if path.is_dir() else 0o600)
                    except OSError: pass
                shutil.rmtree(temporary, ignore_errors=True)
            raise
        receipt = {"deployment_id": "stage_" + uuid.uuid4().hex, "operation": "STAGE",
                   "requested_by": "nova_release_controller",
                   "approval_id": None, "candidate_release": release, "candidate_hash": manifest_hash,
                   "previous_release": None, "previous_hash": None, "dropin_changed": False,
                   "service_restarted": False, "process_pid_before": None, "process_pid_after": None,
                   "start_time_after": None, "poller_count": None, "verification_result": "STAGED",
                   "rollback_performed": False, "mutations": 1, "mutation_list": ["immutable_release_stage"],
                   "started_at": _now(), "completed_at": _now()}
        receipt["provenance_attestation"] = self.provenance_provider(self.policy.source_root, manifest_hash)
        self._write_receipt(receipt)
        return {"release": str(destination), "manifest_hash": manifest_hash, "validation": validation,
                "immutable": True, "service_mutation": False, "receipt": receipt}

    def validate(self, *, candidate_release: str, expected_manifest_hash: str = "") -> dict[str, Any]:
        release = _release_id(candidate_release)
        path = self.policy.release_root / release
        result = self._validate_release(path, expected_manifest_hash=expected_manifest_hash or None)
        staged = self._stage_receipt(release, result.get("manifest_hash", "")) if result["valid"] else None
        if not staged:
            return {**result, "release": str(path), "read_only": True,
                    "test_attestation": {"test_result": "NOT_RUN", "reason": "CANDIDATE_NOT_STAGED"}}
        test_attestation = self.test_runner(path, self.policy.test_paths)
        test_attestation["tested_manifest_hash"] = result["manifest_hash"]
        test_attestation["test_timestamp"] = _now()
        test_attestation["source_build_input_hash"] = staged["provenance_attestation"].get("build_input_hash", "")
        staged["test_attestation"] = test_attestation
        staged["validation"] = {"manifest_hash": result["manifest_hash"], "manifest_entries": result["manifest_entries"],
                                "valid": result["valid"], "validated_at": _now()}
        self._write_receipt(staged)
        return {**result, "release": str(path),
                "provenance_attestation": staged["provenance_attestation"],
                "test_attestation": test_attestation,
                "read_only": False, "service_mutation": False, "attestation_written": True}

    def _run_candidate_tests(self, candidate: Path, test_paths: tuple[str, ...]) -> dict[str, Any]:
        """Run the fixed focused Nova contracts from the exact immutable candidate."""
        commands = [[sys.executable, "-m", "pytest", "-q", *test_paths]]
        missing = [name for name in test_paths if not (candidate / name).is_file()]
        if missing:
            return {"test_commands": commands, "test_result": "FAIL", "test_count": 0,
                    "failure_code": "MISSING_CANDIDATE_TESTS", "missing_test_paths": missing}
        try:
            with tempfile.TemporaryDirectory(prefix="nova-release-tests-") as isolated_home:
                env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": isolated_home,
                       "TMPDIR": isolated_home, "PYTHONDONTWRITEBYTECODE": "1",
                       "PYTEST_ADDOPTS": "-p no:cacheprovider", "PYTHONPATH": str(candidate / "scripts")}
                completed = subprocess.run(commands[0], cwd=candidate, env=env,
                                           capture_output=True, text=True, timeout=300, check=False)
        except (OSError, subprocess.SubprocessError) as exc:
            return {"test_commands": commands, "test_result": "FAIL", "test_count": 0,
                    "failure_code": type(exc).__name__}
        output = ((completed.stdout or "") + "\n" + (completed.stderr or ""))[-12000:]
        match = re.search(r"(?:^|\s)(\d+) passed(?:\s|$)", output)
        count = int(match.group(1)) if match else 0
        passed = completed.returncode == 0 and count > 0 and " failed" not in output
        return {"test_commands": commands, "test_result": "PASS" if passed else "FAIL",
                "test_count": count, "return_code": completed.returncode,
                "failure_code": None if passed else "CANDIDATE_TESTS_FAILED"}

    def _source_provenance(self, source_root: Path, manifest_hash: str) -> dict[str, Any]:
        root = Path(source_root).resolve()
        try:
            revision = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True,
                                      text=True, timeout=10, check=True).stdout.strip()
            origin = subprocess.run(["git", "-C", str(root), "remote", "get-url", "origin"],
                                    capture_output=True, text=True, timeout=10, check=True).stdout.strip()
            diff = subprocess.run(["git", "-C", str(root), "diff", "--binary", "HEAD", "--"],
                                  capture_output=True, timeout=20, check=True).stdout
            untracked = subprocess.run(["git", "-C", str(root), "ls-files", "--others", "--exclude-standard", "-z"],
                                       capture_output=True, timeout=10, check=True).stdout
            untracked_digest = hashlib.sha256()
            for raw_path in sorted(x for x in untracked.split(b"\0") if x):
                rel = Path(os.fsdecode(raw_path))
                target = root / rel
                if target.is_file() and not target.is_symlink() and _under(target, root):
                    untracked_digest.update(raw_path + b"\0" + target.read_bytes())
            state_payload = diff + b"\0UNTRACKED\0" + untracked_digest.hexdigest().encode()
            state_hash = hashlib.sha256(state_payload).hexdigest()
            dirty = bool(diff or untracked)
            trusted = (origin.rstrip("/").removesuffix(".git").lower() ==
                       "https://github.com/rayscentro27/nexus-os-v2" and bool(re.fullmatch(r"[a-f0-9]{40,64}", revision)))
        except (OSError, subprocess.SubprocessError, ValueError):
            revision, state_hash, dirty, trusted = "UNAVAILABLE", "", True, False
        build_input = {"source_root": str(root), "source_revision": revision,
                       "source_tree_state": "DIRTY" if dirty else "CLEAN", "source_state_hash": state_hash,
                       "manifest_hash": manifest_hash}
        return {"source_root": str(root), "source_commit_or_revision": revision,
                "source_tree_state": build_input["source_tree_state"], "source_state_hash": state_hash,
                "source_trusted": trusted, "build_input_hash": hashlib.sha256(
                    json.dumps(build_input, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                "manifest_hash": manifest_hash, "attested_at": _now()}

    def _stage_receipt(self, candidate: str, manifest_hash: str) -> dict[str, Any] | None:
        if not self.policy.receipt_root.is_dir():
            return None
        for path in sorted(self.policy.receipt_root.glob("stage_*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            if path.is_symlink() or path.stat().st_size > 1024 * 1024:
                continue
            try:
                receipt = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if receipt.get("candidate_release") == candidate and receipt.get("candidate_hash") == manifest_hash:
                return receipt
        return None

    def _attestation_status(self, candidate: str, manifest_hash: str) -> tuple[dict[str, Any] | None, str]:
        receipt = self._stage_receipt(candidate, manifest_hash)
        if not receipt:
            return None, "UNATTESTED_CANDIDATE"
        provenance = receipt.get("provenance_attestation") or {}
        tests = receipt.get("test_attestation") or {}
        if (provenance.get("manifest_hash") != manifest_hash or not provenance.get("source_root") or
                not provenance.get("source_commit_or_revision") or not provenance.get("source_state_hash") or
                not provenance.get("build_input_hash")):
            return receipt, "PROVENANCE_ATTESTATION_INVALID"
        if provenance.get("source_trusted") is not True:
            return receipt, "UNTRUSTED_SOURCE"
        if tests.get("test_result") == "FAIL":
            return receipt, "TESTS_FAILED"
        if (tests.get("test_result") != "PASS" or int(tests.get("test_count", 0) or 0) < 1 or
                not tests.get("test_commands") or not tests.get("test_timestamp")):
            return receipt, "TEST_ATTESTATION_MISSING"
        if (tests.get("tested_manifest_hash") != manifest_hash or
                tests.get("source_build_input_hash") != provenance.get("build_input_hash")):
            return receipt, "ATTESTATION_MANIFEST_MISMATCH"
        current = self._validate_release(self.policy.release_root / candidate, expected_manifest_hash=manifest_hash)
        if not current.get("valid"):
            return receipt, "POST_VALIDATION_MUTATION"
        return receipt, "ATTESTED"

    def request_activation_approval(self, *, deployment_id: str, candidate_release: str,
                                    candidate_hash: str, current_release: str, dropin_name: str) -> dict[str, Any]:
        if self.approval_store is None:
            raise RuntimeError("GOVERNED_APPROVAL_STORE_UNAVAILABLE")
        deployment = _deployment_id(deployment_id)
        candidate = _release_id(candidate_release)
        current = _release_id(current_release)
        self._validate_dropin_name(dropin_name)
        validated = self._validate_release(self.policy.release_root / candidate,
                                           expected_manifest_hash=candidate_hash)
        if not validated["valid"]:
            raise ValueError("CANDIDATE_VALIDATION_FAILED")
        attestation, attestation_status = self._attestation_status(candidate, candidate_hash)
        if attestation_status in {"TESTS_FAILED", "ATTESTATION_MANIFEST_MISMATCH", "POST_VALIDATION_MUTATION"}:
            raise PermissionError("NOVA_RELEASE_ATTESTATION_INVALID:" + attestation_status)
        inputs = {"deployment_id": deployment, "candidate_release": candidate,
                  "candidate_hash": candidate_hash, "current_release": current,
                  "dropin_name": dropin_name, "automatic_rollback_on_failure": True}
        approval = self.approval_store.request(ACTIVATE_ACTION, inputs, {
            "candidate_release": str(self.policy.release_root / candidate),
            "candidate_hash": candidate_hash, "current_release": str(self.policy.release_root / current),
            "rollback_release": str(self.policy.release_root / current), "dropin_name": dropin_name,
            "service_to_restart": self.policy.service,
            "expected_downtime_scope": f"{self.policy.service} restart only; brief service interruption",
            "planned_verification": "release hash, entrypoint/code root/PYTHONPATH equality, service status, exactly one poller",
            "rollback_plan": f"restore snapshotted drop-in; daemon-reload; restart {self.policy.service} only; verify previous identity",
        })
        return {"approval": approval, "approval_required": True, "service_mutations": False}

    def request_rollback_approval(self, *, deployment_id: str, target_release: str,
                                  target_hash: str, current_release: str,
                                  source_deployment_id: str) -> dict[str, Any]:
        deployment = _deployment_id(deployment_id)
        target = _release_id(target_release)
        current = _release_id(current_release)
        source_id = _deployment_id(source_deployment_id)
        validation = self._validate_release(self.policy.release_root / target, expected_manifest_hash=target_hash)
        if not validation["valid"]:
            raise ValueError("ROLLBACK_TARGET_INVALID")
        prior = self.receipt(deployment_id=source_id).get("receipt") or {}
        if (prior.get("candidate_release") != current or prior.get("previous_release") != target or
                prior.get("previous_hash") != target_hash or not prior.get("previous_dropin_snapshot")):
            raise ValueError("ROLLBACK_SOURCE_RECEIPT_MISMATCH")
        if self._known_good_rollback(prior, target, target_hash):
            result = self.rollback(deployment_id=deployment, target_release=target, target_hash=target_hash,
                current_release=current, source_deployment_id=source_id)
            return {**result, "approval_required": False, "rollback_mode": "KNOWN_GOOD_AUTONOMOUS"}
        if self.approval_store is None:
            raise RuntimeError("GOVERNED_APPROVAL_STORE_UNAVAILABLE")
        inputs = {"deployment_id": deployment, "target_release": target,
                  "target_hash": target_hash, "current_release": current,
                  "source_deployment_id": source_id}
        approval = self.approval_store.request(ROLLBACK_ACTION, inputs, {
            "rollback_release": str(self.policy.release_root / target), "rollback_hash": target_hash,
            "current_release": str(self.policy.release_root / current), "service_to_restart": self.policy.service,
            "rollback_plan": f"restore snapshotted Nova drop-in; daemon-reload; restart {self.policy.service} only; verify target identity",
        })
        return {"approval": approval, "approval_required": True, "service_mutations": False}

    def activate(self, *, deployment_id: str, candidate_release: str, candidate_hash: str,
                 previous_release: str, dropin_name: str, approval_id: str = "") -> dict[str, Any]:
        """Activate only a tested immutable candidate or an exactly approved exception."""
        deployment = _deployment_id(deployment_id)
        candidate = _release_id(candidate_release)
        previous = _release_id(previous_release)
        self._validate_dropin_name(dropin_name)
        candidate_path = self.policy.release_root / candidate
        previous_path = self.policy.release_root / previous
        validation = self._validate_release(candidate_path, expected_manifest_hash=candidate_hash)
        rollback_validation = self._validate_release(previous_path)
        if not validation["valid"] or not rollback_validation["valid"]:
            raise ValueError("CANDIDATE_OR_ROLLBACK_VALIDATION_FAILED")
        before = self.inspect_effective_config()
        if not before.get("release") or before.get("release") != previous:
            raise ValueError("CURRENT_RELEASE_DOES_NOT_MATCH_ROLLBACK_TARGET")
        staged_receipt, attestation_status = self._attestation_status(candidate, candidate_hash)
        if attestation_status in {"TESTS_FAILED", "ATTESTATION_MANIFEST_MISMATCH", "POST_VALIDATION_MUTATION"}:
            raise PermissionError("NOVA_RELEASE_ATTESTATION_INVALID:" + attestation_status)
        if not approval_id and attestation_status != "ATTESTED":
            return self.request_activation_approval(deployment_id=deployment, candidate_release=candidate,
                candidate_hash=candidate_hash, current_release=previous, dropin_name=dropin_name)
        if attestation_status != "ATTESTED":
            if self.approval_store is None:
                raise RuntimeError("GOVERNED_APPROVAL_STORE_UNAVAILABLE")
        approval_inputs = {"deployment_id": deployment, "candidate_release": candidate,
                           "candidate_hash": candidate_hash, "current_release": previous,
                           "dropin_name": dropin_name, "automatic_rollback_on_failure": True}
        automatic_attested = attestation_status == "ATTESTED" and not approval_id
        if not automatic_attested:
            self.approval_store.consume(approval_id, ACTIVATE_ACTION, approval_inputs)
        effective_approval_id = approval_id or "ATTESTED_INTERNAL"
        receipt = self._new_receipt(deployment, effective_approval_id, candidate, candidate_hash, previous,
                                    rollback_validation["manifest_hash"], before, operation="ACTIVATE")
        receipt["approval_mode"] = "ATTESTED_INTERNAL" if automatic_attested else "RAY_APPROVED"
        if staged_receipt:
            receipt["provenance_attestation"] = staged_receipt.get("provenance_attestation")
            receipt["test_attestation"] = staged_receipt.get("test_attestation")
        receipt["process_pid_before"] = next(iter(self.host.pollers()), {}).get("pid")
        snapshot = self._snapshot_dropins()
        receipt["previous_dropin_snapshot"] = {
            name: base64.b64encode(content).decode("ascii") for name, content in snapshot.items()
        }
        self._write_receipt(receipt)
        try:
            self._install_single_dropin(candidate_path, dropin_name, deployment)
            receipt["dropin_changed"] = True
            receipt["mutations"] += 1
            receipt["mutation_list"].append("install_single_nova_dropin")
            self._write_receipt(receipt)
            self.host.systemctl("daemon-reload")
            receipt["mutations"] += 1
            receipt["mutation_list"].append("systemd_user_daemon_reload")
            self._write_receipt(receipt)
            self.host.systemctl("restart")
            receipt["service_restarted"] = True
            receipt["mutations"] += 1
            receipt["mutation_list"].append("nova_service_restart")
            self._write_receipt(receipt)
            verified = self.verify(expected_release=candidate, expected_hash=candidate_hash)
            receipt.update({"service_restarted": True, "process_pid_after": verified.get("process_pid"),
                            "start_time_after": verified.get("process_start_time"),
                            "poller_count": verified.get("poller_count"),
                            "verification_result": "PASS" if verified["pass"] else "FAIL"})
            if not verified["pass"]:
                if not approval_inputs["automatic_rollback_on_failure"]:
                    raise RuntimeError("ACTIVATION_VERIFICATION_FAILED_ROLLBACK_NOT_AUTHORIZED")
                self._restore_dropins(snapshot)
                self.host.systemctl("daemon-reload")
                self.host.systemctl("restart")
                rollback = self.verify(expected_release=previous)
                receipt["mutation_list"].extend(["restore_prior_nova_dropins", "systemd_user_daemon_reload", "nova_service_restart_rollback"])
                receipt["rollback_performed"] = True
                receipt["rollback_verification"] = "PASS" if rollback["pass"] else "FAIL"
                receipt["mutations"] = receipt.get("mutations", 0) + 3
                receipt["rollback_receipt_id"] = self._record_automatic_rollback(
                    source_deployment_id=deployment, approval_id=effective_approval_id,
                    failed_release=candidate, failed_hash=candidate_hash,
                    restored_release=previous, restored_hash=rollback_validation["manifest_hash"],
                    verification=rollback)
                self._write_receipt(receipt)
                return {"status": "ROLLED_BACK" if rollback["pass"] else "ROLLBACK_FAILED",
                        "verification": verified, "rollback": rollback, "receipt": receipt}
            self._write_receipt(receipt)
            return {"status": "COMPLETE", "verification": verified, "receipt": receipt}
        except Exception as exc:
            # If configuration was changed, restore it. Automatic rollback is
            # bound into the consumed approval request created above.
            if self._snapshot_differs(snapshot):
                try:
                    self._restore_dropins(snapshot)
                    self.host.systemctl("daemon-reload")
                    self.host.systemctl("restart")
                    rollback = self.verify(expected_release=previous)
                    receipt["mutation_list"].extend(["restore_prior_nova_dropins", "systemd_user_daemon_reload", "nova_service_restart_rollback"])
                    receipt.update({"rollback_performed": True,
                                    "rollback_verification": "PASS" if rollback["pass"] else "FAIL",
                                    "mutations": receipt.get("mutations", 0) + 3})
                    receipt["rollback_receipt_id"] = self._record_automatic_rollback(
                        source_deployment_id=deployment, approval_id=effective_approval_id,
                        failed_release=candidate, failed_hash=candidate_hash,
                        restored_release=previous, restored_hash=rollback_validation["manifest_hash"],
                        verification=rollback)
                except Exception as rollback_exc:
                    receipt["rollback_verification"] = "ERROR:" + type(rollback_exc).__name__
            receipt["verification_result"] = "ERROR:" + type(exc).__name__
            self._write_receipt(receipt)
            raise

    def verify(self, *, expected_release: str, expected_hash: str | None = None) -> dict[str, Any]:
        release = _release_id(expected_release)
        config = self.inspect_effective_config()
        release_path = self.policy.release_root / release
        validation = self._validate_release(release_path, expected_manifest_hash=expected_hash)
        pollers = self.host.pollers()
        status_text = self.host.systemctl("status")
        release_suffix = str(release_path.resolve())
        poller = pollers[0] if len(pollers) == 1 else {}
        pass_value = bool(validation["valid"] and config.get("release") == release and
                          config.get("code_root") == release_suffix and config.get("pythonpath") == str(release_path / "scripts") and
                          len(pollers) == 1 and poller.get("code_root") == release_suffix and
                          str(poller.get("pythonpath", "")) == str(release_path / "scripts") and
                          (self.policy.mode != "certification" or poller.get("cert_release_id") == release) and
                          self.policy.service in status_text and "Active: active (running)" in status_text)
        return {"pass": pass_value, "active_release": release_suffix if config.get("release") == release else "",
                "active_release_hash": validation["manifest_hash"], "entrypoint": config.get("entrypoint", ""),
                "code_root": config.get("code_root", ""), "pythonpath": config.get("pythonpath", ""),
                "active_dropin": config.get("active_dropin", ""), "process_pid": poller.get("pid"),
                "process_start_time": self._start_time(poller.get("pid")), "poller_count": len(pollers),
                "service_state": "RUNNING" if "Active: active (running)" in status_text else "NOT_RUNNING",
                "manifest_mismatches": validation["mismatches"]}

    def rollback(self, *, deployment_id: str, target_release: str, target_hash: str,
                 current_release: str, approval_id: str = "",
                 snapshot: dict[str, bytes] | None = None,
                 source_deployment_id: str = "") -> dict[str, Any]:
        deployment = _deployment_id(deployment_id)
        target = _release_id(target_release)
        current = _release_id(current_release)
        validation = self._validate_release(self.policy.release_root / target, expected_manifest_hash=target_hash)
        current_validation = self._validate_release(self.policy.release_root / current)
        if not validation["valid"] or not current_validation["valid"]:
            raise ValueError("ROLLBACK_TARGET_INVALID")
        inputs = {"deployment_id": deployment, "target_release": target, "target_hash": target_hash,
                  "current_release": current, "source_deployment_id": _deployment_id(source_deployment_id)}
        source_id = inputs["source_deployment_id"]
        if snapshot is None:
            source = inputs["source_deployment_id"]
            prior = self.receipt(deployment_id=source)
            prior_row = prior.get("receipt") or {}
            if (prior_row.get("candidate_release") != current or prior_row.get("previous_release") != target or
                    prior_row.get("previous_hash") != target_hash):
                raise ValueError("ROLLBACK_SOURCE_RECEIPT_MISMATCH")
            encoded = prior_row.get("previous_dropin_snapshot") or {}
            if not encoded:
                raise ValueError("ROLLBACK_CONFIGURATION_SNAPSHOT_REQUIRED")
            snapshot = {name: base64.b64decode(payload, validate=True) for name, payload in encoded.items()}
        source_receipt = self.receipt(deployment_id=source_id).get("receipt", {})
        autonomous_rollback = bool(not approval_id and self._known_good_rollback(source_receipt, target, target_hash))
        if not autonomous_rollback:
            if not approval_id:
                return self.request_rollback_approval(deployment_id=deployment, target_release=target,
                    target_hash=target_hash, current_release=current, source_deployment_id=source_id)
            if self.approval_store is None:
                raise RuntimeError("GOVERNED_APPROVAL_STORE_UNAVAILABLE")
            self.approval_store.consume(approval_id, ROLLBACK_ACTION, inputs)
        effective_approval_id = approval_id or "KNOWN_GOOD_INTERNAL_ROLLBACK"
        receipt = self._new_receipt(deployment, effective_approval_id, target, target_hash, current,
                                    current_validation["manifest_hash"], {}, operation="ROLLBACK")
        receipt["approval_mode"] = "KNOWN_GOOD_AUTONOMOUS" if autonomous_rollback else "RAY_APPROVED"
        receipt["process_pid_before"] = next(iter(self.host.pollers()), {}).get("pid")
        receipt["previous_dropin_snapshot"] = {
            name: base64.b64encode(content).decode("ascii") for name, content in self._snapshot_dropins().items()
        }
        self._write_receipt(receipt)
        try:
            self._restore_dropins(snapshot)
            receipt["dropin_changed"] = True
            receipt["mutations"] += 1
            receipt["mutation_list"].append("restore_nova_dropins")
            self._write_receipt(receipt)
            self.host.systemctl("daemon-reload")
            receipt["mutations"] += 1
            receipt["mutation_list"].append("systemd_user_daemon_reload")
            self._write_receipt(receipt)
            self.host.systemctl("restart")
            receipt["service_restarted"] = True
            receipt["mutations"] += 1
            receipt["mutation_list"].append("nova_service_restart")
            verification = self.verify(expected_release=target, expected_hash=target_hash)
            receipt.update({"process_pid_after": verification.get("process_pid"),
                            "start_time_after": verification.get("process_start_time"),
                            "poller_count": verification.get("poller_count"),
                            "verification_result": "PASS" if verification["pass"] else "FAIL",
                            "rollback_performed": True})
            self._write_receipt(receipt)
            return {"status": "COMPLETE" if verification["pass"] else "ROLLBACK_FAILED",
                    "verification": verification, "receipt": receipt}
        except Exception as exc:
            receipt.update({"verification_result": "ERROR:" + type(exc).__name__, "rollback_performed": True})
            self._write_receipt(receipt)
            raise

    def _known_good_rollback(self, activation_receipt: dict[str, Any], target: str, target_hash: str) -> bool:
        if (activation_receipt.get("operation") != "ACTIVATE" or
                activation_receipt.get("verification_result") != "PASS" or
                activation_receipt.get("candidate_release") != self.inspect_effective_config().get("release") or
                activation_receipt.get("previous_release") != target or
                activation_receipt.get("previous_hash") != target_hash or
                not activation_receipt.get("previous_dropin_snapshot")):
            return False
        target_validation = self._validate_release(self.policy.release_root / target, expected_manifest_hash=target_hash)
        return bool(target_validation.get("valid"))

    def inspect_effective_config(self) -> dict[str, Any]:
        active = sorted(self.policy.dropin_root.glob("*.conf")) if self.policy.dropin_root.is_dir() else []
        if len(active) != 1 or active[0].is_symlink() or not active[0].is_file():
            return {"release": "", "effective_dropin_count": len(active), "active_dropin": ""}
        path = active[0]
        values: dict[str, str] = {}
        exec_start = ""
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("ExecStart=") and line != "ExecStart=":
                exec_start = line.split("=", 1)[1]
            elif line.startswith("Environment="):
                for item in line.split("=", 1)[1].split():
                    if "=" in item:
                        key, value = item.split("=", 1)
                        values[key] = value
        worker = "nova_telegram_worker.py" if self.policy.mode == "production" else "lifecycle_fixture_worker.py"
        match = re.search(r"(/[^ ]+)/scripts/nova/" + re.escape(worker), exec_start)
        release_path = match.group(1) if match else ""
        release = Path(release_path).name if release_path else ""
        return {"release": release, "entrypoint": exec_start, "code_root": values.get("NOVA_CODE_ROOT", ""),
                "pythonpath": values.get("PYTHONPATH", ""), "active_dropin": str(path),
                "effective_dropin_count": len(active)}

    def _install_single_dropin(self, candidate: Path, name: str, deployment: str) -> None:
        self.policy.dropin_root.mkdir(parents=True, exist_ok=True)
        target = self.policy.dropin_root / name
        if target.suffix != ".conf" or not _under(target, self.policy.dropin_root):
            raise ValueError("INVALID_NOVA_DROPIN_PATH")
        for old in self.policy.dropin_root.glob("*.conf"):
            if old == target:
                continue
            old.rename(old.with_name(old.name + ".inactive." + deployment))
        if self.policy.mode == "certification":
            content = ("[Service]\nExecStart=\n"
                       f"ExecStart=/usr/bin/python3 {candidate}/scripts/nova/lifecycle_fixture_worker.py --hold\n"
                       "Environment=\n"
                       f"Environment=NOVA_CODE_ROOT={candidate}\n"
                       f"Environment=PYTHONPATH={candidate}/scripts\n"
                       f"Environment=NOVA_CERT_RELEASE_ID={candidate.name}\n"
                       "Environment=NOVA_LIFECYCLE_CERTIFICATION=1\n")
        else:
            content = ("[Service]\nExecStart=\n"
                       f"ExecStart=/home/opc/.local/share/nexus-venvs/nova-runtime/bin/python {candidate}/scripts/nova/nova_telegram_worker.py --poll\n"
                       "Environment=\n"
                       f"Environment=NOVA_CODE_ROOT={candidate}\n"
                       f"Environment=PYTHONPATH={candidate}/scripts\n"
                       f"Environment=NOVA_REPO_ROOT={self.policy.runtime_state_root.parents[1]}\n"
                       f"Environment=NEXUS_REPO_ROOT={self.policy.runtime_state_root.parents[1]}\n"
                       f"Environment=NEXUS_GOVERNOR_DB={self.policy.runtime_state_root / 'resource_spend_governor.sqlite3'}\n"
                       f"Environment=NOVA_PROACTIVE_DATA_ROOT={candidate}\n"
                       "Environment=NOVA_PROACTIVE_STATE_PATH=/home/opc/.nexus/state/nova/nova_proactive_communications.json\n"
                       "Environment=NOVA_GATEWAY_CERTIFICATION_CANARY=0\n"
                       "Environment=NOVA_RUNTIME_ENV=/home/opc/.config/nova-telegram.env\n"
                       "Environment=NOVA_TRACE_DIR=/home/opc/.nexus/state/nova/agent_traces\n")
        self._atomic_write(target, content.encode(), 0o644)

    def _snapshot_dropins(self) -> dict[str, bytes]:
        if not self.policy.dropin_root.exists():
            return {}
        rows: dict[str, bytes] = {}
        for path in self.policy.dropin_root.iterdir():
            if path.is_symlink() or not path.is_file():
                raise ValueError("UNSUPPORTED_NOVA_DROPIN_ENTRY")
            rows[path.name] = path.read_bytes()
        return rows

    def _restore_dropins(self, snapshot: dict[str, bytes]) -> None:
        if any(name in {".", ".."} or not re.fullmatch(r"[A-Za-z0-9_.~+-]{1,255}", name) or Path(name).name != name
               or not isinstance(payload, bytes) for name, payload in snapshot.items()):
            raise ValueError("INVALID_DROPIN_SNAPSHOT")
        self.policy.dropin_root.mkdir(parents=True, exist_ok=True)
        for path in self.policy.dropin_root.iterdir():
            if path.is_symlink() or path.is_file():
                path.unlink()
            else:
                raise ValueError("UNSUPPORTED_NOVA_DROPIN_ENTRY")
        for name, payload in snapshot.items():
            self._atomic_write(self.policy.dropin_root / name, payload, 0o644)

    def _snapshot_differs(self, snapshot: dict[str, bytes]) -> bool:
        return self._snapshot_dropins() != snapshot

    @staticmethod
    def _validate_dropin_name(name: str) -> None:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,80}\.conf", str(name)):
            raise ValueError("INVALID_NOVA_DROPIN_NAME")

    @staticmethod
    def _atomic_write(path: Path, payload: bytes, mode: int) -> None:
        temporary = path.with_name(path.name + ".tmp." + uuid.uuid4().hex)
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            try: temporary.unlink()
            except FileNotFoundError: pass

    def _new_receipt(self, deployment: str, approval_id: str, candidate: str, candidate_hash: str,
                     previous: str, previous_hash: str, before: dict[str, Any],
                     *, operation: str = "ACTIVATE") -> dict[str, Any]:
        return {"deployment_id": deployment, "operation": operation, "requested_by": "ray",
                "approval_id": approval_id, "candidate_release": candidate,
                "candidate_hash": candidate_hash, "previous_release": previous,
                "previous_hash": previous_hash, "dropin_changed": False,
                "service_restarted": False, "process_pid_before": None,
                "process_pid_after": None, "start_time_after": None,
                "poller_count": None, "verification_result": "PENDING",
                "rollback_performed": False, "mutations": 0, "mutation_list": [],
                "started_at": _now(), "created_at": _now(), "completed_at": None,
                "active_dropin_before": before.get("active_dropin", ""),
                "previous_effective_config": before}

    def _record_automatic_rollback(self, *, source_deployment_id: str, approval_id: str,
                                   failed_release: str, failed_hash: str,
                                   restored_release: str, restored_hash: str,
                                   verification: dict[str, Any]) -> str:
        rollback_id = "deploy_" + uuid.uuid4().hex
        receipt = self._new_receipt(rollback_id, approval_id, restored_release, restored_hash,
                                    failed_release, failed_hash, {}, operation="AUTOMATIC_ROLLBACK")
        receipt.update({"source_deployment_id": source_deployment_id,
                        "dropin_changed": True, "service_restarted": True,
                        "process_pid_after": verification.get("process_pid"),
                        "start_time_after": verification.get("process_start_time"),
                        "poller_count": verification.get("poller_count"),
                        "verification_result": "PASS" if verification.get("pass") else "FAIL",
                        "rollback_performed": True, "mutations": 3,
                        "mutation_list": ["restore_prior_nova_dropins", "systemd_user_daemon_reload",
                                          "nova_service_restart_rollback"]})
        self._write_receipt(receipt)
        return rollback_id

    def _write_receipt(self, receipt: dict[str, Any]) -> None:
        self.policy.receipt_root.mkdir(parents=True, exist_ok=True)
        if receipt.get("verification_result") not in {"PENDING", "PREPARED"}:
            receipt["completed_at"] = _now()
        receipt["updated_at"] = _now()
        path = self.policy.receipt_root / (str(receipt["deployment_id"]) + ".json")
        self._atomic_write(path, (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode(), 0o600)

    @staticmethod
    def _start_time(pid: int | None) -> str:
        if not pid:
            return ""
        try:
            stat = Path("/proc", str(pid), "stat").read_text().rpartition(")")[2].split()
            ticks = int(stat[19])
            hz = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
            uptime = float(Path("/proc/uptime").read_text().split()[0])
            timestamp = time.time() - max(0, uptime - ticks / hz)
            return datetime.fromtimestamp(timestamp, timezone.utc).isoformat().replace("+00:00", "Z")
        except (OSError, ValueError, IndexError):
            return "UNAVAILABLE"


class GovernedApprovalStore:
    """Adapter to the existing append-only Ray approval ledger."""
    def request(self, action_id: str, inputs: dict[str, Any], detail: dict[str, Any]) -> dict[str, Any]:
        if action_id not in {ACTIVATE_ACTION, ROLLBACK_ACTION}:
            raise ValueError("NOVA_APPROVAL_ACTION_NOT_ALLOWED")
        from nexus_agent_platform.governed.approvals import create_approval_request
        row = create_approval_request(action_id=action_id, requested_by="nova_release_controller",
            requested_for="ray", input_summary=inputs,
            action_summary=f"{action_id}: {json.dumps(detail, sort_keys=True)}",
            evidence_refs=[str(detail.get("candidate_release") or detail.get("rollback_release") or "")])
        return row

    def consume(self, approval_id: str, action_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
        from nexus_agent_platform.governed.approvals import get_approval, is_approval_valid_for, mark_approval_consumed
        row = get_approval(str(approval_id))
        if not row or row.get("action_id") != action_id or row.get("input_summary") != inputs:
            raise PermissionError("NOVA_APPROVAL_NOT_BOUND_TO_REQUEST")
        resolved_by = " ".join(str(row.get("resolved_by") or "").upper().replace("_", " ").split())
        if resolved_by not in {"RAY", "RAY DAVIS", "RAYMOND DAVIS"}:
            raise PermissionError("NOVA_RELEASE_REQUIRES_RAY_APPROVAL")
        reason = is_approval_valid_for(row, action_id, inputs)
        if reason:
            raise PermissionError("NOVA_APPROVAL_INVALID:" + reason)
        mark_approval_consumed(str(approval_id))
        return row


class NovaReleaseCapability:
    """Typed capability facade; rejects unknown operation names and arguments."""
    CONTRACTS = {
        "nova.release.status": (set(), {"deployment_id"}),
        "nova.release.stage": ({"candidate_release", "bundle_id"}, set()),
        "nova.release.validate": ({"candidate_release"}, {"expected_manifest_hash"}),
        "nova.release.activate": ({"deployment_id", "candidate_release", "candidate_hash", "current_release", "dropin_name"}, {"approval_id"}),
        "nova.release.verify": ({"expected_release"}, {"expected_hash"}),
        "nova.release.rollback": ({"deployment_id", "target_release", "target_hash", "current_release", "source_deployment_id"}, {"approval_id"}),
    }

    def __init__(self, controller: NovaReleaseController):
        self.controller = controller

    def invoke(self, capability: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        if capability not in self.CONTRACTS:
            raise ValueError("NOVA_RELEASE_CAPABILITY_NOT_ALLOWED")
        required, optional = self.CONTRACTS[capability]
        values = dict(arguments or {})
        if set(values) - required - optional or required - set(values):
            raise ValueError("NOVA_RELEASE_ARGUMENT_SCHEMA_INVALID")
        if capability == "nova.release.status":
            deployment_id = values.pop("deployment_id", "")
            return self.controller.receipt(deployment_id=deployment_id) if deployment_id else self.controller.status()
        if capability == "nova.release.stage":
            return self.controller.stage(**values)
        if capability == "nova.release.validate":
            return self.controller.validate(**values)
        if capability == "nova.release.activate":
            approval_id = values.pop("approval_id", "")
            current_release = values.pop("current_release")
            return self.controller.activate(**{**values, "previous_release": current_release,
                                               "approval_id": approval_id})
        if capability == "nova.release.verify":
            return self.controller.verify(**values)
        if capability == "nova.release.rollback":
            approval_id = values.pop("approval_id", "")
            return self.controller.rollback(**{**values, "approval_id": approval_id})
        raise ValueError("NOVA_RELEASE_CAPABILITY_NOT_ALLOWED")

