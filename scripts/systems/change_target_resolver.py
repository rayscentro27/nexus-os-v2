#!/usr/bin/env python3
"""Resolve an authorized Nexus change target from the Living Manifest.

This is a read-only gate. It never edits files, services, or agent config.
Agents should resolve a target before edits, retain the emitted plan, and run
--post-change against that plan before validation/restart.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import stat
import subprocess
import sys
import sqlite3
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/systems/NEXUS_LIVING_MANIFEST.v1.json"


def _expand(value: str) -> str:
    return value.replace("$REPO_ROOT", str(ROOT)).replace("${REPO_ROOT}", str(ROOT)).replace("$NEXUS_HOME", str(Path.home() / ".nexus")).replace("${NEXUS_HOME}", str(Path.home() / ".nexus"))


def _canonical(value: str) -> str:
    p = Path(os.path.expanduser(_expand(value)))
    if not p.is_absolute():
        p = ROOT / p
    return str(p.resolve(strict=False))


def _matches(path: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        resolved = _canonical(pattern)
        if fnmatch.fnmatchcase(path, resolved):
            return True
        # A registered directory prefix intentionally covers its descendants.
        if pattern.endswith("/**"):
            prefix = _canonical(pattern[:-3]).rstrip(os.sep) + os.sep
            if path.startswith(prefix):
                return True
    return False


def _git_status() -> set[str] | None:
    try:
        # The current repository contains a large pre-existing untracked
        # virtualenv tree; allow Git to enumerate it instead of silently
        # converting a slow snapshot into an unverified drift check.
        # Directory-level untracked paths keep the snapshot useful while avoiding
        # expensive enumeration of every file in large existing artifact trees.
        # The fingerprint records directory metadata; tracked file contents are
        # separately protected by SHA-256 below.
        run = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=normal"], capture_output=True, text=True, timeout=5, check=True)
        out: set[str] = set()
        for line in run.stdout.splitlines():
            if len(line) >= 4:
                out.add(line[3:].split(" -> ")[-1])
        return out
    except (OSError, subprocess.SubprocessError):
        return None


def _tracked_status() -> set[str] | None:
    try:
        run = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=no"], capture_output=True, text=True, timeout=60, check=True)
        return {line[3:].split(" -> ")[-1] for line in run.stdout.splitlines() if len(line) >= 4}
    except (OSError, subprocess.SubprocessError):
        return None


def _workspace_fingerprint(paths: set[str] | None, authorized: set[str]) -> str | None:
    if paths is None:
        return None
    digest = hashlib.sha256()
    for relative in sorted(paths):
        absolute = os.path.abspath(os.path.join(ROOT, relative))
        if absolute in authorized:
            continue
        try:
            info = os.stat(absolute, follow_symlinks=False)
            marker = f"{relative}\0{info.st_size}\0{info.st_mtime_ns}\0{info.st_mode}\0{info.st_ino}\n"
        except OSError:
            marker = f"{relative}\0MISSING\n"
        digest.update(marker.encode())
    return digest.hexdigest()


def _workspace_path_fingerprint(paths: set[str] | None, authorized: set[str]) -> str | None:
    if paths is None:
        return None
    digest = hashlib.sha256()
    for relative in sorted(paths):
        if os.path.abspath(os.path.join(ROOT, relative)) not in authorized:
            digest.update(relative.encode())
            digest.update(b"\n")
    return digest.hexdigest()


def _sha(path: str) -> str | None:
    p = Path(path)
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _mutable_state_assets(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    assets: dict[str, dict[str, Any]] = {}
    for item in manifest.get("mutable_runtime_state_assets", []):
        if not isinstance(item, dict) or not item.get("path"):
            continue
        path = _canonical(str(item["path"]))
        assets[path] = item
    return assets


def _path_identity(path: str) -> dict[str, Any]:
    p = Path(path)
    try:
        info = p.lstat()
    except OSError:
        return {"exists": False, "path": path}
    return {"exists": True, "path": str(p.resolve(strict=False)), "is_symlink": p.is_symlink(),
            "device": info.st_dev, "inode": info.st_ino, "file_type": stat.S_IFMT(info.st_mode)}


def _sqlite_integrity(path: str) -> str:
    """Read-only SQLite integrity probe; never creates or mutates the database."""
    try:
        uri = Path(path).resolve().as_uri() + "?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=2) as con:
            con.execute("PRAGMA busy_timeout=2000")
            row = con.execute("PRAGMA quick_check").fetchone()
        return "PASS" if row and row[0] == "ok" else "FAIL"
    except (OSError, sqlite3.Error, ValueError):
        return "FAIL"


def _concrete_denied_paths(patterns: list[str]) -> list[str]:
    """Resolve explicit file denies; prose policies are retained separately."""
    result: list[str] = []
    for pattern in patterns:
        expanded = _expand(str(pattern))
        if not expanded.startswith(("/", "~")) or any(ch in expanded for ch in "*?[]"):
            continue
        result.append(_canonical(expanded))
    return sorted(set(result))


def resolve_target(manifest: dict[str, Any], component: str, objective: str, requested_files: list[str]) -> dict[str, Any]:
    registry = manifest.get("change_target_registry", {})
    entry = registry.get("components", {}).get(component)
    if not entry:
        raise ValueError("COMPONENT_NOT_REGISTERED")
    if not objective.strip():
        raise ValueError("CHANGE_OBJECTIVE_REQUIRED")
    if not requested_files:
        raise ValueError("BOUNDED_FILE_SCOPE_REQUIRED")
    # The manifest uses `authoritative_files` as the human-readable contract;
    # accept the earlier prototype key as a compatibility alias.
    allowed = entry.get("authoritative_files", entry.get("authoritative_file_patterns", []))
    denied = entry.get("do_not_patch_paths", []) + entry.get("historical_only_paths", []) + registry.get("global_do_not_patch_paths", [])
    files = [_canonical(p) for p in requested_files]
    rejected = [p for p in files if _matches(p, denied) or not _matches(p, allowed)]
    if rejected:
        raise ValueError("OUT_OF_AUTHORITY_SCOPE:" + ",".join(rejected))
    workspace_status = _git_status()
    dependency_files = [_canonical(p) for p in entry.get("allowed_dependency_files", [])]
    protected_files = _concrete_denied_paths(denied)
    mutable_assets = _mutable_state_assets(manifest)
    mutable_paths = set(mutable_assets)
    mutable_paths_in_scope = sorted(p for p in protected_files if p in mutable_paths)
    protected_files = [p for p in protected_files if p not in mutable_paths]
    authorized = set(files) | set(dependency_files)
    return {
        "schema_version": "nexus.change-scope.v2",
        "scope_mode": "SCOPED_TARGETS",
        "component": component,
        "objective": objective.strip(),
        "target_confirmation": "PASS",
        "authority_check": "PASS",
        "authoritative_runtime": entry.get("authoritative_runtime"),
        "authoritative_database": entry.get("authoritative_database"),
        "authoritative_service": entry.get("authoritative_service"),
        "authoritative_scheduler": entry.get("authoritative_scheduler"),
        "authoritative_mcp": entry.get("authoritative_mcp"),
        "authorized_files": files,
        "allowed_dependency_files": dependency_files,
        "baseline_sha256": {p: _sha(p) for p in files},
        "allowed_dependency_sha256": {p: _sha(p) for p in dependency_files},
        "prohibited_file_hashes": {p: _sha(p) for p in protected_files},
        "mutable_runtime_state": {p: {"identity": _path_identity(p),
            "integrity": _sqlite_integrity(p) if mutable_assets[p].get("integrity_check") == "sqlite_quick_check" else None,
            "classification": mutable_assets[p].get("classification", "EXPECTED_MUTABLE_RUNTIME_STATE")}
            for p in mutable_paths_in_scope},
        "prohibited_path_patterns": denied,
        "workspace_status_before_count": len(workspace_status or []),
        "workspace_status_before_paths": sorted(workspace_status or []),
        "workspace_status_available": workspace_status is not None,
        "rollback_reference": entry.get("rollback_reference"),
    }


def post_change_check(plan: dict[str, Any]) -> dict[str, Any]:
    authorized = set(plan.get("authorized_files", []))
    current = {p: _sha(p) for p in authorized}
    target_before = plan.get("baseline_sha256", {})
    target_changed = sorted(p for p in plan.get("authorized_files", []) if current.get(p) != target_before.get(p))
    missing_targets = sorted(p for p in plan.get("authorized_files", []) if target_before.get(p) is not None and current.get(p) is None)
    dependency_before = plan.get("allowed_dependency_sha256", {})
    dependency_now = {p: _sha(p) for p in plan.get("allowed_dependency_files", [])}
    dependency_changed = sorted(p for p in dependency_now if dependency_now[p] != dependency_before.get(p))

    prohibited_before = plan.get("prohibited_file_hashes", {})
    prohibited_changed = sorted(p for p, old in prohibited_before.items() if _sha(p) != old)
    mutable_state = plan.get("mutable_runtime_state", {})
    mutable_state_failures: list[str] = []
    mutable_state_observed: dict[str, Any] = {}
    for path, baseline in mutable_state.items():
        before_identity = baseline.get("identity", {})
        after_identity = _path_identity(path)
        integrity = _sqlite_integrity(path) if baseline.get("integrity") is not None else None
        mutable_state_observed[path] = {"identity": after_identity, "integrity": integrity,
                                        "content_hash_checked": False}
        if not after_identity.get("exists"):
            mutable_state_failures.append("MUTABLE_STATE_MISSING:" + path)
        elif (before_identity.get("path") != after_identity.get("path")
              or before_identity.get("is_symlink") != after_identity.get("is_symlink")
              or before_identity.get("device") != after_identity.get("device")
              or before_identity.get("inode") != after_identity.get("inode")
              or before_identity.get("file_type") != after_identity.get("file_type")):
            mutable_state_failures.append("MUTABLE_STATE_REPLACED_OR_REDIRECTED:" + path)
        if integrity == "FAIL":
            mutable_state_failures.append("MUTABLE_STATE_INTEGRITY_FAILED:" + path)
    # For legacy plans, don't reinterpret the old workspace-wide fingerprint as
    # a blocking condition. Exact authorized-target checks still apply.
    after = _git_status() if plan.get("scope_mode") == "SCOPED_TARGETS" else None
    unrelated: dict[str, Any] = {"classification": "INFORMATIONAL_NONBLOCKING", "status": "UNAVAILABLE"}
    if after is not None:
        before_paths = set(plan.get("workspace_status_before_paths", []))
        comparable = plan.get("scope_mode") == "SCOPED_TARGETS" and plan.get("workspace_status_available") is True
        changed_paths = (after ^ before_paths) if comparable else set()
        denied_patterns = plan.get("prohibited_path_patterns", [])
        newly_prohibited: list[str] = []
        for relative in changed_paths:
            absolute = _canonical(relative)
            if _matches(absolute, denied_patterns) and absolute not in mutable_state:
                newly_prohibited.append(absolute)
        prohibited_changed.extend(newly_prohibited)
        unrelated_paths = sorted(
            relative for relative in changed_paths
            if _canonical(relative) not in authorized
            and not _matches(_canonical(relative), denied_patterns)
        )
        unrelated = {"classification": "INFORMATIONAL_NONBLOCKING",
                     "status": "OBSERVED" if comparable else "BASELINE_UNAVAILABLE",
                     "changed_path_count": len(unrelated_paths) if comparable else None,
                     "sample": unrelated_paths[:10] if comparable else []}
    hard_failures = sorted(set(prohibited_changed + mutable_state_failures + ["AUTHORIZED_TARGET_MISSING:" + p for p in missing_targets]))
    return {
        "post_change_drift_check": "PASS" if not hard_failures else "FAIL",
        "drift_classification": "PROHIBITED_TARGET_DRIFT" if prohibited_changed or mutable_state_failures else ("AUTHORIZED_TARGET_DRIFT" if target_changed else "UNRELATED_WORKSPACE_DRIFT" if unrelated.get("changed_path_count", 0) else "NO_SCOPED_DRIFT"),
        "authorized_target_drift": target_changed,
        "allowed_dependency_drift": dependency_changed,
        "prohibited_target_drift": sorted(set(prohibited_changed)),
        "mutable_runtime_state": mutable_state_observed,
        "mutable_runtime_state_failures": mutable_state_failures,
        "unrelated_workspace_drift": unrelated,
        "authorized_file_hashes": current,
        "authorized_files_changed": target_changed,
        "new_workspace_changes_outside_scope": sorted(set(prohibited_changed)),
        "workspace_status_available": after is not None and bool(plan.get("workspace_status_available")),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("component", nargs="?")
    parser.add_argument("--objective")
    parser.add_argument("--file", action="append", default=[])
    parser.add_argument("--output", type=Path, help="optional JSON scope plan path")
    parser.add_argument("--post-change", type=Path, help="check a previously emitted plan")
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        if args.post_change:
            result = post_change_check(json.loads(args.post_change.read_text(encoding="utf-8")))
        else:
            if not args.component:
                raise ValueError("COMPONENT_REQUIRED")
            result = resolve_target(manifest, args.component, args.objective or "", args.file)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        # Keep the plan file complete for the post-change comparison while
        # keeping terminal output bounded even in a historically dirty repo.
        display = dict(result)
        for key in ("workspace_status_before", "new_workspace_changes_outside_scope"):
            if key in display:
                values = display.pop(key)
                display[key + "_count"] = len(values)
                if values:
                    display[key + "_sample"] = values[:20]
        print(json.dumps(display, indent=2, sort_keys=True))
        return 0 if result.get("post_change_drift_check", "PASS") == "PASS" else 2
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "DENIED", "reason": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
