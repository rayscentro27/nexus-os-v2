#!/usr/bin/env python3
"""Build the immutable R54 Research-only overlay from passing test evidence."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASE_ID = "nexus-capability-actions-20261024-r54"
CONTRACT = ROOT / "config/r54_research_only_release_manifest.v1.json"
REPORT = ROOT / "dist/r54_certification.xml"
OUTPUT = ROOT / "dist" / RELEASE_ID
ARCHIVE = ROOT / "dist" / f"{RELEASE_ID}.tar.gz"
SHA_FILE = ROOT / "dist" / f"{RELEASE_ID}.sha256"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def certification_summary(contract: dict) -> dict:
    if not REPORT.is_file():
        raise SystemExit("R54_CERTIFICATION_REPORT_MISSING")
    root = ET.parse(REPORT).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    tests = sum(int(item.attrib.get("tests", 0)) for item in suites)
    failures = sum(int(item.attrib.get("failures", 0)) for item in suites)
    errors = sum(int(item.attrib.get("errors", 0)) for item in suites)
    skipped = sum(int(item.attrib.get("skipped", 0)) for item in suites)
    cases = list(root.iter("testcase"))
    names = {str(case.attrib.get("classname", "")).replace(".", "/") for case in cases}
    missing = [suite for suite in contract["certification"]["required_suites"]
               if not any(suite.removesuffix(".py") in name for name in names)]
    minimum = int(contract["certification"]["minimum_test_count"])
    if tests < minimum or failures or errors or skipped or missing:
        raise SystemExit(f"R54_CERTIFICATION_FAILED:tests={tests}:failures={failures}:errors={errors}:skipped={skipped}:missing_suites={len(missing)}")
    return {"result": "PASS", "tests": tests, "failures": failures,
            "errors": errors, "skipped": skipped,
            "report": "certification/r54_certification.xml"}


def main() -> int:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("release_id") != RELEASE_ID:
        raise SystemExit("R54_RELEASE_ID_MISMATCH")
    if OUTPUT.exists() or ARCHIVE.exists() or SHA_FILE.exists():
        raise SystemExit("R54_IMMUTABLE_OUTPUT_ALREADY_EXISTS")
    certification = certification_summary(contract)
    files = contract["runtime_files"]
    if len(set(files)) != len(files):
        raise SystemExit("R54_DUPLICATE_RUNTIME_PATH")
    OUTPUT.mkdir(parents=True)
    for relative in files:
        source = ROOT / contract["source_map"][relative]
        if not source.is_file():
            raise SystemExit(f"R54_RUNTIME_FILE_MISSING:{relative}")
        target = OUTPUT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        shutil.copystat(source, target)
    cert_path = OUTPUT / "certification/r54_certification.xml"
    cert_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPORT, cert_path)
    payload = {relative: sha256(OUTPUT / relative) for relative in files}
    (OUTPUT / "R54_RELEASE_MANIFEST.json").write_text(json.dumps({
        **contract, "payload_sha256": payload, "certification": {
            **contract["certification"], **certification}}, sort_keys=True, indent=2) + "\n")
    try:
        source_commit = os.environ.get("GITHUB_SHA") or subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
            text=True, timeout=10, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        source_commit = "UNAVAILABLE"
    (OUTPUT / "BUILD_METADATA.json").write_text(json.dumps({
        "release_id": RELEASE_ID, "base_release_id": contract["base_release_id"],
        "source_commit": source_commit, "built_at": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version.split()[0], "payload_file_count": len(files),
        "certification": certification}, sort_keys=True, indent=2) + "\n")
    manifest = json.loads((OUTPUT / "R54_RELEASE_MANIFEST.json").read_text(encoding="utf-8"))
    for relative, expected in manifest["payload_sha256"].items():
        if sha256(OUTPUT / relative) != expected:
            raise SystemExit(f"R54_STAGED_HASH_MISMATCH:{relative}")
        if sha256(ROOT / contract["source_map"][relative]) != expected:
            raise SystemExit(f"R54_SOURCE_LINEAGE_MISMATCH:{relative}")
    with tarfile.open(ARCHIVE, "w:gz", compresslevel=6) as archive:
        archive.add(OUTPUT, arcname=RELEASE_ID, recursive=True)
    digest = sha256(ARCHIVE)
    SHA_FILE.write_text(f"{digest}  {ARCHIVE.name}\n", encoding="utf-8")
    print(json.dumps({"release_id": RELEASE_ID, "archive": str(ARCHIVE),
        "sha256": digest, "runtime_files": len(files), **certification}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
