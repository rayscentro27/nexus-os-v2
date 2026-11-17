#!/usr/bin/env python3
"""Bounded Git wrapper and staged-index guard for Nexus development."""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "configs/nexus_repository_policy.yaml"


def policy():
    import yaml
    return yaml.safe_load(POLICY_PATH.read_text())


def git(*args, check=True, text=True):
    return subprocess.run(["git", *args], cwd=ROOT, check=check, capture_output=True, text=text)


def classify(path: str, p=None) -> str:
    p = p or policy()
    path = path.replace("\\", "/").removeprefix("./")
    if Path(path).name in {".env.example", ".env.sample", ".env.template"}:
        return "CONFIGURATION"
    for rule in p["path_classes"]:
        if any(fnmatch.fnmatchcase(path, pattern) for pattern in rule["patterns"]):
            return rule["name"]
    return "UNKNOWN"


def subsystem(path: str, p=None) -> str:
    p = p or policy()
    normalized = path.replace("\\", "/").removeprefix("./")
    for pattern, name in p.get("subsystem_overrides", {}).items():
        if fnmatch.fnmatchcase(normalized, pattern):
            return name
    matches = [(len(root), name) for root, name in p["subsystem_roots"].items()
               if normalized == root or normalized.startswith(root + "/")]
    if matches:
        return max(matches)[1]
    return normalized.split("/", 1)[0] or "ROOT"


BLOCKED_GIT = {"clean", "reset", "restore", "rm"}


def check_git_argv(args: list[str], owner_approved=False):
    if not args:
        return False, "missing git command"
    command = args[0]
    if command in BLOCKED_GIT:
        return (True, "owner approval required") if owner_approved else (False, f"blocked dangerous git command: {command}")
    if command == "checkout" and ("--" in args[1:] or any(x in {".", "-A", "--all"} for x in args[1:])):
        return False, f"blocked broad {command} operation"
    if command == "push" and any(x in {"-f", "--force", "--mirror", "--force-with-lease"} for x in args[1:]):
        return False, "force push or mirror push blocked"
    if command == "add":
        paths = [x for x in args[1:] if not x.startswith("-")]
        if any(x in {".", ".."} for x in paths) or any(x in {"-A", "--all", "-u", "--update"} for x in args[1:]):
            return False, "git add requires explicit scoped paths; broad add is blocked"
        if not paths:
            return False, "git add requires explicit paths"
    if command == "commit" and any(x in {"-a", "--all"} for x in args[1:]):
        return False, "git commit -a is blocked; stage reviewed paths explicitly"
    if command == "commit" and any(x in {"--amend", "--no-verify"} for x in args[1:]):
        return False, "commit amend and hook bypass are blocked"
    return True, "allowed"


def checkpoint(target: str, paths: list[str]):
    branch = git("branch", "--show-current").stdout.strip()
    head = git("rev-parse", "HEAD").stdout.strip()
    home = Path(os.environ.get("NEXUS_GIT_GOVERNOR_HOME", Path.home() / ".nexus/state/repo_guard"))
    home.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    record = {"timestamp": stamp, "branch": branch, "head": head,
              "target_subsystem": target, "planned_paths": paths}
    out = home / f"checkpoint-{stamp}.json"
    out.write_text(json.dumps(record, indent=2) + "\n")
    return out


def validate_paths(paths: list[str], deleted: list[str] | None = None, p=None):
    p = p or policy()
    deleted = deleted or []
    errors = []
    if len(paths) > p["max_commit_files"]:
        errors.append(f"staged file limit exceeded ({len(paths)} > {p['max_commit_files']})")
    subsystems = {subsystem(x, p) for x in paths}
    if len(subsystems) > p["max_commit_subsystems"]:
        errors.append("cross-subsystem commit blocked: " + ", ".join(sorted(subsystems)))
    for path in paths:
        kind = classify(path, p)
        if kind in p["blocked_commit_classes"]:
            errors.append(f"blocked {kind} path: {path}")
    if len(deleted) > p["mass_delete_limit"]:
        errors.append(f"mass deletion blocked ({len(deleted)} staged deletions)")
    return errors


def staged_paths():
    out = git("diff", "--cached", "--name-only", "-z", text=False).stdout
    return [x.decode() for x in out.split(b"\0") if x]


def precommit():
    paths = staged_paths()
    if not paths:
        return 0
    deleted = [p for p in paths if git("diff", "--cached", "--diff-filter=D", "--name-only", "--", p, check=False).stdout.strip()]
    p = policy()
    errors = validate_paths(paths, deleted, p)
    max_size = int(p["max_staged_file_bytes"])
    for path in paths:
        spec = f":{path}"
        blob = git("show", spec, check=False, text=False)
        if blob.returncode == 0:
            content = blob.stdout
            if len(content) > max_size:
                errors.append(f"large staged artifact blocked ({len(content)} bytes): {path}")
            if re.search(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", content):
                errors.append(f"private key material blocked: {path}")
            if re.search(rb"(?i)(api[_-]?key|secret|access[_-]?token|password)\s*[:=]\s*['\"][^'\"]{16,}['\"]", content):
                errors.append(f"possible embedded secret blocked: {path}")
    if errors:
        print("Nexus repository guard rejected this commit:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"Nexus repository guard: {len(paths)} staged paths validated.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    check = sub.add_parser("check-command"); check.add_argument("command", nargs=argparse.REMAINDER)
    add = sub.add_parser("add"); add.add_argument("paths", nargs="+")
    commit = sub.add_parser("commit"); commit.add_argument("-m", "--message", required=True); commit.add_argument("--owner-approved", action="store_true")
    cp = sub.add_parser("checkpoint"); cp.add_argument("subsystem"); cp.add_argument("paths", nargs="+")
    sub.add_parser("pre-commit")
    args = parser.parse_args(argv)
    if args.action == "check-command":
        ok, message = check_git_argv(args.command)
        print(message)
        return 0 if ok else 2
    if args.action == "pre-commit": return precommit()
    if args.action == "checkpoint":
        approved = [str(Path(x).as_posix()) for x in args.paths]
        if any(x in {".", ".."} or x.startswith("/") for x in approved):
            print("checkpoint paths must be explicit repository-relative files", file=sys.stderr); return 2
        out = checkpoint(args.subsystem, approved)
        print(out); return 0
    if args.action == "add":
        ok, message = check_git_argv(["add", *args.paths])
        if not ok: print(message, file=sys.stderr); return 2
        for path in args.paths:
            if Path(path).is_absolute() or ".." in Path(path).parts or any(c in path for c in "*?[]"):
                print(f"path must be an explicit repository-relative file: {path}", file=sys.stderr); return 2
            candidate = ROOT / path
            tracked = git("ls-files", "--error-unmatch", "--", path, check=False).returncode == 0
            if candidate.is_dir():
                print(f"directory-wide staging blocked: {path}", file=sys.stderr); return 2
            if not candidate.exists() and not tracked:
                print(f"path does not exist and is not tracked: {path}", file=sys.stderr); return 2
        subsystems = {subsystem(x) for x in args.paths}
        if len(subsystems) > policy()["max_commit_subsystems"]:
            print("cross-subsystem staging blocked: " + ", ".join(sorted(subsystems)), file=sys.stderr); return 2
        checkpoint(",".join(subsystems), args.paths)
        git("add", "--", *args.paths)
        print("staged explicit paths: " + ", ".join(args.paths)); return 0
    if args.action == "commit":
        staged = staged_paths()
        if not staged: print("no staged paths", file=sys.stderr); return 2
        errors = validate_paths(staged)
        if errors: print("\n".join(errors), file=sys.stderr); return 2
        if args.owner_approved:
            if not sys.stdin.isatty(): print("owner approval requires an interactive terminal", file=sys.stderr); return 2
            if input("Owner approval: commit currently reviewed staged paths? [y/N] ").strip().lower() != "y": return 2
        checkpoint(",".join(sorted({subsystem(x) for x in staged})), staged)
        return git("commit", "-m", args.message).returncode
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
