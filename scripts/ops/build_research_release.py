#!/usr/bin/env python3
"""Build an immutable Research release and close its entrypoint import graph."""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from validate_nova_release import module_file, reachable_missing_imports  # noqa: E402

ENTRYPOINTS = [
    "scripts/nexus_agent_platform/dispatcher_once.py",
    "scripts/nexus_agent_platform/job_worker_once.py",
    "scripts/research/run_dispatched_research_job.py",
]


def make_writable(root: Path) -> None:
    for path in root.rglob("*"):
        if path.is_symlink():
            continue
        mode = path.stat().st_mode
        if path.is_dir(): path.chmod(mode | 0o700)
        elif path.is_file(): path.chmod(mode | 0o600)
    root.chmod(root.stat().st_mode | 0o700)


def add_dependency(source_root: Path, release_root: Path, module: str) -> str:
    source = module_file(source_root, module)
    if source is None:
        raise RuntimeError(f"local import is unresolved in canonical source: {module}")
    relative = source.relative_to(source_root)
    target = release_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return relative.as_posix()


def hash_release(release_root: Path) -> str:
    files: list[Path] = []
    for path in release_root.rglob("*"):
        if path.is_file() and not path.is_symlink() and "__pycache__" not in path.parts:
            relative = path.relative_to(release_root).as_posix()
            if relative not in {"RELEASE_MANIFEST.sha256", "RELEASE_SOURCE_HASH"}:
                files.append(path)
    runtime_manifest = release_root / "RESEARCH_RUNTIME_RELEASE_MANIFEST.sha256"
    lines = [f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path}" for path in sorted(files)]
    runtime_manifest.write_text("\n".join(lines) + "\n")
    relative_lines = [f"{hashlib.sha256(path.read_bytes()).hexdigest()}  ./{path.relative_to(release_root).as_posix()}"
                      for path in sorted(files + [runtime_manifest])]
    manifest = release_root / "RELEASE_MANIFEST.sha256"
    manifest.write_text("\n".join(relative_lines) + "\n")
    source_hash = hashlib.sha256(manifest.read_bytes()).hexdigest()
    (release_root / "RELEASE_SOURCE_HASH").write_text(source_hash + "\n")
    return source_hash


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--base-release", type=Path, required=True)
    parser.add_argument("--output-release", type=Path, required=True)
    args = parser.parse_args()
    source_root = args.source_root.resolve()
    base = args.base_release.resolve()
    output = args.output_release.expanduser().absolute()
    if not base.is_dir() or not source_root.is_dir() or output.exists():
        raise SystemExit("BUILD_INPUT_INVALID_OR_OUTPUT_EXISTS")

    shutil.copytree(base, output, symlinks=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    make_writable(output)
    added: dict[str, str] = {}
    for _ in range(20):
        missing = reachable_missing_imports(output, ENTRYPOINTS, source_root)
        if not missing:
            break
        modules = sorted({item.split(": ", 1)[1] for item in missing})
        progress = False
        for module in modules:
            source_path = module_file(source_root, module)
            candidate_path = module_file(output, module)
            if source_path is None:
                raise SystemExit(f"UNRESOLVED_CANONICAL_LOCAL_IMPORT={module}")
            if candidate_path is None:
                relative = add_dependency(source_root, output, module)
                digest = hashlib.sha256((output / relative).read_bytes()).hexdigest()
                added[module] = f"{relative} sha256={digest}"
                print(f"PACKAGED_MODULE={module} PATH={relative} SHA256={digest}", flush=True)
                progress = True
        if not progress:
            details = "\n".join(sorted(missing))
            raise SystemExit(f"DEPENDENCY_CLOSURE_STALLED\n{details}")
    else:
        raise SystemExit("DEPENDENCY_CLOSURE_ITERATION_LIMIT")

    wrapper = output / "scripts/ops/run_with_canonical_runtime_env.sh"
    content = wrapper.read_text()
    old_release = 'RELEASE="/Users/raymonddavis/.nexus/releases/nexus-research-runtime-plan-assigned-work-20261019-r3"'
    if old_release in content:
        content = content.replace(old_release, 'SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"\nRELEASE="$(cd "$SCRIPT_DIR/../.." && pwd)"')
    elif 'BASH_SOURCE[0]' in content:
        content = content.replace('$(dirname "${BASH_SOURCE[0]}")', '$(dirname "$0")')
    if "plan-assigned-work-20261019-r3" in content:
        raise SystemExit("CANDIDATE_WRAPPER_STILL_REFERENCES_ACTIVE_R3")
    wrapper.write_text(content)
    wrapper.chmod(wrapper.stat().st_mode | 0o111)
    health = output / "scripts/nexus_agent_platform/job_health.py"
    health_text = health.read_text()
    old_signature = 'def persist_snapshot(path: Path = ROOT / "data/runtime/durable_job_health_latest.json") -> dict:'
    new_signature = 'def persist_snapshot(path: Path | None = None) -> dict:'
    if old_signature in health_text:
        health_text = health_text.replace(old_signature, new_signature)
        health_text = health_text.replace(
            '    value=snapshot(); path.parent.mkdir(parents=True,exist_ok=True)',
            '    value=snapshot()\n    path = path or Path(os.environ.get("NEXUS_RESEARCH_HEALTH_PATH", ROOT / "data/runtime/durable_job_health_latest.json"))\n    path.parent.mkdir(parents=True,exist_ok=True)',
        )
    elif new_signature not in health_text:
        raise SystemExit("UNEXPECTED_JOB_HEALTH_INTERFACE")
    health.write_text(health_text)
    if 'NEXUS_RESEARCH_HEALTH_PATH=' not in content:
        content = wrapper.read_text().replace(
            'export NEXUS_REPO_ROOT="/Users/raymonddavis/nexus-os-v2-canonical"',
            'export NEXUS_REPO_ROOT="/Users/raymonddavis/nexus-os-v2-canonical"\nexport NEXUS_RESEARCH_HEALTH_PATH="$NEXUS_REPO_ROOT/reports/runtime/durable_job_health_latest.json"',
        )
        wrapper.write_text(content)
        wrapper.chmod(wrapper.stat().st_mode | 0o111)
    source_hash = hash_release(output)
    for path in sorted(output.rglob("*"), reverse=True):
        if path.is_symlink(): continue
        if path.is_dir(): path.chmod(0o555)
        elif path.is_file(): path.chmod(0o555 if path.stat().st_mode & 0o111 else 0o444)
    output.chmod(0o555)
    print(f"OUTPUT_RELEASE={output}")
    print(f"ADDED_DEPENDENCY_COUNT={len(added)}")
    print(f"RELEASE_SOURCE_HASH={source_hash}")
    print("ACTIVE_R3_MUTATED=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
