#!/usr/bin/env python3
"""Build an immutable Nexus MCP release from canonical runtime sources."""
from __future__ import annotations

import argparse
import ast
import hashlib
import plistlib
import re
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from validate_nova_release import imported_local_names, module_file  # noqa: E402

MCP_ENTRYPOINT = "nexus_mcp.http_server"
RESEARCH_WORKER_ENTRYPOINT = "nexus_agent_platform.job_worker_once"
DISPATCHER_ENTRYPOINT = "nexus_agent_platform.dispatcher_once"
NOVA_RESEARCH_ENTRYPOINT = "nova.research_room_dispatch"
RESEARCH_INTAKE_RUNNER_ENTRYPOINT = "run_dispatched_research_job"
RESEARCH_INTAKE_RUNNER_PATH = Path("scripts/research/run_dispatched_research_job.py")
RESEARCH_INTAKE_WORKER_PATH = Path("scripts/nexus_agent_platform/job_worker_once.py")
LAUNCHER = Path("scripts/ops/nexus_mcp_bridge.sh")
DISPATCHER_WRAPPER = Path("scripts/ops/run_with_canonical_runtime_env.sh")
LAUNCHD_PLIST = Path("launchd/com.nexus.nexus-mcp-bridge.plist")
DISPATCHER_PLIST = Path("launchd/com.nexus.durable-dispatcher.plist")
STATIC_DATA_FILES = {
    "first_3_testers_seed_template.json",
    "tester_accounts_template.json",
    "tester_client_records_template.json",
}
STATIC_SEED_FILES = {
    Path("requirements-agent-platform.txt"),
    LAUNCHER,
    DISPATCHER_WRAPPER,
    LAUNCHD_PLIST,
    DISPATCHER_PLIST,
    # The active bridge plist launches this release-relative gateway. Include
    # it in immutable packages or launchd will register a missing executable.
    Path("scripts/ops/nexus_mcp_gateway.sh"),
}


def seed_files(base: Path) -> set[Path]:
    """Return only immutable configuration and entrypoint assets from the seed."""
    selected = set(STATIC_SEED_FILES)
    for folder in (Path("configs"), Path("config")):
        directory = base / folder
        if directory.is_dir():
            for path in directory.rglob("*"):
                if not path.is_file() or path.is_symlink():
                    continue
                relative = path.relative_to(base)
                if "__pycache__" in relative.parts or path.suffix in {".pyc", ".ipynb"}:
                    continue
                if folder == Path("config") and path.suffix != ".json":
                    continue
                if relative == Path("config/remote_capability_memory.json") or "memories" in relative.parts:
                    continue
                selected.add(relative)
    selected.add(Path("config/research/research_tool_registry.json"))
    selected.update(Path("data") / name for name in STATIC_DATA_FILES)
    return {relative for relative in selected if (base / relative).is_file()}


def static_seed_files(base: Path, runtime_files: set[Path]) -> set[Path]:
    """Use the base only for static assets absent from the canonical runtime."""
    return seed_files(base) - runtime_files


def copy_selected(source: Path, output: Path, selected: set[Path], label: str) -> None:
    """Sequential bounded copy with progress; never clones an entire release tree."""
    started = time.monotonic()
    ordered = sorted(selected)
    for index, relative in enumerate(ordered, 1):
        source_path = source / relative
        if not source_path.is_file() or source_path.is_symlink():
            raise RuntimeError(f"SELECTED_RELEASE_FILE_INVALID: {relative}")
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target)
        target.chmod(target.stat().st_mode | 0o600)
        if index % 100 == 0 or index == len(ordered):
            print(f"{label}_PROGRESS={index}/{len(ordered)} ELAPSED_SECONDS={int(time.monotonic()-started)}", flush=True)


def python_import_closure(source: Path, entrypoints: tuple[str, ...] = (MCP_ENTRYPOINT,)) -> set[Path]:
    pending = list(entrypoints)
    visited: set[str] = set()
    files: set[Path] = set()
    while pending:
        name = pending.pop()
        if name in visited:
            continue
        visited.add(name)
        path = module_file(source, name)
        if path is None:
            raise RuntimeError(f"canonical local import is unresolved: {name}")
        files.add(path.relative_to(source))
        pending.extend(imported_local_names(path, source, None) - visited)
    return files


def worker_executable_paths(source: Path) -> set[Path]:
    """Find repository scripts selected by literal path in the durable worker."""
    worker = source / RESEARCH_INTAKE_WORKER_PATH
    if not worker.is_file():
        raise RuntimeError(f"EXECUTABLE_PATH_SOURCE_MISSING: {RESEARCH_INTAKE_WORKER_PATH}")
    tree = ast.parse(worker.read_text(encoding="utf-8"), filename=str(worker))
    return {Path(node.value) for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
            and node.value.startswith("scripts/") and node.value.endswith(".py")}


def script_module_name(path: Path) -> str:
    if not path.parts or path.parts[0] != "scripts" or path.suffix != ".py":
        raise RuntimeError(f"EXECUTABLE_PATH_NOT_A_PACKAGED_SCRIPT: {path}")
    return ".".join(path.with_suffix("").parts[1:])


def runtime_files_for_source(source: Path) -> set[Path]:
    """Include imported modules and explicitly invoked executable entrypoints."""
    roots = (MCP_ENTRYPOINT, DISPATCHER_ENTRYPOINT, RESEARCH_WORKER_ENTRYPOINT,
             NOVA_RESEARCH_ENTRYPOINT, RESEARCH_INTAKE_RUNNER_ENTRYPOINT)
    # Several provider/governor adapters late-bind this helper at runtime to
    # load the established canonical environment. Static import discovery does
    # not follow those dynamic adapter boundaries, so package the helper
    # explicitly instead of allowing a canonical-checkout import escape.
    executable_paths = worker_executable_paths(source)
    executable_roots = tuple(script_module_name(path) for path in sorted(executable_paths))
    # `scripts.opportunities` is imported by the operator as a namespace under
    # the release's scripts root; module_file() historically only followed the
    # deeper `nexus_agent_platform` script namespace. Include its runtime files
    # explicitly so canonical opportunity modules cannot be omitted silently.
    opportunities_root = source / "scripts/opportunities"
    opportunities_files = {
        path.relative_to(source) for path in opportunities_root.rglob("*.py")
        if path.is_file() and "tests" not in path.relative_to(opportunities_root).parts
        and "__pycache__" not in path.parts
    } if opportunities_root.is_dir() else set()
    # The github_remote operator late-binds `from scripts.github_remote import
    # github_remote` inside a function; the `scripts.`-prefixed import is not
    # followed by the module-name closure, so include this sibling script
    # package explicitly (same pattern as opportunities) to avoid silently
    # dropping a packaged runtime dependency.
    github_remote_root = source / "scripts/github_remote"
    github_remote_files = {
        path.relative_to(source) for path in github_remote_root.rglob("*.py")
        if path.is_file() and "tests" not in path.relative_to(github_remote_root).parts
        and "__pycache__" not in path.parts
    } if github_remote_root.is_dir() else set()
    return python_import_closure(source, roots + executable_roots) | executable_paths | opportunities_files | github_remote_files | {
        LAUNCHER, DISPATCHER_WRAPPER, Path("scripts/ops/nexus_runtime_env.py")}


def validate_executable_path_closure(source: Path, release: Path,
                                     runtime_files: set[Path] | None = None) -> None:
    """Fail closed for the runner path used by the dispatched intake worker.

    This dependency is selected by a subprocess path, so ordinary import
    traversal cannot discover it from ``job_worker_once.py``.
    """
    selected = runtime_files if runtime_files is not None else runtime_files_for_source(source)
    worker = source / RESEARCH_INTAKE_WORKER_PATH
    if not worker.is_file():
        raise RuntimeError(f"EXECUTABLE_PATH_SOURCE_MISSING: {RESEARCH_INTAKE_WORKER_PATH}")
    referenced = worker_executable_paths(source)
    missing_closure = referenced - selected
    if missing_closure:
        raise RuntimeError("EXECUTABLE_PATH_NOT_IN_RUNTIME_CLOSURE: " +
                           ", ".join(sorted(path.as_posix() for path in missing_closure)))
    missing_release = [path for path in referenced if not (release / path).is_file()]
    if missing_release:
        raise RuntimeError("EXECUTABLE_PATH_MISSING_FROM_RELEASE: " +
                           ", ".join(sorted(path.as_posix() for path in missing_release)))


def _copy_ignore_mutable_data(base: Path):
    """Keep immutable seed files, never snapshot mutable state into a release."""
    base = base.resolve()

    def ignore(directory: str, names: list[str]) -> set[str]:
        current = Path(directory).resolve()
        try:
            relative = current.relative_to(base)
        except ValueError:
            return set()
        if relative == Path("data"):
            return {name for name in names if name not in STATIC_DATA_FILES}
        return {name for name in names if name == "__pycache__" or name.endswith(".pyc")}

    return ignore


def validate_runtime_match(source: Path, release: Path, runtime_files: set[Path] | None = None) -> dict[str, str]:
    """Fail closed when any declared runtime source is absent or differs in staging."""
    selected = runtime_files if runtime_files is not None else runtime_files_for_source(source)
    mismatches: list[str] = []
    hashes: dict[str, str] = {}
    for relative in sorted(selected):
        canonical = source / relative
        packaged = release / relative
        if not canonical.is_file() or not packaged.is_file():
            mismatches.append(f"{relative}:missing")
            continue
        canonical_hash = hashlib.sha256(canonical.read_bytes()).hexdigest()
        packaged_hash = hashlib.sha256(packaged.read_bytes()).hexdigest()
        if canonical_hash != packaged_hash:
            mismatches.append(f"{relative}:{canonical_hash}!={packaged_hash}")
        hashes[relative.as_posix()] = canonical_hash
    if mismatches:
        raise RuntimeError("CANONICAL_RUNTIME_MISMATCH: " + "; ".join(mismatches[:20]))
    return hashes


def hash_and_manifest(release: Path) -> tuple[int, str, list[Path]]:
    manifest = release / "RELEASE_MANIFEST.sha256"
    source_hash_file = release / "RELEASE_SOURCE_HASH"
    files = sorted(
        path for path in release.rglob("*")
        if path.is_file() and not path.is_symlink()
        and path not in {manifest, source_hash_file}
        and "__pycache__" not in path.parts
    )
    lines: list[str] = []
    for index, path in enumerate(files, 1):
        lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  ./{path.relative_to(release).as_posix()}\n")
        if index % 100 == 0 or index == len(files):
            print(f"HASH_PROGRESS={index}/{len(files)}", flush=True)
    manifest.write_text("".join(lines), encoding="utf-8")
    digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    source_hash_file.write_text(digest + "\n", encoding="utf-8")
    return len(files), digest, files


def bind_launchd_to_release(release: Path, final_release_path: Path) -> int:
    """Point packaged launchd metadata at this release's eventual immutable path."""
    plist = release / LAUNCHD_PLIST
    text = plist.read_text(encoding="utf-8")
    prefix = str(Path.home() / ".nexus/releases") + "/"
    pattern = re.compile(re.escape(prefix) + r"nexus-capability-actions-[^/\s<]+")
    updated, count = pattern.subn(str(final_release_path), text)
    if count < 2:
        raise RuntimeError(f"expected executable and root launchd bindings, found {count}")
    plist.write_text(updated, encoding="utf-8")
    return count


def bind_durable_dispatcher_to_release(release: Path, final_release_path: Path,
                                      state_root: Path) -> int:
    """Bind MCP's durable dispatcher and child worker to the same release."""
    plist_path = release / DISPATCHER_PLIST
    with plist_path.open("rb") as handle:
        plist = plistlib.load(handle)
    arguments = list(plist.get("ProgramArguments") or [])
    if len(arguments) < 3:
        raise RuntimeError("DURABLE_DISPATCHER_PROGRAM_ARGUMENTS_INVALID")
    arguments[0] = str(final_release_path / DISPATCHER_WRAPPER)
    arguments[2] = str(final_release_path / "scripts/nexus_agent_platform/dispatcher_once.py")
    plist["ProgramArguments"] = arguments
    plist["WorkingDirectory"] = str(final_release_path)
    environment = dict(plist.get("EnvironmentVariables") or {})
    environment["PYTHONPATH"] = f"{final_release_path}/scripts:{final_release_path}"
    environment["NEXUS_RESEARCH_STATE_ROOT"] = str(state_root.resolve())
    plist["EnvironmentVariables"] = environment
    with plist_path.open("wb") as handle:
        plistlib.dump(plist, handle, sort_keys=False)
    return 4


def merge_dispatcher_allowed_sources(release: Path, source: Path) -> list[str]:
    """Keep seed allowlists while adding canonical dispatcher job sources."""
    packaged_path = release / DISPATCHER_PLIST
    source_path = source / DISPATCHER_PLIST
    with packaged_path.open("rb") as handle:
        packaged = plistlib.load(handle)
    with source_path.open("rb") as handle:
        canonical = plistlib.load(handle)
    packaged_env = dict(packaged.get("EnvironmentVariables") or {})
    canonical_env = dict(canonical.get("EnvironmentVariables") or {})
    packaged_sources = [item.strip() for item in str(
        packaged_env.get("NEXUS_DISPATCH_ALLOWED_JOB_SOURCES") or "").split(",") if item.strip()]
    canonical_sources = [item.strip() for item in str(
        canonical_env.get("NEXUS_DISPATCH_ALLOWED_JOB_SOURCES") or "").split(",") if item.strip()]
    merged = list(dict.fromkeys(packaged_sources + canonical_sources))
    packaged_env["NEXUS_DISPATCH_ALLOWED_JOB_SOURCES"] = ",".join(merged)
    packaged["EnvironmentVariables"] = packaged_env
    with packaged_path.open("wb") as handle:
        plistlib.dump(packaged, handle, sort_keys=False)
    return merged


def freeze(release: Path, files: list[Path]) -> None:
    directories: set[Path] = set()
    for path in files:
        for parent in path.parents:
            if parent == release:
                break
            if release in parent.parents:
                directories.add(parent)
    for path in files:
        if path.is_file() and not path.is_symlink():
            path.chmod(0o555 if path.stat().st_mode & 0o111 else 0o444)
    for path in sorted(directories, key=lambda item: len(item.parts), reverse=True):
        path.chmod(0o555)
    reports_root = release / "reports"
    if reports_root.is_dir():
        reports_root.chmod(0o555)
    release.chmod(0o555)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--base-release", type=Path, required=True,
                        help="Existing immutable release used only as a static asset seed")
    parser.add_argument("--output-release", type=Path, required=True)
    parser.add_argument("--release-id", required=True)
    args = parser.parse_args()
    source = args.source_root.resolve()
    base = args.base_release.expanduser().resolve()
    output = args.output_release.expanduser().absolute()
    final_release_path = Path.home() / ".nexus/releases" / args.release_id
    if not source.is_dir() or not base.is_dir() or output.exists():
        raise SystemExit("BUILD_INPUT_INVALID_OR_OUTPUT_EXISTS")

    runtime_files = runtime_files_for_source(source)
    output.mkdir(parents=True)
    # Nexus root discovery requires this structural directory. Keep it empty:
    # reports and logs are mutable runtime state and stay outside the release.
    (output / "reports").mkdir()
    # Runtime code always comes from canonical source. The seed contributes only
    # static config/assets; mutable state, reports, logs, caches, and manifests
    # are deliberately outside the package boundary.
    copy_selected(source, output, runtime_files, "RUNTIME_COPY")
    copy_selected(base, output, static_seed_files(base, runtime_files), "STATIC_SEED_COPY")
    merge_dispatcher_allowed_sources(output, source)
    validate_runtime_match(source, output, runtime_files)
    validate_executable_path_closure(source, output, runtime_files)
    launchd_binding_count = bind_launchd_to_release(output, final_release_path)
    dispatcher_binding_count = bind_durable_dispatcher_to_release(
        output, final_release_path, source / "data")
    launcher_text = (output / LAUNCHER).read_text(encoding="utf-8")
    if "nexus-capability-actions-20261020-r20" in launcher_text or "nexus-capability-actions-20261020-r21" in launcher_text:
        raise SystemExit("PACKAGED_LAUNCHER_HAS_PRIOR_RELEASE_REFERENCE")
    if 'ROOT="$(cd "$SCRIPT_DIR/../.." && pwd -P)"' not in launcher_text:
        raise SystemExit("PACKAGED_LAUNCHER_NOT_RELEASE_RELATIVE")
    dispatcher_text = (output / DISPATCHER_PLIST).read_text(encoding="utf-8")
    if "nexus-research-runtime-isolated-closure-20261020-r4" in dispatcher_text:
        raise SystemExit("PACKAGED_DISPATCHER_HAS_R4_BINDING")
    if (output / "data/runtime").exists() or (output / "data/governed").exists():
        raise SystemExit("MUTABLE_RUNTIME_STATE_PACKAGED_IN_RELEASE")

    count, digest, files = hash_and_manifest(output)
    freeze(output, files)
    print(f"OUTPUT_RELEASE={output}")
    print(f"RUNTIME_SOURCE_FILE_COUNT={len(runtime_files)}")
    print(f"LAUNCHD_RELEASE_BINDINGS={launchd_binding_count}")
    print(f"DISPATCHER_RELEASE_BINDINGS={dispatcher_binding_count}")
    print(f"MANIFEST_ENTRY_COUNT={count}")
    print(f"RELEASE_SOURCE_HASH={digest}")
    print("CANDIDATE_FROZEN=YES")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
