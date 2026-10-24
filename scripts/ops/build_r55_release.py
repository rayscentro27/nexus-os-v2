#!/usr/bin/env python3
"""Compose the immutable, self-contained R53 + certified R54 R55 release."""
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
RELEASE_ID = "nexus-capability-actions-20261024-r55"
CONTRACT_PATH = ROOT / "config/r55_deployable_release_manifest.v1.json"
REPORT = ROOT / "dist/r55_certification.xml"
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
FORBIDDEN_SUFFIXES = {".sqlite", ".sqlite3", ".db", ".jsonl", ".log", ".env"}
FORBIDDEN_NAMES = {"runtime.env", "research_runtime_states.jsonl"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_hash(path: Path) -> str:
    return digest(path.read_bytes())


def inventory(directory: Path) -> dict[str, str]:
    if not directory.is_dir():
        raise SystemExit(f"R55_SOURCE_DIRECTORY_MISSING:{directory}")
    return {p.relative_to(directory).as_posix(): file_hash(p)
            for p in sorted(directory.rglob("*")) if p.is_file()}


def validate_certification(contract: dict) -> dict:
    if not REPORT.is_file():
        raise SystemExit("R55_CERTIFICATION_REPORT_MISSING")
    root = ET.parse(REPORT).getroot()
    suites = list(root.iter("testsuite"))
    totals = {key: sum(int(s.attrib.get(key, 0)) for s in suites)
              for key in ("tests", "failures", "errors", "skipped")}
    cases = list(root.iter("testcase"))
    names = {str(c.attrib.get("classname", "")).replace(".", "/") for c in cases}
    missing = [s for s in contract["certification"]["required_suites"]
               if not any(s.removesuffix(".py") in name for name in names)]
    if (totals["tests"] < int(contract["certification"]["minimum_test_count"])
            or totals["failures"] or totals["errors"] or totals["skipped"] or missing):
        raise SystemExit("R55_CERTIFICATION_FAILED:" + json.dumps({**totals, "missing_suites": missing}))
    return {"result": "PASS", **totals, "required_suites": len(contract["certification"]["required_suites"])}


def validate_inputs(contract: dict) -> tuple[dict[str, str], dict[str, str]]:
    if contract.get("release_id") != RELEASE_ID:
        raise SystemExit("R55_RELEASE_ID_MISMATCH")
    base = ROOT / contract["base_release"]["source_directory"]
    overlay = ROOT / contract["overlay_release"]["source_directory"]
    base_hashes, overlay_hashes = inventory(base), inventory(overlay)
    if base_hashes != contract["base_release"]["payload_sha256"]:
        raise SystemExit("R55_R53_BASE_INVENTORY_MISMATCH")
    if overlay_hashes != contract["overlay_release"]["payload_sha256"]:
        raise SystemExit("R55_R54_OVERLAY_INVENTORY_MISMATCH")
    lineage = contract["lineage_manifests"]
    for name, record in lineage.items():
        path = ROOT / record["path"]
        if file_hash(path) != record["sha256"]:
            raise SystemExit(f"R55_LINEAGE_MANIFEST_HASH_MISMATCH:{name}")
        release = json.loads(path.read_text(encoding="utf-8"))
        expected_ids = {
            "R52_RELEASE_MANIFEST.json": "nexus-capability-actions-20261023-r52",
            "R53_RELEASE_MANIFEST.json": "nexus-capability-actions-20261024-r53",
            "R54_RELEASE_MANIFEST.json": "nexus-capability-actions-20261024-r54",
        }
        if release.get("release_id") != expected_ids.get(name):
            raise SystemExit(f"R55_LINEAGE_RELEASE_ID_MISMATCH:{name}")
        if release.get("certification", {}).get("result") != "PASS":
            raise SystemExit(f"R55_LINEAGE_NOT_CERTIFIED:{name}")
    r53_manifest = json.loads((ROOT / lineage["R53_RELEASE_MANIFEST.json"]["path"]).read_text())
    r54_manifest = json.loads((ROOT / lineage["R54_RELEASE_MANIFEST.json"]["path"]).read_text())
    if r53_manifest.get("base_release_id") != "nexus-capability-actions-20261023-r52":
        raise SystemExit("R55_R53_BASE_CHAIN_MISMATCH")
    if any(base_hashes.get(rel) != sha for rel, sha in r53_manifest.get("payload_sha256", {}).items()):
        raise SystemExit("R55_R53_CERTIFIED_PAYLOAD_MISMATCH")
    if r54_manifest.get("base_release_id") != contract["base_release"]["release_id"]:
        raise SystemExit("R55_R54_BASE_CHAIN_MISMATCH")
    if r54_manifest.get("payload_sha256") != overlay_hashes:
        raise SystemExit("R55_R54_ARTIFACT_PAYLOAD_MISMATCH")
    required_entrypoints = contract["entrypoints"]
    for entry in required_entrypoints:
        if entry not in base_hashes and entry not in overlay_hashes:
            raise SystemExit(f"R55_ENTRYPOINT_MISSING:{entry}")
    return base_hashes, overlay_hashes


def scan_runtime(release: Path) -> None:
    for path in sorted(p for p in release.rglob("*") if p.is_file()):
        rel = path.relative_to(release)
        if path.name in FORBIDDEN_NAMES or path.suffix.lower() in FORBIDDEN_SUFFIXES:
            raise SystemExit(f"R55_FORBIDDEN_RUNTIME_FILE:{rel}")
        body = path.read_bytes()
        for pattern in SECRET_PATTERNS:
            if pattern.search(body):
                raise SystemExit(f"R55_SECRET_PATTERN:{rel}")


def main() -> int:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    base_hashes, overlay_hashes = validate_inputs(contract)
    certification = validate_certification(contract)
    if RELEASE.exists() or ARCHIVE.exists() or SIDECAR.exists():
        raise SystemExit("R55_IMMUTABLE_OUTPUT_ALREADY_EXISTS")
    RELEASE.mkdir(parents=True)
    (RELEASE / "reports").mkdir()
    base_root = ROOT / contract["base_release"]["source_directory"]
    overlay_root = ROOT / contract["overlay_release"]["source_directory"]
    for rel in sorted(base_hashes):
        dest = RELEASE / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(base_root / rel, dest)
    for rel in sorted(overlay_hashes):
        dest = RELEASE / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            dest.unlink()
        shutil.copy2(overlay_root / rel, dest)
    scan_runtime(RELEASE)
    runtime_hashes = inventory(RELEASE)
    expected_paths = set(base_hashes) | set(overlay_hashes)
    if set(runtime_hashes) != expected_paths:
        raise SystemExit("R55_COMPOSED_FILE_SET_MISMATCH")
    cert_dest = RELEASE / "certification/r55_certification.xml"
    cert_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPORT, cert_dest)
    payload = {**runtime_hashes}
    manifest = {**contract, "runtime_file_count": len(payload), "payload_sha256": payload,
                "certification": {**contract["certification"], **certification}}
    (RELEASE / "R55_RELEASE_MANIFEST.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    release_manifest_hash = file_hash(RELEASE / "R55_RELEASE_MANIFEST.json")
    (RELEASE / "RELEASE_MANIFEST.sha256").write_text(
        f"{release_manifest_hash}  R55_RELEASE_MANIFEST.json\n", encoding="utf-8")
    try:
        source_commit = os.environ.get("GITHUB_SHA") or subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
            capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        source_commit = "UNAVAILABLE"
    metadata = {"release_id": RELEASE_ID, "base_release_id": contract["base_release"]["release_id"],
        "overlay_release_id": contract["overlay_release"]["release_id"],
        "source_commit": source_commit, "built_at": datetime.now(timezone.utc).isoformat(),
        "runtime_file_count": len(payload), "base_file_count": len(base_hashes),
        "overlay_file_count": len(overlay_hashes), "certification": certification}
    (RELEASE / "BUILD_METADATA.json").write_text(json.dumps(metadata, sort_keys=True, indent=2)+"\n")
    for rel, expected in payload.items():
        if file_hash(RELEASE / rel) != expected:
            raise SystemExit(f"R55_FINAL_PAYLOAD_HASH_MISMATCH:{rel}")
    with tarfile.open(ARCHIVE, "w:gz", compresslevel=6) as tar:
        tar.add(RELEASE, arcname=RELEASE_ID, recursive=True)
    archive_hash = file_hash(ARCHIVE)
    SIDECAR.write_text(f"{archive_hash}  {ARCHIVE.name}\n", encoding="utf-8")
    print(json.dumps({"release_id": RELEASE_ID, "archive": str(ARCHIVE),
        "sha256": archive_hash, "runtime_file_count": len(payload), **certification}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
