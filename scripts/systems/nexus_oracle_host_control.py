"""Fixed-scope, local-only Oracle host control for Nexus Systems.

The server accepts one bounded JSON request per AF_UNIX connection. It has no
TCP listener, shell endpoint, caller-provided filesystem path, or caller-
provided service name. Production mutations require a single-use approval
record whose hash binds the operation and all relevant runtime evidence.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import socket
import socketserver
import stat
import subprocess
import tarfile
import tempfile
import time
import uuid
import struct
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable


RELEASE_ROOT = Path("/home/opc/.nexus/releases")
STATE_ROOT = Path("/home/opc/.nexus/state/host-control")
INCOMING_ROOT = STATE_ROOT / "incoming"
SOCKET_PATH = STATE_ROOT / "host-control.sock"
PRODUCTION_SERVICE = "nova-telegram-oracle.service"
CERTIFICATION_SERVICE = "nova-release-lifecycle-cert.service"
UNIT_ROOT = Path("/home/opc/.config/systemd/user")
DROPIN_ROOT = UNIT_ROOT / (PRODUCTION_SERVICE + ".d")
BASE_UNIT = UNIT_ROOT / PRODUCTION_SERVICE
NEW_DROPIN_NAME = "90-nexus-r69.1-host-control.conf"
PRODUCTION_PYTHON = "/home/opc/.local/share/nexus-venvs/nova-runtime/bin/python"
MAX_FILES = 12000
MAX_BYTES = 256 * 1024 * 1024
MAX_REQUEST_BYTES = 2 * 1024 * 1024
RELEASE_NAME_RE = re.compile(r"[a-z0-9][a-z0-9.-]{2,119}\Z")
ID_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._-]{1,79}\Z")
HASH_RE = re.compile(r"[a-f0-9]{64}\Z")
APPROVAL_RE = re.compile(r"appr_[a-f0-9]{32}\Z")

CAPABILITIES = frozenset({
    "systems.oracle.release.inspect", "systems.oracle.release.stage",
    "systems.oracle.nova.snapshot", "systems.oracle.nova.snapshot_validate",
    "systems.oracle.nova.poller_status", "systems.oracle.nova.activate",
    "systems.oracle.nova.verify", "systems.oracle.nova.rollback",
    "systems.oracle.receipt.read",
})
SCHEMAS: dict[str, tuple[set[str], set[str]]] = {
    "systems.oracle.release.inspect": ({"release_name", "expected_hash"}, set()),
    "systems.oracle.release.stage": ({"artifact_id", "release_name", "expected_release_hash",
                                      "expected_manifest_hash", "approval_id"}, set()),
    "systems.oracle.nova.snapshot": (set(), set()),
    "systems.oracle.nova.snapshot_validate": ({"snapshot_id"}, set()),
    "systems.oracle.nova.poller_status": (set(), set()),
    "systems.oracle.nova.activate": ({"deployment_id", "target_release_name", "target_release_hash",
                                       "shared_release_hash", "dependency_lock_hash", "current_snapshot_hash",
                                       "target_dropin_hash", "expected_effective_dropin_count",
                                       "automatic_rollback_on_failure", "approval_id"}, set()),
    "systems.oracle.nova.verify": ({"expected_release_name", "expected_release_hash"}, set()),
    "systems.oracle.nova.rollback": ({"snapshot_id", "snapshot_hash", "approval_id"}, set()),
    "systems.oracle.receipt.read": ({"receipt_id"}, set()),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_hash(value: dict[str, Any]) -> str:
    return _sha(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def _safe_name(value: Any, pattern: re.Pattern[str], error: str) -> str:
    text = str(value or "")
    if not pattern.fullmatch(text) or "/" in text or "\\" in text or ".." in text:
        raise ValueError(error)
    return text


def _manifest(root: Path, expected_hash: str | None = None) -> dict[str, Any]:
    manifest = root / "RELEASE_MANIFEST.sha256"
    if root.is_symlink() or manifest.is_symlink() or not root.is_dir() or not manifest.is_file():
        return {"present": False, "hash": "", "entries": 0, "mismatches": ["release_or_manifest_missing"], "read_only": False}
    raw = manifest.read_bytes()
    manifest_hash = _sha(raw)
    mismatches: list[str] = []
    listed: set[str] = set()
    total = 0
    for line in raw.decode("utf-8", errors="replace").splitlines():
        match = re.fullmatch(r"([a-f0-9]{64})  ([A-Za-z0-9_.+/-]{1,300})", line)
        if not match:
            mismatches.append("malformed_manifest_line")
            continue
        digest, reltext = match.groups()
        rel = PurePosixPath(reltext)
        if rel.is_absolute() or not rel.parts or ".." in rel.parts or reltext in listed:
            mismatches.append("unsafe_or_duplicate_manifest_path")
            continue
        listed.add(reltext)
        target = root.joinpath(*rel.parts)
        try:
            cursor = root
            for part in rel.parts:
                cursor = cursor / part
                if cursor.is_symlink():
                    raise ValueError("manifest_symlink_path")
            if target.is_symlink() or not target.is_file() or not target.resolve().is_relative_to(root.resolve()):
                mismatches.append("missing_or_symlink:" + reltext)
                continue
            content = target.read_bytes()
            total += len(content)
            if _sha(content) != digest:
                mismatches.append("hash:" + reltext)
        except OSError:
            mismatches.append("unreadable:" + reltext)
        if len(listed) > MAX_FILES or total > MAX_BYTES:
            mismatches.append("artifact_bound_exceeded")
            break
    actual: set[str] = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            mismatches.append("symlink_present")
        elif path.is_file() and path != manifest:
            actual.add(path.relative_to(root).as_posix())
    mismatches.extend("unlisted:" + name for name in sorted(actual - listed))
    if expected_hash and (not HASH_RE.fullmatch(expected_hash) or manifest_hash != expected_hash):
        mismatches.append("release_hash_mismatch")
    writable = bool(root.stat().st_mode & 0o222)
    for path in root.rglob("*"):
        if path.is_dir() and path.stat().st_mode & 0o222:
            writable = True
        if path.is_file() and path.stat().st_mode & 0o222:
            writable = True
    if manifest.stat().st_mode & 0o222:
        writable = True
    return {"present": True, "hash": manifest_hash, "entries": len(listed),
            "mismatches": sorted(set(mismatches)), "read_only": not writable}


@dataclass(frozen=True)
class Policy:
    release_root: Path = RELEASE_ROOT
    state_root: Path = STATE_ROOT
    incoming_root: Path = INCOMING_ROOT
    unit_root: Path = UNIT_ROOT
    dropin_root: Path = DROPIN_ROOT
    base_unit: Path = BASE_UNIT
    service: str = PRODUCTION_SERVICE
    certification_service: str = CERTIFICATION_SERVICE
    cgroup_root: Path = Path("/sys/fs/cgroup")
    proc_root: Path = Path("/proc")
    # Test-only injection. Production construction does not accept request paths.
    test_mode: bool = False

    def __post_init__(self) -> None:
        if self.service != PRODUCTION_SERVICE or self.certification_service != CERTIFICATION_SERVICE:
            raise ValueError("SERVICE_POLICY_FIXED")
        if not self.test_mode:
            fixed = ((self.release_root, RELEASE_ROOT), (self.state_root, STATE_ROOT),
                     (self.incoming_root, INCOMING_ROOT), (self.unit_root, UNIT_ROOT),
                     (self.dropin_root, DROPIN_ROOT), (self.base_unit, BASE_UNIT))
            if any(Path(got) != expected for got, expected in fixed):
                raise ValueError("PATH_POLICY_FIXED")


class HostControl:
    def __init__(self, policy: Policy = Policy(), runner: Callable[..., Any] = subprocess.run):
        self.p = policy
        self.runner = runner

    def invoke(self, capability: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        if capability not in CAPABILITIES:
            raise ValueError("CAPABILITY_NOT_ALLOWED")
        args = dict(arguments or {})
        required, optional = SCHEMAS[capability]
        if set(args) != required | optional:
            raise ValueError("ARGUMENT_SCHEMA_INVALID")
        if capability == "systems.oracle.release.inspect":
            return self.inspect(args["release_name"], args["expected_hash"])
        if capability == "systems.oracle.release.stage":
            return self.stage(**args)
        if capability == "systems.oracle.nova.snapshot":
            return self.snapshot()
        if capability == "systems.oracle.nova.snapshot_validate":
            return self.snapshot_validate(args["snapshot_id"])
        if capability == "systems.oracle.nova.poller_status":
            return self.poller_status()
        if capability == "systems.oracle.nova.verify":
            return self.verify(args["expected_release_name"], args["expected_release_hash"])
        if capability == "systems.oracle.nova.activate":
            return self.activate(**args)
        if capability == "systems.oracle.nova.rollback":
            return self.rollback(**args)
        return self.receipt_read(args["receipt_id"])

    def inspect(self, release_name: str, expected_hash: str) -> dict[str, Any]:
        name = _safe_name(release_name, RELEASE_NAME_RE, "RELEASE_NAME_INVALID")
        if not HASH_RE.fullmatch(str(expected_hash)):
            raise ValueError("EXPECTED_HASH_INVALID")
        result = _manifest(self.p.release_root / name, str(expected_hash))
        return {"release_name": name, "release_path": str(self.p.release_root / name), **result,
                "read_only": result["read_only"]}

    def _receipt(self, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.p.state_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        receipt_id = "hcr_" + uuid.uuid4().hex
        row = {"receipt_id": receipt_id, "operation": operation, **payload,
               "mutation_count": len(payload.get("mutations", [])), "completed_at": _now()}
        path = self.p.state_root / "receipts" / (receipt_id + ".json")
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        _atomic_json(path, row, 0o600)
        return row

    def stage(self, artifact_id: str, release_name: str, expected_release_hash: str,
              expected_manifest_hash: str, approval_id: str) -> dict[str, Any]:
        aid = _safe_name(artifact_id, ID_RE, "ARTIFACT_ID_INVALID")
        name = _safe_name(release_name, RELEASE_NAME_RE, "RELEASE_NAME_INVALID")
        if not HASH_RE.fullmatch(expected_release_hash) or expected_release_hash != expected_manifest_hash:
            raise ValueError("ARTIFACT_HASH_CONTRACT_INVALID")
        self._consume_approval(approval_id, "STAGE", {"artifact_id": aid, "release_name": name,
            "artifact_hash": expected_release_hash, "manifest_hash": expected_manifest_hash})
        archive = self.p.incoming_root / (aid + ".tar.gz")
        if archive.is_symlink() or not archive.is_file() or archive.stat().st_size > MAX_BYTES:
            raise ValueError("APPROVED_ARTIFACT_NOT_FOUND_OR_TOO_LARGE")
        destination = self.p.release_root / name
        if destination.exists():
            raise FileExistsError("IMMUTABLE_RELEASE_ALREADY_EXISTS")
        self.p.release_root.mkdir(parents=True, exist_ok=True)
        temporary = self.p.release_root / ("." + name + ".stage-" + uuid.uuid4().hex)
        published = False
        try:
            temporary.mkdir(mode=0o700)
            with tarfile.open(archive, "r:*") as tf:
                members = tf.getmembers()
                if len(members) > MAX_FILES or any(not _safe_tar_member(m) for m in members):
                    raise ValueError("ARTIFACT_ARCHIVE_PATH_REJECTED")
                if sum(max(0, member.size) for member in members) > MAX_BYTES:
                    raise ValueError("ARTIFACT_UNCOMPRESSED_SIZE_LIMIT")
                for member in members:
                    target = temporary.joinpath(*PurePosixPath(member.name).parts)
                    target.relative_to(temporary)
                    if member.isdir():
                        target.mkdir(parents=True, exist_ok=True, mode=0o700)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                        source = tf.extractfile(member)
                        if source is None:
                            raise ValueError("ARTIFACT_MEMBER_UNREADABLE")
                        with source, target.open("xb") as output:
                            shutil.copyfileobj(source, output)
            checked = _manifest(temporary, expected_manifest_hash)
            if checked["mismatches"]:
                raise ValueError("STAGED_ARTIFACT_MANIFEST_MISMATCH")
            for path in sorted(temporary.rglob("*"), reverse=True):
                path.chmod(0o555 if path.is_dir() else 0o444)
            temporary.chmod(0o755)
            os.replace(temporary, destination)
            published = True
            destination.chmod(0o555)
            checked = _manifest(destination, expected_release_hash)
            if checked["mismatches"] or not checked["read_only"]:
                raise ValueError("STAGED_ARTIFACT_FINAL_VERIFICATION_FAILED")
        except Exception:
            if published and destination.exists():
                _remove_tree(destination)
            if temporary.exists():
                _remove_tree(temporary)
            raise
        receipt = self._receipt("STAGE", {"artifact_id": aid, "release_name": name,
            "release_hash": expected_release_hash, "manifest_hash": expected_manifest_hash,
            "final_path": str(destination), "files_written": checked["entries"],
            "permissions_applied": "directories=0555,files=0444", "verification_result": "PASS",
            "mutations": ["immutable_release_stage", "stage_receipt"]})
        return {"status": "STAGED", "verification": checked, "receipt": receipt}

    def snapshot(self) -> dict[str, Any]:
        if not self.p.base_unit.is_file() or self.p.base_unit.is_symlink():
            raise ValueError("NOVA_BASE_UNIT_UNAVAILABLE")
        show = self._systemctl("show", "--property=MainPID,FragmentPath,DropInPaths,ExecStart,WorkingDirectory,Environment,NOVA_CODE_ROOT,PYTHONPATH,NOVA_REPO_ROOT,ControlGroup")
        status = self._systemctl("status", "--no-pager", "-n", "0")
        props = _parse_properties(show)
        dropins = [Path(x) for x in props.get("DropInPaths", "").split() if x]
        if any(path.parent != self.p.dropin_root or path.is_symlink() or not path.is_file() for path in dropins):
            raise ValueError("NOVA_DROPIN_SCOPE_INVALID")
        units = {str(self.p.base_unit): _read_config(self.p.base_unit)}
        for path in dropins:
            units[str(path)] = _read_config(path)
        directory_entries = []
        if self.p.dropin_root.exists():
            for entry in sorted(self.p.dropin_root.iterdir(), key=lambda p: p.name):
                if entry.is_symlink() or not entry.is_file():
                    raise ValueError("NOVA_DROPIN_DIRECTORY_ENTRY_UNSUPPORTED")
                units[str(entry)] = _read_config(entry)
                directory_entries.append(str(entry))
        payload = {"snapshot_id": "snap_" + uuid.uuid4().hex, "service": self.p.service,
            "base_unit": str(self.p.base_unit), "ordered_dropins": [str(p) for p in dropins],
            "directory_entries": directory_entries, "files": units,
            "effective": _redact_properties(props), "service_state": status[-1000:],
            "captured_at": _now()}
        main_pid = props.get("MainPID", "")
        if re.fullmatch(r"[1-9][0-9]{0,8}", main_pid):
            payload["process_start_time"] = _process_start_time(Path("/proc") / main_pid / "stat")
        payload["configuration_hash"] = _snapshot_configuration_hash(payload)
        payload["snapshot_hash"] = _json_hash(payload)
        path = self.p.state_root / "snapshots" / (payload["snapshot_id"] + ".json")
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        _atomic_json(path, payload, 0o600)
        return {"snapshot_id": payload["snapshot_id"], "snapshot_hash": payload["snapshot_hash"],
                "dropin_count": len(dropins), "service": self.p.service}

    def snapshot_validate(self, snapshot_id: str) -> dict[str, Any]:
        snap = self._load_snapshot(snapshot_id)
        required = {"base_unit", "ordered_dropins", "directory_entries", "files", "effective", "service_state", "configuration_hash", "snapshot_hash"}
        missing = sorted(required - set(snap))
        no_content = [path for path in [snap.get("base_unit"), *snap.get("directory_entries", [])]
                      if path not in snap.get("files", {})]
        unhashed = [path for path, row in snap.get("files", {}).items()
                    if not isinstance(row, dict) or _sha(base64.b64decode(row.get("content_b64", ""))) != row.get("sha256")]
        expected = dict(snap); stored_hash = expected.pop("snapshot_hash", None)
        stored_config_hash = snap.get("configuration_hash")
        valid = (not missing and not no_content and not unhashed and _json_hash(expected) == stored_hash
                 and _snapshot_configuration_hash(snap) == stored_config_hash)
        return {"valid": valid, "missing_components": missing + no_content + unhashed,
                "snapshot_hash": stored_hash, "read_only": True}

    def poller_status(self) -> dict[str, Any]:
        props = _parse_properties(self._systemctl("show", "--property=MainPID,ControlGroup"))
        main_pid = _pid(props.get("MainPID", ""))
        group = props.get("ControlGroup", "")
        if not group.startswith("/") or ".." in Path(group).parts:
            raise ValueError("SERVICE_CGROUP_INVALID")
        procs = self.p.cgroup_root / group.lstrip("/") / "cgroup.procs"
        pids = []
        for token in procs.read_text(encoding="ascii").split():
            pid = _pid(token)
            cmd = self.p.proc_root / pid / "cmdline"
            argv = [x.decode(errors="replace") for x in cmd.read_bytes().split(b"\0") if x]
            if any(x.endswith("nova_telegram_worker.py") for x in argv) and "--poll" in argv:
                pids.append(pid)
        return {"service": self.p.service, "main_pid": main_pid,
                "poller_count": len(set(pids)), "poller_pids": sorted(set(pids)), "read_only": True}

    def verify(self, expected_release_name: str, expected_release_hash: str) -> dict[str, Any]:
        name = _safe_name(expected_release_name, RELEASE_NAME_RE, "RELEASE_NAME_INVALID")
        inspected = self.inspect(name, expected_release_hash)
        props = _parse_properties(self._systemctl("show", "--property=MainPID,ExecStart,WorkingDirectory,Environment,NOVA_CODE_ROOT,PYTHONPATH"))
        env = _environment_map(props.get("Environment", ""))
        state = self._systemctl("is-active")
        pollers = self.poller_status()
        release = str(self.p.release_root / name)
        checks = {"release_valid": inspected["present"] and not inspected["mismatches"],
                  "entrypoint_matches": release in props.get("ExecStart", ""),
                  "code_root_matches": env.get("NOVA_CODE_ROOT", props.get("NOVA_CODE_ROOT", "")) == release,
                  "pythonpath_matches": bool(env.get("PYTHONPATH", props.get("PYTHONPATH", ""))) and all(x.startswith(release + "/") or x == (env.get("NOVA_SHARED_PLATFORM_RELEASE_ROOT", "") + "/scripts") for x in env.get("PYTHONPATH", props.get("PYTHONPATH", "")).split(":")),
                  "service_running": state.strip() == "active", "single_poller": pollers["poller_count"] == 1}
        return {"pass": all(checks.values()), "checks": checks, "main_pid": props.get("MainPID"),
                "poller_count": pollers["poller_count"], "read_only": True}

    def activate(self, **args: Any) -> dict[str, Any]:
        return self._mutate_with_approval("ACTIVATE", args)

    def rollback(self, **args: Any) -> dict[str, Any]:
        return self._mutate_with_approval("ROLLBACK", args)

    def _mutate_with_approval(self, operation: str, args: dict[str, Any]) -> dict[str, Any]:
        approval_id = args.pop("approval_id")
        if operation == "ACTIVATE":
            return self._activate_approved(approval_id, args)
        return self._rollback_approved(approval_id, args)

    def _activate_approved(self, approval_id: str, args: dict[str, Any]) -> dict[str, Any]:
        name = _safe_name(args["target_release_name"], RELEASE_NAME_RE, "RELEASE_NAME_INVALID")
        if args["expected_effective_dropin_count"] != 1:
            raise ValueError("EFFECTIVE_DROPIN_COUNT_MUST_BE_ONE")
        if args["automatic_rollback_on_failure"] is not True:
            raise ValueError("AUTOMATIC_ROLLBACK_MUST_BE_PREAUTHORIZED")
        for key in ("target_release_hash", "shared_release_hash", "dependency_lock_hash",
                    "current_snapshot_hash", "target_dropin_hash"):
            if not HASH_RE.fullmatch(str(args[key])):
                raise ValueError("APPROVAL_HASH_INVALID:" + key)
        binding = {**args, "service_target": self.p.service}
        self._validate_approval(approval_id, "ACTIVATE", binding)
        release_check = self.inspect(name, args["target_release_hash"])
        if not release_check["present"] or release_check["mismatches"] or not release_check["read_only"]:
            raise ValueError("TARGET_RELEASE_INVALID")
        snapshot = self._snapshot_by_hash(args["current_snapshot_hash"])
        validation = self.snapshot_validate(snapshot["snapshot_id"])
        if not validation["valid"]:
            raise ValueError("CURRENT_SNAPSHOT_INVALID")
        fresh_ref = self.snapshot()
        fresh_snapshot = self._load_snapshot(fresh_ref["snapshot_id"])
        if fresh_snapshot.get("configuration_hash") != snapshot.get("configuration_hash"):
            raise ValueError("CURRENT_NOVA_SNAPSHOT_STALE")
        shared_path, lock_hash = self._shared_dependency(name, args["shared_release_hash"])
        if lock_hash != args["dependency_lock_hash"]:
            raise ValueError("DEPENDENCY_LOCK_HASH_MISMATCH")
        dropin = _dropin_content(self.p.release_root / name, shared_path)
        if _sha(dropin) != args["target_dropin_hash"]:
            raise ValueError("TARGET_DROPIN_HASH_MISMATCH")
        binding["expected_effective_dropin_count"] = 1
        self._consume_approval(approval_id, "ACTIVATE", binding)
        deployment_id = args.get("deployment_id")
        if not re.fullmatch(r"deploy_[a-f0-9]{32}", str(deployment_id)):
            raise ValueError("DEPLOYMENT_ID_INVALID")
        before = _parse_properties(self._systemctl("show", "--property=MainPID")).get("MainPID", "")
        started = _now()
        mutation_list: list[str] = []
        try:
            self._disable_current_dropins(deployment_id)
            mutation_list.append("historical_dropins_made_inactive")
            _atomic_bytes(self.p.dropin_root / NEW_DROPIN_NAME, dropin, 0o644)
            mutation_list.append("authoritative_dropin_installed")
            self._systemctl_mutation("daemon-reload")
            mutation_list.append("user_daemon_reload")
            self._systemctl_mutation("restart")
            mutation_list.append("nova_service_restart")
            verification = self.verify(name, args["target_release_hash"])
            if not verification["pass"]:
                raise RuntimeError("POST_ACTIVATION_VERIFICATION_FAILED")
            receipt = self._receipt("ACTIVATE", {"deployment_id": deployment_id,
                "target_release_name": name, "target_release_hash": args["target_release_hash"],
                "shared_release_hash": args["shared_release_hash"],
                "dependency_lock_hash": args["dependency_lock_hash"],
                "snapshot_id": snapshot["snapshot_id"], "snapshot_hash": args["current_snapshot_hash"],
                "approval_id": approval_id, "process_pid_before": before,
                "process_pid_after": verification.get("main_pid"), "verification_result": verification,
                "rollback_performed": False, "mutations": mutation_list, "started_at": started})
            return {"status": "ACTIVATED", "verification": verification, "receipt": receipt}
        except Exception as exc:
            rollback = self._restore_snapshot(snapshot, restart=True)
            receipt = self._receipt("ACTIVATE_FAILED_AUTO_ROLLBACK", {"deployment_id": deployment_id,
                "target_release_name": name, "target_release_hash": args["target_release_hash"],
                "snapshot_id": snapshot["snapshot_id"], "snapshot_hash": args["current_snapshot_hash"],
                "approval_id": approval_id, "verification_result": str(exc),
                "rollback_performed": bool(rollback.get("pass")),
                "rollback_verification": rollback, "mutations": mutation_list + rollback.get("mutations", []),
                "started_at": started})
            return {"status": "FAILED_ROLLED_BACK" if rollback.get("pass") else "FAILED_ROLLBACK_UNVERIFIED",
                    "verification_error": type(exc).__name__, "rollback": rollback, "receipt": receipt}

    def _rollback_approved(self, approval_id: str, args: dict[str, Any]) -> dict[str, Any]:
        binding = {**args, "service_target": self.p.service}
        self._validate_approval(approval_id, "ROLLBACK", binding)
        snap = self._load_snapshot(args["snapshot_id"])
        if snap.get("snapshot_hash") != args["snapshot_hash"]:
            raise ValueError("SNAPSHOT_HASH_MISMATCH")
        if not self.snapshot_validate(args["snapshot_id"])["valid"]:
            raise ValueError("ROLLBACK_SNAPSHOT_INVALID")
        self._consume_approval(approval_id, "ROLLBACK", binding)
        result = self._restore_snapshot(snap, restart=True)
        receipt = self._receipt("ROLLBACK", {**args, "approval_id": approval_id,
            "verification_result": result, "rollback_performed": True,
            "mutations": result.get("mutations", [])})
        return {"status": "ROLLED_BACK" if result.get("pass") else "ROLLBACK_FAILED",
                "verification": result, "receipt": receipt}

    def _disable_current_dropins(self, deployment_id: str) -> None:
        self.p.dropin_root.mkdir(parents=True, exist_ok=True)
        for path in sorted(self.p.dropin_root.glob("*.conf")):
            if path.is_symlink() or not path.is_file():
                raise ValueError("DROPIN_NOT_REGULAR_FILE")
            path.rename(path.with_name(path.name + ".inactive." + deployment_id))

    def _restore_snapshot(self, snapshot: dict[str, Any], *, restart: bool) -> dict[str, Any]:
        if Path(snapshot["base_unit"]) != self.p.base_unit:
            raise ValueError("SNAPSHOT_BASE_UNIT_MISMATCH")
        current_base = self.p.base_unit.read_bytes()
        saved_base = base64.b64decode(snapshot["files"][str(self.p.base_unit)]["content_b64"])
        if current_base != saved_base:
            raise RuntimeError("BASE_UNIT_CHANGED_SNAPSHOT_RESTORE_REFUSED")
        self.p.dropin_root.mkdir(parents=True, exist_ok=True)
        for path in self.p.dropin_root.iterdir():
            if path.is_symlink() or not path.is_file():
                raise ValueError("DROPIN_DIRECTORY_CONTAINS_UNEXPECTED_ENTRY")
            path.unlink()
        for filename in snapshot["directory_entries"]:
            row = snapshot["files"][filename]
            data = base64.b64decode(row["content_b64"])
            if _sha(data) != row["sha256"] or Path(filename).parent != self.p.dropin_root:
                raise ValueError("SNAPSHOT_DROPIN_HASH_OR_PATH_INVALID")
            if row.get("uid") != os.getuid() or row.get("gid") != os.getgid():
                raise ValueError("SNAPSHOT_DROPIN_OWNER_MISMATCH")
            mode = row.get("mode")
            if not isinstance(mode, int) or mode & ~0o777:
                raise ValueError("SNAPSHOT_DROPIN_MODE_INVALID")
            _atomic_bytes(Path(filename), data, mode)
        mutations = ["dropin_snapshot_restored"]
        self._systemctl_mutation("daemon-reload"); mutations.append("user_daemon_reload")
        if restart:
            self._systemctl_mutation("restart"); mutations.append("nova_service_restart")
        service_state = self._systemctl("is-active").strip()
        pollers = self.poller_status()
        return {"pass": service_state == "active" and pollers["poller_count"] == 1,
                "service_state": service_state, "poller_count": pollers["poller_count"],
                "mutations": mutations}

    def _snapshot_by_hash(self, snapshot_hash: str) -> dict[str, Any]:
        snaps = self.p.state_root / "snapshots"
        matches = []
        if snaps.is_dir():
            paths = sorted(snaps.glob("snap_*.json"))
            if len(paths) > 1000:
                raise ValueError("SNAPSHOT_INDEX_BOUND_EXCEEDED")
            for path in paths:
                if path.is_symlink() or not path.is_file():
                    continue
                try:
                    row = json.loads(path.read_text())
                    if row.get("snapshot_hash") == snapshot_hash:
                        matches.append(row)
                except (OSError, ValueError):
                    continue
        if len(matches) != 1:
            raise ValueError("CURRENT_SNAPSHOT_NOT_UNIQUE")
        return matches[0]

    def _shared_dependency(self, release_name: str, expected_shared_hash: str) -> tuple[Path, str]:
        lock_path = self.p.release_root / release_name / "NOVA_SHARED_DEPENDENCIES.json"
        if lock_path.is_symlink() or not lock_path.is_file():
            raise ValueError("DEPENDENCY_LOCK_MISSING")
        raw = lock_path.read_bytes(); lock_hash = _sha(raw)
        lock = json.loads(raw)
        if lock.get("source_release_manifest_sha256") != expected_shared_hash or lock.get("source_release_hash") != expected_shared_hash:
            raise ValueError("SHARED_RELEASE_NOT_PINNED")
        release = str(lock.get("source_release") or "")
        release = _safe_name(release, RELEASE_NAME_RE, "SHARED_RELEASE_NAME_INVALID")
        path = self.p.release_root / release
        checked = _manifest(path, expected_shared_hash)
        if checked["mismatches"] or not checked["present"]:
            raise ValueError("SHARED_RELEASE_INVALID")
        return path, lock_hash

    def _systemctl_mutation(self, action: str) -> str:
        if action == "daemon-reload":
            argv = ["systemctl", "--user", "daemon-reload"]
        elif action in {"restart"}:
            argv = ["systemctl", "--user", action, self.p.service]
        else:
            raise ValueError("SYSTEMCTL_MUTATION_NOT_ALLOWED")
        result = self.runner(argv, capture_output=True, text=True, timeout=60, check=False)
        if result.returncode:
            raise RuntimeError("FIXED_NOVA_SYSTEMCTL_MUTATION_FAILED")
        return result.stdout or ""

    def receipt_read(self, receipt_id: str) -> dict[str, Any]:
        rid = _safe_name(receipt_id, re.compile(r"hcr_[a-f0-9]{32}\Z"), "RECEIPT_ID_INVALID")
        path = self.p.state_root / "receipts" / (rid + ".json")
        if not path.is_file() or path.is_symlink():
            return {"status": "NOT_FOUND", "receipt_id": rid, "read_only": True}
        if path.stat().st_size > 1024 * 1024:
            raise ValueError("RECEIPT_TOO_LARGE")
        return {"status": "FOUND", "receipt": json.loads(path.read_text()), "read_only": True}

    def _systemctl(self, action: str, *args: str) -> str:
        if action not in {"show", "status", "is-active"}:
            raise ValueError("SYSTEMCTL_ACTION_NOT_ALLOWED")
        argv = ["systemctl", "--user", action, self.p.service, *args]
        result = self.runner(argv, capture_output=True, text=True, timeout=15, check=False)
        if result.returncode and action != "status":
            raise RuntimeError("FIXED_NOVA_SYSTEMCTL_READ_FAILED")
        return (result.stdout or "") + (result.stderr or "")

    def _load_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        sid = _safe_name(snapshot_id, re.compile(r"snap_[a-f0-9]{32}\Z"), "SNAPSHOT_ID_INVALID")
        path = self.p.state_root / "snapshots" / (sid + ".json")
        if not path.is_file() or path.is_symlink() or path.stat().st_size > 8 * 1024 * 1024:
            raise ValueError("SNAPSHOT_NOT_FOUND_OR_INVALID")
        row = json.loads(path.read_text())
        if row.get("snapshot_id") != sid or row.get("service") != self.p.service:
            raise ValueError("SNAPSHOT_SCOPE_INVALID")
        return row

    def _consume_approval(self, approval_id: str, operation: str, binding: dict[str, Any]) -> None:
        row, path = self._validate_approval(approval_id, operation, binding)
        row["consumed"] = True
        _atomic_json(path, row, 0o600)

    def _validate_approval(self, approval_id: str, operation: str,
                           binding: dict[str, Any]) -> tuple[dict[str, Any], Path]:
        aid = _safe_name(approval_id, APPROVAL_RE, "APPROVAL_ID_INVALID")
        path = self.p.state_root / "approvals" / (aid + ".json")
        if not path.is_file() or path.is_symlink():
            raise PermissionError("APPROVAL_REQUIRED")
        row = json.loads(path.read_text())
        if (row.get("approved") is not True or row.get("consumed") is True or row.get("operation") != operation
                or row.get("binding") != binding or row.get("binding_hash") != _json_hash(binding)):
            raise PermissionError("APPROVAL_BINDING_MISMATCH_OR_STALE")
        return row, path


class _LocalHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        if not self.server.host_control.p.test_mode:
            if not hasattr(socket, "SO_PEERCRED"):
                self.wfile.write(b'{"error":"LOCAL_PEER_CREDENTIALS_UNAVAILABLE"}\n')
                return
            raw = self.request.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
            _peer_pid, peer_uid, _peer_gid = struct.unpack("3i", raw)
            if peer_uid != os.getuid():
                self.wfile.write(b'{"error":"LOCAL_PEER_UID_REJECTED"}\n')
                return
        line = self.rfile.readline(MAX_REQUEST_BYTES + 1)
        if len(line) > MAX_REQUEST_BYTES:
            self.wfile.write(b'{"error":"REQUEST_TOO_LARGE"}\n')
            return
        try:
            req = json.loads(line)
            if not isinstance(req, dict) or set(req) != {"capability", "arguments"}:
                raise ValueError("REQUEST_SCHEMA_INVALID")
            out = self.server.host_control.invoke(req["capability"], req["arguments"])
            self.wfile.write(json.dumps({"ok": True, "result": out}, sort_keys=True).encode() + b"\n")
        except Exception as exc:
            self.wfile.write(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True).encode() + b"\n")


class LocalServer(socketserver.UnixStreamServer):
    allow_reuse_address = False
    def __init__(self, host_control: HostControl, socket_path: Path = SOCKET_PATH):
        self.host_control = host_control
        if socket_path != SOCKET_PATH and not host_control.p.test_mode:
            raise ValueError("SOCKET_PATH_FIXED")
        socket_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if socket_path.exists() or socket_path.is_symlink():
            raise FileExistsError("HOST_CONTROL_SOCKET_ALREADY_EXISTS")
        super().__init__(str(socket_path), _LocalHandler)
        os.chmod(socket_path, 0o600)


def _safe_tar_member(member: tarfile.TarInfo) -> bool:
    p = PurePosixPath(member.name)
    return bool(p.parts) and bool(member.isfile() or member.isdir()) and not p.is_absolute() and ".." not in p.parts and not member.issym() and not member.islnk()


def _atomic_json(path: Path, value: dict[str, Any], mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_name("." + path.name + ".tmp-" + uuid.uuid4().hex)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2); stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
    os.replace(tmp, path)
    os.chmod(path, mode)


def _atomic_bytes(path: Path, data: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_name("." + path.name + ".tmp-" + uuid.uuid4().hex)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())
    os.replace(tmp, path); os.chmod(path, mode)


def _dropin_content(release: Path, shared: Path) -> bytes:
    worker = release / "scripts/nova/nova_telegram_worker.py"
    if not worker.is_file():
        raise ValueError("NOVA_WORKER_MISSING")
    py_path = f"{release}/scripts/nova:{release}/scripts:{shared}/scripts"
    text = ("[Service]\nExecStart=\n"
            f"ExecStart={PRODUCTION_PYTHON} {worker} --poll\n"
            f"WorkingDirectory=/home/opc/nexus-os-v2-source\n"
            f"Environment=NOVA_CODE_ROOT={release}\n"
            f"Environment=NOVA_REPO_ROOT=/home/opc/nexus-os-v2-source\n"
            f"Environment=NEXUS_REPO_ROOT=/home/opc/nexus-os-v2-source\n"
            f"Environment=PYTHONPATH={py_path}\n"
            f"Environment=NOVA_SHARED_PLATFORM_RELEASE_ROOT={shared}\n")
    return text.encode()


def _snapshot_configuration_hash(snapshot: dict[str, Any]) -> str:
    effective = snapshot.get("effective", {})
    stable_keys = {"FragmentPath", "DropInPaths", "ExecStart", "WorkingDirectory",
                   "Environment", "NOVA_CODE_ROOT", "NOVA_REPO_ROOT", "PYTHONPATH",
                   "NOVA_SHARED_PLATFORM_RELEASE_ROOT"}
    projection = {"service": snapshot.get("service"), "base_unit": snapshot.get("base_unit"),
        "ordered_dropins": snapshot.get("ordered_dropins"),
        "directory_entries": snapshot.get("directory_entries"), "files": snapshot.get("files"),
        "effective": {k: v for k, v in effective.items() if k in stable_keys}}
    return _json_hash(projection)


def _remove_tree(path: Path) -> None:
    if path.is_symlink():
        path.unlink(); return
    if path.is_dir():
        path.chmod(0o700)
        for child in path.iterdir():
            _remove_tree(child)
        path.rmdir()
    elif path.exists():
        path.chmod(0o600); path.unlink()


def _read_config(path: Path) -> dict[str, str]:
    data = path.read_bytes()
    text = data.decode("utf-8")
    if re.search(r"(?im)^\s*Environment=[^\n]*(?:TOKEN|SECRET|PASSWORD|CREDENTIAL|AUTHORIZATION)\s*=", text):
        raise ValueError("INLINE_SECRET_IN_NOVA_UNIT_CONFIG")
    st = path.stat()
    return {"content_b64": base64.b64encode(data).decode(), "sha256": _sha(data),
            "mode": stat.S_IMODE(st.st_mode), "uid": st.st_uid, "gid": st.st_gid}


def _parse_properties(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines():
        if "=" in line:
            k, v = line.split("=", 1); out[k] = v
    return out


def _redact_properties(props: dict[str, str]) -> dict[str, str]:
    out = {}
    for key, value in props.items():
        if key == "Environment":
            safe_values = {"NOVA_CODE_ROOT", "NOVA_REPO_ROOT", "PYTHONPATH", "NOVA_SHARED_PLATFORM_RELEASE_ROOT"}
            rendered = []
            for part in value.split():
                if "=" not in part:
                    continue
                env_key, env_value = part.split("=", 1)
                rendered.append(env_key + "=" + (env_value if env_key in safe_values else "[REDACTED]"))
                if env_key in safe_values:
                    out[env_key] = env_value
            out[key] = " ".join(rendered)
        else:
            out[key] = value
    return out


def _environment_map(value: str) -> dict[str, str]:
    out = {}
    for part in value.split():
        if "=" in part:
            key, val = part.split("=", 1)
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
                out[key] = val
    return out


def _pid(value: str) -> str:
    if not re.fullmatch(r"[1-9][0-9]{0,8}", str(value)):
        raise ValueError("PID_INVALID")
    return str(value)


def _process_start_time(stat_path: Path) -> str | None:
    try:
        raw = stat_path.read_text(encoding="ascii")
        # Fields after the final ')' start at proc stat field 3; starttime is 22.
        tail = raw[raw.rfind(")") + 2:].split()
        ticks = int(tail[19])
        uptime = float(Path("/proc/uptime").read_text(encoding="ascii").split()[0])
        boot_epoch = time.time() - uptime
        return datetime.fromtimestamp(boot_epoch + ticks / os.sysconf("SC_CLK_TCK"), timezone.utc).isoformat()
    except (OSError, ValueError, IndexError, ZeroDivisionError):
        return None


def serve() -> None:
    server = LocalServer(HostControl())
    server.serve_forever()


def invoke_local(request: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(request, dict) or set(request) != {"capability", "arguments"}:
        raise ValueError("REQUEST_SCHEMA_INVALID")
    payload = json.dumps(request, sort_keys=True).encode() + b"\n"
    if len(payload) > MAX_REQUEST_BYTES:
        raise ValueError("REQUEST_TOO_LARGE")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(10)
        client.connect(str(SOCKET_PATH))
        client.sendall(payload)
        data = b""
        while not data.endswith(b"\n") and len(data) <= MAX_REQUEST_BYTES:
            chunk = client.recv(65536)
            if not chunk:
                break
            data += chunk
    if len(data) > MAX_REQUEST_BYTES:
        raise ValueError("RESPONSE_TOO_LARGE")
    response = json.loads(data.decode("utf-8"))
    if not isinstance(response, dict):
        raise ValueError("RESPONSE_SCHEMA_INVALID")
    return response


if __name__ == "__main__":
    if sys.argv[1:] == ["--invoke"]:
        try:
            print(json.dumps(invoke_local(json.load(sys.stdin)), sort_keys=True))
        except Exception as exc:
            print(json.dumps({"ok": False, "error": type(exc).__name__}, sort_keys=True))
            raise SystemExit(2)
    elif not sys.argv[1:]:
        serve()
    else:
        raise SystemExit("ONLY_TYPED_LOCAL_INVOKE_OR_SERVICE_MODE")
