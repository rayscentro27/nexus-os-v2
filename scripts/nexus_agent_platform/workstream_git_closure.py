#!/usr/bin/env python3
"""Workstream-scoped Git closure guard for Nexus engineering tasks.

Read-only by default. Commit and push are separate explicit commands. The
tool never uses broad staging and rejects runtime, cache, local-profile, and
credential-adjacent paths by default.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(os.environ.get("NEXUS_GIT_ROOT", Path(__file__).resolve().parents[2])).resolve()
MANIFEST = ROOT / "configs" / "nexus_git_workstreams.json"


def run(*args: str, cwd: Path = ROOT, check: bool = True) -> str:
    p = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and p.returncode:
        raise RuntimeError(f"command failed ({p.returncode}): {' '.join(args)}\n{p.stderr.strip()}")
    return p.stdout


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text())


def status_paths() -> list[str]:
    raw = subprocess.check_output(["git", "status", "--porcelain=v1", "-z"], cwd=ROOT)
    paths = []
    for item in raw.decode().split("\0"):
        if item:
            paths.append(item[3:])
    return sorted(set(paths))


def expand(path: str) -> list[str]:
    candidate = ROOT / path
    if candidate.is_dir():
        tracked = run("git", "diff", "--name-only", "--", path, check=False).splitlines()
        untracked = run("git", "ls-files", "--others", "--exclude-standard", "--", path, check=False).splitlines()
        return sorted(set(tracked + untracked))
    return [path]


def forbidden(path: str, manifest: dict) -> str | None:
    p = path.replace(os.sep, "/")
    base = Path(p).name
    for pattern in manifest["global_forbidden"]:
        if pattern.startswith("**/"):
            if fnmatch.fnmatch(p, pattern) or fnmatch.fnmatch(p, pattern[3:]):
                return pattern
        elif pattern.endswith("/") and (p == pattern[:-1] or p.startswith(pattern)):
            return pattern
        elif fnmatch.fnmatch(p, pattern) or fnmatch.fnmatch(base, pattern):
            return pattern
    return None


def owns(path: str, spec: dict) -> bool:
    p = path.replace(os.sep, "/")
    for prefix in spec["owned_paths"]:
        if "*" in prefix and fnmatch.fnmatch(p, prefix):
            return True
        if p == prefix.rstrip("/") or p.startswith(prefix):
            return True
    for prefix in spec.get("allowed_report_paths", []):
        if p.startswith(prefix):
            return True
    return False


def candidate_report(workstream: str) -> dict:
    manifest = load_manifest()
    if workstream not in manifest["workstreams"]:
        raise ValueError(f"unknown workstream: {workstream}")
    spec = manifest["workstreams"][workstream]
    raw = status_paths()
    files = sorted({f for p in raw for f in expand(p)})
    owned, blocked, forbidden_owned, other = [], [], [], []
    for path in files:
        reason = forbidden(path, manifest)
        if reason:
            blocked.append({"file": path, "reason": reason})
            if owns(path, spec):
                forbidden_owned.append({"file": path, "reason": reason})
        elif owns(path, spec):
            owned.append(path)
        else:
            other.append(path)
    ahead = run("git", "rev-list", "--count", "origin/" + current_branch() + "..HEAD", check=False).strip()
    behind = run("git", "rev-list", "--count", "HEAD..origin/" + current_branch(), check=False).strip()
    return {"workstream": workstream, "owned_candidates": owned, "forbidden": blocked,
            "forbidden_owned": forbidden_owned,
            "other_dirty_files": other, "branch": current_branch(), "ahead": int(ahead or 0),
            "behind": int(behind or 0), "commit_message": spec["commit_message"]}


def current_branch() -> str:
    return run("git", "branch", "--show-current").strip()


def print_report(report: dict) -> None:
    print(json.dumps(report, indent=2))


def assert_clean_candidate(report: dict) -> None:
    if report["forbidden_owned"]:
        raise RuntimeError("COMMIT_BLOCKED_FORBIDDEN_PATHS\n" + json.dumps(report["forbidden_owned"], indent=2))
    if not report["owned_candidates"]:
        raise RuntimeError("NO_WORKSTREAM_FILES_TO_COMMIT")


def write_receipt(workstream: str, report: dict, commit_sha: str, push_status: str = "NOT_ATTEMPTED") -> Path:
    out = ROOT / "reports" / "repository" / "git_closure"
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out / f"{workstream}_{stamp}.json"
    path.write_text(json.dumps({"workstream": workstream, "timestamp": stamp,
                                "branch": report["branch"], "base_sha": run("git", "rev-parse", "HEAD"),
                                "commit_sha": commit_sha, "files": report["owned_candidates"],
                                "tests": [], "push_status": push_status,
                                "remote_sha": None, "deployment_status": "NOT_RECORDED",
                                "reason_if_not_pushed": None}, indent=2) + "\n")
    return path


def commit(workstream: str) -> None:
    report = candidate_report(workstream)
    assert_clean_candidate(report)
    run("git", "diff", "--check", "--", *report["owned_candidates"])
    print("PROPOSED_STAGED_FILES=" + json.dumps(report["owned_candidates"]))
    run("git", "add", "--", *report["owned_candidates"])
    staged = run("git", "diff", "--cached", "--name-only").splitlines()
    if staged != report["owned_candidates"]:
        raise RuntimeError("STAGED_SET_MISMATCH")
    run("git", "diff", "--cached", "--check")
    run("git", "commit", "-m", report["commit_message"])
    sha = run("git", "rev-parse", "HEAD").strip()
    receipt = write_receipt(workstream, report, sha)
    print(json.dumps({"commit_sha": sha, "receipt": str(receipt.relative_to(ROOT))}, indent=2))


def push(workstream: str, remote: str = "origin") -> None:
    report = candidate_report(workstream)
    run("git", "fetch", remote)
    branch = current_branch()
    upstream = f"{remote}/{branch}"
    ahead = int(run("git", "rev-list", "--count", upstream + "..HEAD").strip() or 0)
    behind = int(run("git", "rev-list", "--count", "HEAD.." + upstream).strip() or 0)
    if behind or not ahead:
        raise RuntimeError("PUSH_BLOCKED_NON_FAST_FORWARD_OR_NO_NEW_COMMIT")
    for sha in run("git", "rev-list", upstream + "..HEAD").splitlines():
        changed = run("git", "diff-tree", "--no-commit-id", "--name-only", "-r", sha).splitlines()
        if any(not owns(path, load_manifest()["workstreams"][workstream]) or forbidden(path, load_manifest()) for path in changed):
            raise RuntimeError("PUSH_BLOCKED_UNRELATED_HISTORY")
    run("git", "push", remote, f"HEAD:{branch}")
    print(json.dumps({"push_status": "PUSHED", "remote_sha": run("git", "rev-parse", f"{remote}/{branch}").strip()}, indent=2))


def isolate(workstream: str, destination: str) -> None:
    report = candidate_report(workstream)
    if report["forbidden_owned"]:
        raise RuntimeError("ISOLATE_BLOCKED_FORBIDDEN_PATHS")
    if Path(destination).exists():
        raise RuntimeError("ISOLATE_DESTINATION_EXISTS")
    branch = report["branch"]
    run("git", "worktree", "add", "--detach", destination, f"origin/{branch}")
    dest = Path(destination)
    for path in report["owned_candidates"]:
        source = ROOT / path
        target = dest / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_file():
            shutil.copy2(source, target)
    print(json.dumps({"worktree": destination, "base": run("git", "-C", destination, "rev-parse", "HEAD").strip(), "files": report["owned_candidates"]}, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("inspect", "plan", "commit", "push"):
        p = sub.add_parser(command); p.add_argument("workstream", choices=sorted(load_manifest()["workstreams"]))
    p = sub.add_parser("isolate"); p.add_argument("workstream", choices=sorted(load_manifest()["workstreams"])); p.add_argument("destination")
    args = parser.parse_args(argv)
    try:
        if args.command in ("inspect", "plan"):
            print_report(candidate_report(args.workstream)); return 0
        if args.command == "commit": commit(args.workstream); return 0
        if args.command == "push": push(args.workstream); return 0
        isolate(args.workstream, args.destination); return 0
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr); return 2


if __name__ == "__main__":
    raise SystemExit(main())
