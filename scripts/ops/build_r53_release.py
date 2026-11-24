#!/usr/bin/env python3
"""Build immutable R53 overlay from a passing focused certification report."""
from __future__ import annotations

import hashlib
import json
import shutil
import tarfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASE_ID = "nexus-capability-actions-20261024-r53"
MANIFEST = ROOT / "config/r53_host_gate_release_manifest.v1.json"
CERTIFICATION = ROOT / "dist/r53_certification.xml"
OUTPUT = ROOT / "dist" / RELEASE_ID
ARCHIVE = ROOT / "dist" / f"{RELEASE_ID}.tar.gz"
SHA_FILE = ROOT / "dist" / f"{RELEASE_ID}.sha256"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def certification_summary(path: Path, contract: dict) -> dict:
    if not path.is_file():
        raise SystemExit("R53_CERTIFICATION_REPORT_MISSING")
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    tests = sum(int(item.attrib.get("tests", 0)) for item in suites)
    failures = sum(int(item.attrib.get("failures", 0)) for item in suites)
    errors = sum(int(item.attrib.get("errors", 0)) for item in suites)
    skipped = sum(int(item.attrib.get("skipped", 0)) for item in suites)
    cases = list(root.iter("testcase"))
    covered = {str(item.attrib.get("classname", "")).replace(".", "/") for item in cases}
    missing = [name for name in contract["certification"]["required_suites"]
               if not any(name.removesuffix(".py") in value for value in covered)]
    minimum = int(contract["certification"]["minimum_test_count"])
    if tests < minimum or failures or errors or skipped or missing:
        raise SystemExit(f"R53_CERTIFICATION_FAILED:tests={tests}:failures={failures}:errors={errors}:skipped={skipped}:missing={len(missing)}")
    return {"result": "PASS", "tests": tests, "failures": failures,
            "errors": errors, "skipped": skipped, "report": "certification/r53_certification.xml"}


def main() -> int:
    contract = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if contract.get("release_id") != RELEASE_ID:
        raise SystemExit("R53_RELEASE_ID_MISMATCH")
    if OUTPUT.exists() or ARCHIVE.exists() or SHA_FILE.exists():
        raise SystemExit("R53_IMMUTABLE_OUTPUT_ALREADY_EXISTS")
    cert = certification_summary(CERTIFICATION, contract)
    runtime_files = contract["runtime_files"]
    for relative in runtime_files:
        if not (ROOT / relative).is_file():
            raise SystemExit(f"R53_RUNTIME_FILE_MISSING:{relative}")
    OUTPUT.mkdir(parents=True)
    for relative in runtime_files:
        target = OUTPUT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
        shutil.copystat(ROOT / relative, target)
    (OUTPUT / "certification").mkdir()
    shutil.copyfile(CERTIFICATION, OUTPUT / "certification/r53_certification.xml")
    hashes = {relative: sha256(OUTPUT / relative) for relative in runtime_files}
    (OUTPUT / "R53_RELEASE_MANIFEST.json").write_text(json.dumps(
        {**contract, "payload_sha256": hashes, "certification": {**contract["certification"], **cert}},
        sort_keys=True, indent=2) + "\n")
    (OUTPUT / "BUILD_METADATA.json").write_text(json.dumps({
        "release_id": RELEASE_ID, "base_release_id": contract["base_release_id"],
        "built_at": datetime.now(timezone.utc).isoformat(),
        "python_version": __import__("sys").version.split()[0],
        "payload_file_count": len(runtime_files), "certification": cert,
    }, sort_keys=True, indent=2) + "\n")
    manifest = json.loads((OUTPUT / "R53_RELEASE_MANIFEST.json").read_text())
    if any(sha256(OUTPUT / name) != digest for name, digest in manifest["payload_sha256"].items()):
        raise SystemExit("R53_STAGED_HASH_MISMATCH")
    with tarfile.open(ARCHIVE, "w:gz", compresslevel=6) as archive:
        archive.add(OUTPUT, arcname=RELEASE_ID, recursive=True)
    digest = sha256(ARCHIVE)
    SHA_FILE.write_text(f"{digest}  {ARCHIVE.name}\n")
    print(json.dumps({"release_id": RELEASE_ID, "archive": str(ARCHIVE),
                      "sha256": digest, "runtime_files": len(runtime_files),
                      "tests": cert["tests"], "result": cert["result"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
