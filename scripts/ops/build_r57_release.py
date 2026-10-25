#!/usr/bin/env python3
"""Compose immutable R57 from the pinned certified R56 artifact and additive migration."""
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
CONTRACT = json.loads((ROOT / "certification/r57_source/contract.json").read_text())
RELEASE_ID = CONTRACT["release_id"]
R56_ROOT = Path(os.environ["R56_RELEASE_ROOT"]).resolve()
REPORT = Path(os.environ.get("R57_CERT_REPORT", ROOT / "dist/r57_certification.xml")).resolve()
RELEASE = ROOT / "dist" / RELEASE_ID
ARCHIVE = ROOT / "dist" / f"{RELEASE_ID}.tar.gz"
SIDECAR = ROOT / "dist" / f"{RELEASE_ID}.sha256"
ADDITIONS = [
    Path(CONTRACT["new_migration"]),
    Path("certification/r57_source/contract.json"),
    Path("certification/r57_source/predecessor/20261022120000_fix_resource_governor_jsonb_threshold.sql"),
    Path("certification/r57_source/sql/isolated_governor_schema.sql"),
    Path("certification/r57_source/tests/test_r57_governor_reservation_ordering.py"),
    Path("certification/r57_source/tests/r57_release_smoke.py"),
]
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


def inventory(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): sha(p) for p in sorted(root.rglob("*")) if p.is_file()}


def main() -> int:
    if not R56_ROOT.is_dir() or R56_ROOT.name != CONTRACT["base_release_id"]:
        raise SystemExit("R56_BASE_ROOT_INVALID")
    if RELEASE.exists() or ARCHIVE.exists() or SIDECAR.exists():
        raise SystemExit("R57_IMMUTABLE_OUTPUT_ALREADY_EXISTS")
    r56_manifest_path = R56_ROOT / "R56_RELEASE_MANIFEST.json"
    if sha(r56_manifest_path) != CONTRACT["base_manifest_sha256"]:
        raise SystemExit("R56_BASE_MANIFEST_HASH_MISMATCH")
    r56_manifest = json.loads(r56_manifest_path.read_text())
    if r56_manifest.get("release_id") != CONTRACT["base_release_id"] or r56_manifest.get("source_commit") != CONTRACT["base_source_commit"]:
        raise SystemExit("R56_BASE_IDENTITY_MISMATCH")
    if r56_manifest.get("certification", {}).get("result") != "PASS":
        raise SystemExit("R56_BASE_NOT_CERTIFIED")
    for relative, expected in r56_manifest.get("payload_sha256", {}).items():
        path = R56_ROOT / relative
        if not path.is_file() or sha(path) != expected:
            raise SystemExit("R56_BASE_PAYLOAD_MISMATCH:" + relative)
    if not REPORT.is_file():
        raise SystemExit("R57_CERTIFICATION_REPORT_MISSING")
    suites = list(ET.parse(REPORT).getroot().iter("testsuite"))
    totals = {key: sum(int(s.attrib.get(key, 0)) for s in suites)
              for key in ("tests", "failures", "errors", "skipped")}
    if totals["tests"] < CONTRACT["minimum_test_count"] or any(totals[k] for k in ("failures", "errors", "skipped")):
        raise SystemExit("R57_CERTIFICATION_FAILED:" + json.dumps(totals))

    shutil.copytree(R56_ROOT, RELEASE)
    # Keep only the immediate base manifest at root; R56's older R55 manifest is lineage metadata.
    old_base_manifest = RELEASE / "R55_RELEASE_MANIFEST.json"
    lineage_dir = RELEASE / "certification/lineage"
    lineage_dir.mkdir(parents=True, exist_ok=True)
    if old_base_manifest.exists():
        shutil.move(str(old_base_manifest), str(lineage_dir / old_base_manifest.name))
    # The root metadata/sidecar belong to the active release and must identify R57.
    old_sidecar = RELEASE / "RELEASE_MANIFEST.sha256"
    if old_sidecar.exists():
        old_sidecar.unlink()
    for relative in ADDITIONS:
        source = ROOT / relative
        if not source.is_file():
            raise SystemExit("R57_SOURCE_MISSING:" + str(relative))
        target = RELEASE / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    report_target = RELEASE / "certification/r57_certification.xml"
    report_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPORT, report_target)

    # Payload includes all certified R56 runtime bytes except the renamed R55 lineage manifest,
    # plus this R57 additive migration and the exact certification inputs.
    payload = dict(r56_manifest["payload_sha256"])
    payload.pop("R55_RELEASE_MANIFEST.json", None)
    payload["certification/lineage/R55_RELEASE_MANIFEST.json"] = sha(lineage_dir / "R55_RELEASE_MANIFEST.json")
    for relative in ADDITIONS:
        payload[relative.as_posix()] = sha(RELEASE / relative)
    metadata = {
        "release_id": RELEASE_ID,
        "base_release_id": CONTRACT["base_release_id"],
        "source_commit": os.environ["GITHUB_SHA"],
        "base_source_commit": CONTRACT["base_source_commit"],
        "base_artifact_sha256": CONTRACT["base_artifact_sha256"],
        "base_manifest_sha256": CONTRACT["base_manifest_sha256"],
        "migration": CONTRACT["new_migration"],
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_file_count": len(payload),
        "certification": {"result": "PASS", **totals},
    }
    metadata_path = RELEASE / "BUILD_METADATA.json"
    metadata_path.write_text(json.dumps(metadata, sort_keys=True, indent=2) + "\n")
    manifest = {
        "release_id": RELEASE_ID,
        "base_release_id": CONTRACT["base_release_id"],
        "source_commit": os.environ["GITHUB_SHA"],
        "base_source_commit": CONTRACT["base_source_commit"],
        "base_artifact_sha256": CONTRACT["base_artifact_sha256"],
        "base_manifest_sha256": CONTRACT["base_manifest_sha256"],
        "build_metadata_sha256": sha(metadata_path),
        "payload_file_count": len(payload),
        "payload_sha256": payload,
        "certification": {"result": "PASS", **totals},
        "composition_rule": "Exact certified R56 release payload plus one additive governor reservation-ordering migration and its isolated certification evidence.",
    }
    manifest_path = RELEASE / "R57_RELEASE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    (RELEASE / "RELEASE_MANIFEST.sha256").write_text(f"{sha(manifest_path)}  R57_RELEASE_MANIFEST.json\n")
    for relative, expected in payload.items():
        if sha(RELEASE / relative) != expected:
            raise SystemExit("R57_FINAL_PAYLOAD_HASH_MISMATCH:" + relative)
    forbidden_suffixes = {".sqlite", ".sqlite3", ".db", ".jsonl", ".log", ".env"}
    forbidden_names = {"runtime.env", "research_runtime_states.jsonl"}
    for path in RELEASE.rglob("*"):
        if path.is_file():
            if path.name in forbidden_names or path.suffix.lower() in forbidden_suffixes:
                raise SystemExit("R57_FORBIDDEN_RELEASE_FILE:" + path.relative_to(RELEASE).as_posix())
            body = path.read_bytes()
            for pattern in SECRET_PATTERNS:
                if pattern.search(body):
                    raise SystemExit("R57_SECRET_PATTERN:" + path.relative_to(RELEASE).as_posix())
    with tarfile.open(ARCHIVE, "w:gz", compresslevel=6) as archive:
        archive.add(RELEASE, arcname=RELEASE_ID, recursive=True)
    archive_hash = sha(ARCHIVE)
    SIDECAR.write_text(f"{archive_hash}  {ARCHIVE.name}\n")
    print(json.dumps({"release_id": RELEASE_ID, "artifact": str(ARCHIVE), "sha256": archive_hash,
                      "payload_file_count": len(payload), **totals}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
