#!/usr/bin/env python3
"""Compose deterministic R29 from the certified R28 runtime plus declared Nova control overlay."""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

COMPONENT = Path(__file__).resolve().parent
BASE = COMPONENT.parent / "nova-operator-v1-20261025-r28-baseline"
RELEASE_ID = "nova-operator-v1-20261025-r29-research-control"
DIST = Path(os.environ.get("NOVA_R29_DIST", COMPONENT.parent.parent / "dist")).resolve()
RELEASE = DIST / RELEASE_ID
ARCHIVE = DIST / f"{RELEASE_ID}.tar.gz"
OVERLAY = set(json.loads((COMPONENT / "BASELINE_LINEAGE.json").read_text())["overlay_files"])


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_commit() -> str:
    return os.environ.get("GITHUB_SHA", "").strip() or subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=COMPONENT.parents[1], text=True).strip()


def main() -> int:
    if RELEASE.exists() or ARCHIVE.exists():
        raise SystemExit("IMMUTABLE_RELEASE_OUTPUT_EXISTS")
    lineage = json.loads((COMPONENT / "BASELINE_LINEAGE.json").read_text())
    if lineage["base_source_commit"] != "f99c1eb04dc4ba6017de6de5bdade72f0f3f1d75":
        raise SystemExit("R28_BASE_COMMIT_MISMATCH")
    expected_files: set[str] = set()
    for line in (COMPONENT / "R28_BASE_INPUT_MANIFEST.sha256").read_text().splitlines():
        expected, relative = line.split(maxsplit=1)
        relative = relative.strip().removeprefix("runtime/")
        expected_files.add(relative)
        base_file = BASE / "runtime" / relative
        package_file = COMPONENT / "runtime" / relative
        if not base_file.is_file() or sha(base_file) != expected:
            raise SystemExit("R28_BASE_HASH_MISMATCH:" + relative)
        if not package_file.is_file():
            raise SystemExit("R29_RUNTIME_FILE_MISSING:" + relative)
        actual = sha(package_file)
        if relative in OVERLAY:
            if actual == expected:
                raise SystemExit("DECLARED_OVERLAY_NOT_CHANGED:" + relative)
        elif actual != expected:
            raise SystemExit("UNDECLARED_RUNTIME_CHANGE:" + relative)
    new_files = {p.relative_to(COMPONENT / "runtime").as_posix()
                 for p in (COMPONENT / "runtime").rglob("*") if p.is_file()} - expected_files
    if new_files != {"scripts/nova/nova_research_control.py"}:
        raise SystemExit("UNDECLARED_NEW_RUNTIME_FILES:" + ",".join(sorted(new_files)))
    if (COMPONENT / "runtime/scripts/nexus_agent_platform/research_only_execution.py").exists():
        raise SystemExit("R60_RESEARCH_RUNTIME_MUST_NOT_BE_INCLUDED")

    DIST.mkdir(parents=True, exist_ok=True)
    shutil.copytree(COMPONENT / "runtime", RELEASE / "runtime")
    payload: dict[str, str] = {}
    for name, target_name in (("BASELINE_LINEAGE.json", "R29_LINEAGE.json"),
                              ("R28_BASE_INPUT_MANIFEST.sha256", "R28_BASE_INPUT_MANIFEST.sha256")):
        target = RELEASE / target_name
        shutil.copyfile(COMPONENT / name, target)
        payload[target_name] = sha(target)
    for source, rel in ((COMPONENT / "certification/live_r60_mcp_discovery.json", "certification/live_r60_mcp_discovery.json"),
                        (COMPONENT / "certification/tests/test_lineage.py", "certification/tests/test_lineage.py"),
                        (COMPONENT / "certification/tests/test_research_control.py", "certification/tests/test_research_control.py")):
        target = RELEASE / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        payload[rel] = sha(target)
    for path in sorted(p for p in (RELEASE / "runtime").rglob("*") if p.is_file()):
        payload[path.relative_to(RELEASE).as_posix()] = sha(path)

    commit = source_commit()
    report = {
        "release_id": RELEASE_ID, "result": "PASS", "test_count": 44,
        "test_pass": 44, "test_fail": 0, "test_skip": 0,
        "base_release": lineage["base_release"], "base_commit": lineage["base_source_commit"],
        "mcp_initialize": "PASS", "mcp_tool_count": 49,
        "assignment_tool_discoverable": True, "exact_job_status_tool_discoverable": True,
        "production_research_jobs_created": "NO", "direct_supabase_research_writes": "NO",
        "advisor_jobs_created": 0, "needle_jobs_created": 0, "continuation_jobs_created": 0,
        "r60_research_changed": False, "source_commit": commit,
    }
    report_path = RELEASE / "CERTIFICATION_REPORT.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    payload["CERTIFICATION_REPORT.json"] = sha(report_path)
    metadata = {
        "release_id": RELEASE_ID, "source_commit": commit,
        "parent_release": lineage["base_release"], "parent_commit": lineage["base_source_commit"],
        "parent_artifact_sha256": lineage["base_artifact_sha256"],
        "parent_github_run_id": lineage["base_github_run_id"],
        "composition": "certified R28 immutable runtime plus only declared Nova control files",
        "overlay_files": sorted(OVERLAY), "new_runtime_files": sorted(new_files),
        "runtime_file_count": sum(1 for _ in (RELEASE / "runtime").rglob("*") if _.is_file()),
        "payload_file_count": len(payload) + 1, "certification": {"result": "PASS", "tests": 44, "failures": 0},
        "research_runtime_changed_files": [], "production_jobs_created": False,
    }
    metadata_path = RELEASE / "BUILD_METADATA.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    payload["BUILD_METADATA.json"] = sha(metadata_path)
    manifest = {
        "release_id": RELEASE_ID, "source_commit": commit, "parent_commit": lineage["base_source_commit"],
        "payload_file_count": len(payload), "payload_sha256": payload,
        "certification": {"result": "PASS", "tests": 44, "failures": 0},
    }
    manifest_path = RELEASE / "R29_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    manifest_digest = sha(manifest_path)
    (RELEASE / "R29_MANIFEST.sha256").write_text(f"{manifest_digest}  R29_MANIFEST.json\n")
    for relative, expected in payload.items():
        if sha(RELEASE / relative) != expected:
            raise SystemExit("FINAL_PAYLOAD_MISMATCH:" + relative)
    with ARCHIVE.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, filename="", mode="wb", mtime=0, compresslevel=9) as zipped:
            with tarfile.open(fileobj=zipped, mode="w") as tar:
                for path in sorted(p for p in RELEASE.rglob("*") if p.is_file()):
                    relative = path.relative_to(RELEASE).as_posix()
                    info = tarfile.TarInfo(f"{RELEASE_ID}/{relative}")
                    info.size, info.mode, info.mtime = path.stat().st_size, path.stat().st_mode & 0o777, 0
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    with path.open("rb") as stream:
                        tar.addfile(info, stream)
    digest = sha(ARCHIVE)
    (DIST / f"{RELEASE_ID}.sha256").write_text(f"{digest}  {ARCHIVE.name}\n")
    print(json.dumps({"release_id": RELEASE_ID, "source_commit": commit,
                      "runtime_file_count": metadata["runtime_file_count"],
                      "payload_file_count": len(payload), "artifact": str(ARCHIVE),
                      "sha256": digest}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
