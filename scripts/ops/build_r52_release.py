#!/usr/bin/env python3
"""Build an explicit, immutable r52 overlay after its focused suite passes."""
from __future__ import annotations

import hashlib
import json
import shutil
import tarfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RELEASE_ID = "nexus-capability-actions-20261023-r52"
MANIFEST = ROOT / "config/r52_research_worker_release_manifest.v1.json"
CERTIFICATION = ROOT / "dist/r52_certification.xml"
OUTPUT = ROOT / "dist" / RELEASE_ID
ARCHIVE = ROOT / "dist" / f"{RELEASE_ID}.tar.gz"
SHA_FILE = ROOT / "dist" / f"{RELEASE_ID}.sha256"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def certification_summary(path: Path, minimum: int) -> dict:
    if not path.is_file():
        raise SystemExit("R52_CERTIFICATION_REPORT_MISSING")
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    tests = sum(int(item.attrib.get("tests", 0)) for item in suites)
    failures = sum(int(item.attrib.get("failures", 0)) for item in suites)
    errors = sum(int(item.attrib.get("errors", 0)) for item in suites)
    skipped = sum(int(item.attrib.get("skipped", 0)) for item in suites)
    testcases = list(root.iter("testcase"))
    covered = {str(item.attrib.get("classname", "")).replace(".", "/") for item in testcases}
    missing_suites = [name for name in json.loads(MANIFEST.read_text())["certification"]["required_suites"]
                      if not any(name.removesuffix(".py") in value for value in covered)]
    if tests < minimum or failures or errors or skipped or missing_suites:
        raise SystemExit(f"R52_CERTIFICATION_FAILED:tests={tests}:failures={failures}:errors={errors}")
    return {"result": "PASS", "tests": tests, "failures": failures,
            "errors": errors, "skipped": skipped, "report": "certification/r52_certification.xml"}


def main() -> int:
    contract = json.loads(MANIFEST.read_text())
    if contract.get("release_id") != RELEASE_ID:
        raise SystemExit("R52_RELEASE_ID_MISMATCH")
    if OUTPUT.exists() or ARCHIVE.exists() or SHA_FILE.exists():
        raise SystemExit("R52_IMMUTABLE_OUTPUT_ALREADY_EXISTS")
    cert = certification_summary(CERTIFICATION, int(contract["certification"]["minimum_test_count"]))
    runtime_files = contract["runtime_files"]
    for relative in runtime_files:
        source = ROOT / relative
        if not source.is_file():
            raise SystemExit(f"R52_RUNTIME_FILE_MISSING:{relative}")

    OUTPUT.mkdir(parents=True)
    try:
        for relative in runtime_files:
            target = OUTPUT / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
            shutil.copystat(ROOT / relative, target)
        certification_dir = OUTPUT / "certification"
        certification_dir.mkdir()
        shutil.copyfile(CERTIFICATION, certification_dir / CERTIFICATION.name)
        payload = {relative: sha256(OUTPUT / relative) for relative in runtime_files}
        manifest = {**contract, "payload_sha256": payload,
                    "certification": {**contract["certification"], **cert}}
        (OUTPUT / "R52_RELEASE_MANIFEST.json").write_text(
            json.dumps(manifest, sort_keys=True, indent=2) + "\n")
        metadata = {
            "release_id": RELEASE_ID,
            "base_release_id": contract["base_release_id"],
            "built_at": datetime.now(timezone.utc).isoformat(),
            "python_version": __import__("sys").version.split()[0],
            "payload_file_count": len(runtime_files),
            "certification": cert,
        }
        (OUTPUT / "BUILD_METADATA.json").write_text(json.dumps(metadata, sort_keys=True, indent=2) + "\n")
        # Re-verify the staged overlay before sealing the immutable archive.
        staged = json.loads((OUTPUT / "R52_RELEASE_MANIFEST.json").read_text())
        for relative, expected in staged["payload_sha256"].items():
            if sha256(OUTPUT / relative) != expected:
                raise SystemExit(f"R52_STAGED_HASH_MISMATCH:{relative}")
        with tarfile.open(ARCHIVE, "w:gz", compresslevel=6) as archive:
            archive.add(OUTPUT, arcname=RELEASE_ID, recursive=True)
        digest = sha256(ARCHIVE)
        SHA_FILE.write_text(f"{digest}  {ARCHIVE.name}\n")
        return 0
    except Exception:
        # Preserve a partial output for inspection; never silently overwrite it.
        raise


if __name__ == "__main__":
    raise SystemExit(main())
