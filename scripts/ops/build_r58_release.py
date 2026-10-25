#!/usr/bin/env python3
"""Compose immutable R58 from the exact certified R57 runtime and R58 overlay."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tarfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = json.loads((ROOT / "certification/r58_source/contract.json").read_text())
RELEASE_ID = CONTRACT["release_id"]
R57_ROOT = Path(os.environ["R57_RELEASE_ROOT"]).resolve()
REPORT = Path(os.environ.get("R58_CERT_REPORT", ROOT / "dist/r58_certification.xml")).resolve()
RELEASE = ROOT / "dist" / RELEASE_ID
ARCHIVE = ROOT / "dist" / f"{RELEASE_ID}.tar.gz"
SIDECAR = ROOT / "dist" / f"{RELEASE_ID}.sha256"
CERT_FILES = [Path("certification/r58_source/contract.json"),
              Path("certification/r58_source/tests/test_r58_assignment_evidence.py"),
              Path("certification/r58_source/tests/r58_release_smoke.py")]
SECRET_PATTERNS = [
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"\bAKIA[0-9A-Z]{16}\b"), re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(rb"\bsb_secret_[A-Za-z0-9_-]{20,}\b"), re.compile(rb"\bsk-[A-Za-z0-9_-]{30,}\b"),
]


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    if not R57_ROOT.is_dir() or R57_ROOT.name != CONTRACT["base_release_id"]:
        raise SystemExit("R57_BASE_ROOT_INVALID")
    if RELEASE.exists() or ARCHIVE.exists() or SIDECAR.exists():
        raise SystemExit("R58_IMMUTABLE_OUTPUT_ALREADY_EXISTS")
    r57_manifest_path = R57_ROOT / "R57_RELEASE_MANIFEST.json"
    if sha(r57_manifest_path) != CONTRACT["base_manifest_sha256"]:
        raise SystemExit("R57_BASE_MANIFEST_HASH_MISMATCH")
    r57_manifest = json.loads(r57_manifest_path.read_text())
    if (r57_manifest.get("release_id") != CONTRACT["base_release_id"]
            or r57_manifest.get("source_commit") != CONTRACT["base_source_commit"]
            or r57_manifest.get("certification", {}).get("result") != "PASS"):
        raise SystemExit("R57_BASE_IDENTITY_OR_CERTIFICATION_MISMATCH")
    for relative, expected in r57_manifest.get("payload_sha256", {}).items():
        path = R57_ROOT / relative
        if not path.is_file() or sha(path) != expected:
            raise SystemExit("R57_BASE_PAYLOAD_MISMATCH:" + relative)
    if not REPORT.is_file():
        raise SystemExit("R58_CERTIFICATION_REPORT_MISSING")
    suites = list(ET.parse(REPORT).getroot().iter("testsuite"))
    totals = {key: sum(int(s.attrib.get(key, 0)) for s in suites)
              for key in ("tests", "failures", "errors", "skipped")}
    if totals["tests"] < 25 or any(totals[key] for key in ("failures", "errors", "skipped")):
        raise SystemExit("R58_CERTIFICATION_FAILED:" + json.dumps(totals))

    shutil.copytree(R57_ROOT, RELEASE, symlinks=True)
    # Keep the immediate R57 manifest as the only root-level base manifest.
    older_manifest = RELEASE / "R56_RELEASE_MANIFEST.json"
    lineage = RELEASE / "certification/lineage"
    lineage.mkdir(parents=True, exist_ok=True)
    if not older_manifest.is_file():
        raise SystemExit("R57_IMMEDIATE_BASE_MANIFEST_MISSING")
    lineage_r56 = lineage / older_manifest.name
    shutil.move(str(older_manifest), str(lineage_r56))
    old_sidecar = RELEASE / "RELEASE_MANIFEST.sha256"
    old_sidecar.unlink(missing_ok=True)
    old_metadata = RELEASE / "BUILD_METADATA.json"
    old_metadata.unlink(missing_ok=True)

    payload = dict(r57_manifest["payload_sha256"])
    payload["R57_RELEASE_MANIFEST.json"] = sha(RELEASE / "R57_RELEASE_MANIFEST.json")
    payload["certification/lineage/R56_RELEASE_MANIFEST.json"] = sha(lineage_r56)
    for relative in CONTRACT["changed_runtime_files"]:
        source = ROOT / relative
        if not source.is_file():
            raise SystemExit("R58_RUNTIME_SOURCE_MISSING:" + relative)
        target = RELEASE / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        payload[relative] = sha(target)
    for relative in CERT_FILES:
        source = ROOT / relative
        if not source.is_file():
            raise SystemExit("R58_CERTIFICATION_SOURCE_MISSING:" + str(relative))
        target = RELEASE / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        payload[relative.as_posix()] = sha(target)
    report_target = RELEASE / "certification/r58_source/r58_certification.xml"
    report_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPORT, report_target)
    payload[report_target.relative_to(RELEASE).as_posix()] = sha(report_target)

    source_commit = os.environ.get("GITHUB_SHA")
    if not source_commit:
        raise SystemExit("GITHUB_SHA_REQUIRED_FOR_IMMUTABLE_LINEAGE")
    metadata = {
        "release_id": RELEASE_ID,
        "base_release_id": CONTRACT["base_release_id"],
        "source_commit": source_commit,
        "base_source_commit": CONTRACT["base_source_commit"],
        "base_artifact_sha256": CONTRACT["base_artifact_sha256"],
        "base_manifest_sha256": CONTRACT["base_manifest_sha256"],
        "changed_runtime_files": CONTRACT["changed_runtime_files"],
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_file_count": len(payload),
        "certification": {"result": "PASS", **totals},
    }
    metadata_path = RELEASE / "BUILD_METADATA.json"
    metadata_path.write_text(json.dumps(metadata, sort_keys=True, indent=2) + "\n")
    manifest = {
        "release_id": RELEASE_ID,
        "base_release_id": CONTRACT["base_release_id"],
        "source_commit": source_commit,
        "base_source_commit": CONTRACT["base_source_commit"],
        "base_artifact_sha256": CONTRACT["base_artifact_sha256"],
        "base_manifest_sha256": CONTRACT["base_manifest_sha256"],
        "build_metadata_sha256": sha(metadata_path),
        "payload_file_count": len(payload),
        "payload_sha256": payload,
        "certification": {"result": "PASS", **totals},
        "composition_rule": CONTRACT["composition_rule"],
    }
    manifest_path = RELEASE / "R58_RELEASE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    (RELEASE / "RELEASE_MANIFEST.sha256").write_text(
        f"{sha(manifest_path)}  R58_RELEASE_MANIFEST.json\n")
    for relative, expected in payload.items():
        if sha(RELEASE / relative) != expected:
            raise SystemExit("R58_FINAL_PAYLOAD_HASH_MISMATCH:" + relative)

    forbidden_suffixes = {".sqlite", ".sqlite3", ".db", ".jsonl", ".log", ".env"}
    forbidden_names = {"runtime.env", "research_runtime_states.jsonl"}
    for path in RELEASE.rglob("*"):
        if not path.is_file():
            continue
        if path.name in forbidden_names or path.suffix.lower() in forbidden_suffixes:
            raise SystemExit("R58_FORBIDDEN_RELEASE_FILE:" + path.relative_to(RELEASE).as_posix())
        body = path.read_bytes()
        for pattern in SECRET_PATTERNS:
            if pattern.search(body):
                raise SystemExit("R58_SECRET_PATTERN:" + path.relative_to(RELEASE).as_posix())
    with tarfile.open(ARCHIVE, "w:gz", compresslevel=6) as archive:
        archive.add(RELEASE, arcname=RELEASE_ID, recursive=True)
    digest = sha(ARCHIVE)
    SIDECAR.write_text(f"{digest}  {ARCHIVE.name}\n")
    print(json.dumps({"release_id": RELEASE_ID, "artifact": str(ARCHIVE),
                      "sha256": digest, "payload_file_count": len(payload), **totals}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
