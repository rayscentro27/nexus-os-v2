#!/usr/bin/env python3
"""Build a manifest-controlled State v2 overlay release; never deploy it."""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import shutil
import sys
import tarfile
import tempfile
import types
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "config/state_v2_release_manifest.v1.json"
MIGRATION = "20261022130000"
CERTIFICATION_RUN = "39877795473"
EXPECTED_CERTIFIED_COMMIT = "f7cbec76a1d5d2837a5d9dbac8a6fe9aca56e5c4"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def checked_source(relative: str) -> Path:
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts:
        raise RuntimeError(f"UNSAFE_MANIFEST_PATH:{relative}")
    path = ROOT.joinpath(*pure.parts)
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"MISSING_OR_UNSAFE_SOURCE:{relative}")
    return path


def verify_certified_copies(manifest: dict) -> None:
    for relative in manifest["certified_bundle_matches"]:
        source = checked_source(relative)
        certified = ROOT / "tmp/state_v2_portable_certification" / relative
        if not certified.is_file() or sha256(source) != sha256(certified):
            raise RuntimeError(f"CERTIFIED_SOURCE_MISMATCH:{relative}")


def import_check(release_root: Path) -> dict:
    """Import the packaged modules with only their declared runtime packages."""
    scripts = release_root / "scripts"
    packages = {
        "nexus_agent_platform": scripts / "nexus_agent_platform",
        "nexus_agent_platform.runtime": scripts / "nexus_agent_platform/runtime",
        "nexus_agent_platform.governed": scripts / "nexus_agent_platform/governed",
        "research": scripts / "research",
    }
    saved = {name: sys.modules.get(name) for name in packages}
    for name, package_path in packages.items():
        module = types.ModuleType(name)
        module.__path__ = [str(package_path)]
        module.__package__ = name
        sys.modules[name] = module
    sys.path.insert(0, str(scripts))
    try:
        for name in (
            "nexus_agent_platform.runtime.paths",
            "nexus_agent_platform.governed.persistence",
            "research.research_state_v2",
            "research.proactive_research_memory",
            "research.research_case_engine",
            "nexus_agent_platform.stability_supervisor",
        ):
            importlib.import_module(name)
    finally:
        sys.path.remove(str(scripts))
        for name in reversed(tuple(packages)):
            sys.modules.pop(name, None)
            if saved[name] is not None:
                sys.modules[name] = saved[name]
        for name in tuple(sys.modules):
            if name.startswith(("research.", "nexus_agent_platform.")):
                sys.modules.pop(name, None)
    return {"status": "PASS", "modules": 6, "production_network": "NOT_USED"}


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest["certified_source_commit"] != EXPECTED_CERTIFIED_COMMIT:
        raise RuntimeError("CERTIFIED_COMMIT_MANIFEST_MISMATCH")
    source_commit = os.environ.get("GITHUB_SHA", "")
    if not source_commit:
        raise RuntimeError("GITHUB_SHA_REQUIRED")
    verify_certified_copies(manifest)

    release_id = manifest["release_id"]
    dist = ROOT / "dist"
    release_root = dist / release_id
    if release_root.exists():
        shutil.rmtree(release_root)
    release_root.mkdir(parents=True)
    packaged: list[dict] = []
    for relative in manifest["source_files"]:
        source = checked_source(relative)
        destination = release_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        packaged.append({
            "path": relative,
            "sha256": sha256(destination),
            "bytes": destination.stat().st_size,
            "source_commit": source_commit,
            "certified_source_commit": manifest["certified_source_commit"],
        })

    runtime_path = release_root / "config/research_runtime_contract.v1.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    runtime["release_id"] = release_id
    state_contract = runtime["research_state_v2_persistence"]
    if state_contract.get("lookup_index_migration_applied") is not False:
        raise RuntimeError("MIGRATION_MUST_REMAIN_PENDING_IN_BUILD")
    runtime_path.write_text(json.dumps(runtime, indent=2) + "\n", encoding="utf-8")
    for item in packaged:
        if item["path"] == "config/research_runtime_contract.v1.json":
            item["sha256"] = sha256(runtime_path)
            item["bytes"] = runtime_path.stat().st_size

    contract = {
        "release_id": release_id,
        "base_release_id": manifest["base_release_id"],
        "REQUIRES_STATE_V2_DATABASE_MIGRATION": MIGRATION,
        "RESEARCH_START_ALLOWED_BEFORE_DB_MIGRATION": "NO",
        "HOT_STATE_SEED_REQUIRED": "YES",
        "LEGACY_LEDGER_REQUIRED": "NO",
        "STATE_V2_RUNTIME_CERTIFICATION": "PASS",
    }
    metadata = {
        "release_id": release_id,
        "source_commit": source_commit,
        "certified_source_commit": EXPECTED_CERTIFIED_COMMIT,
        "github_actions_run_id": os.environ.get("GITHUB_RUN_ID", ""),
        "build_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "state_v2_certification_run_id": CERTIFICATION_RUN,
        "state_v2_certification_result": "25 / 25 PASS",
    }
    for name, value in (("STATE_V2_RELEASE_CONTRACT.json", contract), ("BUILD_METADATA.json", metadata)):
        output = release_root / name
        write_json(output, value)
        packaged.append({"path": name, "sha256": sha256(output), "bytes": output.stat().st_size,
                         "source_commit": source_commit, "generated": True})

    # Immutable-release marker required by the runtime path resolver.
    marker = release_root / "RELEASE_MANIFEST.sha256"
    marker.write_text("".join(f"{item['sha256']}  {item['path']}\n" for item in packaged), encoding="utf-8")
    packaged.append({"path": "RELEASE_MANIFEST.sha256", "sha256": sha256(marker),
                     "bytes": marker.stat().st_size, "source_commit": source_commit, "generated": True})

    # Build-time contract checks are static and read only these explicit files.
    state_source = (release_root / "scripts/research/research_state_v2.py").read_text(encoding="utf-8")
    supervisor_source = (release_root / "scripts/nexus_agent_platform/stability_supervisor.py").read_text(encoding="utf-8")
    if "MAX_HISTORY_SEGMENT_PROBES = 4" not in state_source:
        raise RuntimeError("SEGMENT_PROBE_BOUND_MISSING")
    if "HISTORY_PARTITION_SELECTION_EXHAUSTED" not in supervisor_source:
        raise RuntimeError("SUPERVISOR_EXHAUSTION_ROUTING_MISSING")
    if state_contract["max_history_event_bytes"] != 65536 or state_contract["max_history_partition_bytes"] != 67108864:
        raise RuntimeError("HISTORY_BOUNDS_MISSING")
    if state_contract["normal_legacy_reads_allowed"] or state_contract["normal_legacy_writes_allowed"]:
        raise RuntimeError("LEGACY_NORMAL_ACCESS_REENABLED")

    report = {
        "release_id": release_id,
        "source_commit": source_commit,
        "legacy_ledger_included": False,
        "production_state_included": False,
        "database_migration_applied": False,
        "release_import_check": import_check(release_root),
        "validation": "PASS",
        "manifest_file_count": len(packaged),
        "files": packaged,
    }
    sidecar = dist / f"{release_id}.manifest.json"
    write_json(sidecar, {"release_id": release_id, "base_release_id": manifest["base_release_id"],
                         "files": packaged})
    write_json(dist / "BUILD_METADATA.json", metadata)
    write_json(dist / "validation_report.json", report)

    archive = dist / f"{release_id}.tar.gz"
    with tarfile.open(archive, "w:gz", format=tarfile.PAX_FORMAT) as tar:
        for item in packaged:
            tar.add(release_root / item["path"], arcname=f"{release_id}/{item['path']}", recursive=False)
    artifact = {"name": archive.name, "bytes": archive.stat().st_size, "sha256": sha256(archive)}
    report["artifact"] = artifact
    write_json(dist / "validation_report.json", report)
    summary = {
        "STATE_V2_RELEASE_BUILD": "PASS",
        "RELEASE_ID": release_id,
        "RELEASE_MANIFEST_FILE_COUNT": len(packaged),
        "RELEASE_ARTIFACT_NAME": archive.name,
        "RELEASE_ARTIFACT_BYTES": artifact["bytes"],
        "RELEASE_ARTIFACT_SHA256": artifact["sha256"],
        "RELEASE_IMPORT_CHECK": "PASS",
        "LEGACY_LEDGER_INCLUDED": "NO",
        "PRODUCTION_STATE_INCLUDED": "NO",
    }
    print(json.dumps(summary, sort_keys=True))
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as output:
            output.write("## State v2 release build\n\n")
            output.write("| Field | Value |\n|---|---|\n")
            for key, value in summary.items():
                output.write(f"| `{key}` | `{value}` |\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
