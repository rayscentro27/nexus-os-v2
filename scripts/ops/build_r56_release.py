#!/usr/bin/env python3
"""Build immutable R56 from the certified R55 payload plus its readiness fix."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "certification/r56_source/contract.json"
REPORT = ROOT / "dist/r56_certification.xml"
RELEASE_ID = "nexus-capability-actions-20261025-r56"
RELEASE = ROOT / "dist" / RELEASE_ID
ARCHIVE = ROOT / "dist" / f"{RELEASE_ID}.tar.gz"
SIDECAR = ROOT / "dist" / f"{RELEASE_ID}.sha256"
SECRET_PATTERNS = [
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(rb"\bsb_secret_[A-Za-z0-9_-]{20,}\b"),
    re.compile(rb"\bsk-[A-Za-z0-9_-]{30,}\b"),
]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inventory(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): sha(p)
            for p in sorted(root.rglob("*")) if p.is_file()}


def validate_report(contract: dict) -> dict:
    if not REPORT.is_file():
        raise SystemExit("R56_CERTIFICATION_REPORT_MISSING")
    suites = list(ET.parse(REPORT).getroot().iter("testsuite"))
    totals = {key: sum(int(s.attrib.get(key, 0)) for s in suites)
              for key in ("tests", "failures", "errors", "skipped")}
    cases = list(ET.parse(REPORT).getroot().iter("testcase"))
    classes = {str(c.attrib.get("classname", "")).replace(".", "/") for c in cases}
    required = [p.removesuffix(".py") for p in contract["required_test_suites"]]
    missing = [p for p in required if not any(p in item for item in classes)]
    if (totals["tests"] < contract["minimum_test_count"] or totals["failures"]
            or totals["errors"] or totals["skipped"] or missing):
        raise SystemExit("R56_CERTIFICATION_FAILED:" + json.dumps({**totals, "missing": missing}))
    return {"result": "PASS", **totals, "required_suites": len(required)}


def validate_lineage(contract: dict) -> tuple[dict[str, str], dict[str, str]]:
    lineage = ROOT / contract["base_manifest_path"]
    metadata_path = ROOT / contract["base_metadata_path"]
    artifact_sidecar = ROOT / contract["base_artifact_sidecar_path"]
    if sha(lineage) != contract["base_manifest_sha256"]:
        raise SystemExit("R55_BASE_MANIFEST_HASH_MISMATCH")
    if sha(metadata_path) != contract["base_metadata_sha256"]:
        raise SystemExit("R55_BASE_METADATA_HASH_MISMATCH")
    if artifact_sidecar.read_text(encoding="utf-8").split()[0] != contract["base_artifact_sha256"]:
        raise SystemExit("R55_CERTIFIED_ARTIFACT_HASH_MISMATCH")
    manifest = json.loads(lineage.read_text(encoding="utf-8"))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if manifest.get("release_id") != contract["base_release_id"]:
        raise SystemExit("R55_BASE_RELEASE_ID_MISMATCH")
    if metadata.get("release_id") != contract["base_release_id"]:
        raise SystemExit("R55_BASE_BUILD_METADATA_MISMATCH")
    if metadata.get("source_commit") != contract["base_source_commit"]:
        raise SystemExit("R55_BASE_CERTIFIED_COMMIT_MISMATCH")
    if manifest.get("certification", {}).get("result") != "PASS":
        raise SystemExit("R55_BASE_NOT_CERTIFIED")
    base_root = ROOT / contract["base_source_directory"]
    base_hashes = inventory(base_root)
    if base_hashes != manifest.get("payload_sha256"):
        raise SystemExit("R55_BASE_PAYLOAD_DOES_NOT_MATCH_CERTIFIED_MANIFEST")
    if len(base_hashes) != 310:
        raise SystemExit("R55_BASE_PAYLOAD_COUNT_MISMATCH")
    overlay_root = ROOT / contract["overlay_source_directory"]
    overlay_hashes = inventory(overlay_root)
    if set(overlay_hashes) != set(contract["overlay_runtime_files"]):
        raise SystemExit("R56_OVERLAY_FILE_SET_MISMATCH")
    # The runtime source path must be the exact overlay chosen for this release.
    for relative, digest in overlay_hashes.items():
        if sha(ROOT / relative) != digest:
            raise SystemExit(f"R56_RUNTIME_SOURCE_OVERLAY_MISMATCH:{relative}")
    return base_hashes, overlay_hashes


def scan_runtime(root: Path, prohibited_suffixes: set[str], prohibited_names: set[str]) -> None:
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root)
        if path.name in prohibited_names or path.suffix.lower() in prohibited_suffixes:
            raise SystemExit(f"R56_FORBIDDEN_RUNTIME_FILE:{rel}")
        body = path.read_bytes()
        for pattern in SECRET_PATTERNS:
            if pattern.search(body):
                raise SystemExit(f"R56_SECRET_PATTERN:{rel}")


def main() -> int:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("release_id") != RELEASE_ID:
        raise SystemExit("R56_RELEASE_ID_MISMATCH")
    base_hashes, overlay_hashes = validate_lineage(contract)
    certification = validate_report(contract)
    if RELEASE.exists() or ARCHIVE.exists() or SIDECAR.exists():
        raise SystemExit("R56_IMMUTABLE_OUTPUT_ALREADY_EXISTS")
    RELEASE.mkdir(parents=True)
    (RELEASE / "reports").mkdir()
    base_root = ROOT / contract["base_source_directory"]
    overlay_root = ROOT / contract["overlay_source_directory"]
    for rel in sorted(base_hashes):
        dest = RELEASE / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(base_root / rel, dest)
    for rel in sorted(overlay_hashes):
        dest = RELEASE / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(overlay_root / rel, dest)
    # Retain the certified R55 manifest as explicit lineage metadata. It is a
    # declared base manifest, not a second active release candidate.
    shutil.copy2(ROOT / contract["base_manifest_path"], RELEASE / "R55_RELEASE_MANIFEST.json")
    scan_runtime(RELEASE, set(contract["prohibited_suffixes"]), set(contract["prohibited_names"]))
    payload = inventory(RELEASE)
    expected_paths = set(base_hashes) | set(overlay_hashes) | {"R55_RELEASE_MANIFEST.json"}
    if set(payload) != expected_paths:
        raise SystemExit("R56_COMPOSED_FILE_SET_MISMATCH")
    source_commit = os.environ.get("GITHUB_SHA") or subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True,
        text=True, timeout=10).stdout.strip()
    metadata = {
        "release_id": RELEASE_ID, "base_release_id": contract["base_release_id"],
        "base_artifact_sha256": contract["base_artifact_sha256"],
        "base_manifest_sha256": contract["base_manifest_sha256"],
        "source_commit": source_commit, "built_at": datetime.now(timezone.utc).isoformat(),
        "runtime_file_count": len(payload), "certification": certification,
    }
    metadata_path = RELEASE / "BUILD_METADATA.json"
    metadata_path.write_text(json.dumps(metadata, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "release_id": RELEASE_ID, "base_release_id": contract["base_release_id"],
        "base_artifact_sha256": contract["base_artifact_sha256"],
        "base_manifest_sha256": contract["base_manifest_sha256"],
        "source_commit": source_commit, "build_metadata_sha256": sha(metadata_path),
        "payload_file_count": len(payload), "payload_sha256": payload,
        "certification": {**certification},
        "composition_rule": "Certified immutable R55 runtime payload plus the single R56 active-release readiness resolver overlay.",
    }
    (RELEASE / "R56_RELEASE_MANIFEST.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    manifest_hash = sha(RELEASE / "R56_RELEASE_MANIFEST.json")
    (RELEASE / "RELEASE_MANIFEST.sha256").write_text(
        f"{manifest_hash}  R56_RELEASE_MANIFEST.json\n", encoding="utf-8")
    certification_report = RELEASE / "certification/r56_certification.xml"
    certification_report.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPORT, certification_report)
    (RELEASE / "RELEASE_MANIFEST.sha256").write_text(
        f"{manifest_hash}  R56_RELEASE_MANIFEST.json\n", encoding="utf-8")
    scan_runtime(RELEASE, set(contract["prohibited_suffixes"]), set(contract["prohibited_names"]))
    for relative, expected in payload.items():
        if sha(RELEASE / relative) != expected:
            raise SystemExit(f"R56_FINAL_PAYLOAD_HASH_MISMATCH:{relative}")
    with tarfile.open(ARCHIVE, "w:gz", compresslevel=6) as tar:
        tar.add(RELEASE, arcname=RELEASE_ID, recursive=True)
    archive_hash = sha(ARCHIVE)
    SIDECAR.write_text(f"{archive_hash}  {ARCHIVE.name}\n", encoding="utf-8")
    print(json.dumps({"release_id": RELEASE_ID, "archive": str(ARCHIVE),
        "sha256": archive_hash, "runtime_file_count": len(payload), **certification}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
