#!/usr/bin/env python3
"""Verify exact R57 ancestry and R58 source-to-artifact bytes."""
from __future__ import annotations

import hashlib
import json
import os
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = json.loads((ROOT / "certification/r58_source/contract.json").read_text())
RELEASE_ID = CONTRACT["release_id"]
RELEASE = ROOT / "dist" / RELEASE_ID
ARCHIVE = ROOT / "dist" / f"{RELEASE_ID}.tar.gz"
EXPECTED = os.environ.get("R58_EXPECTED_SHA256")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    actual = sha(ARCHIVE)
    sidecar = ROOT / "dist" / f"{RELEASE_ID}.sha256"
    if sidecar.read_text().split()[0] != actual or (EXPECTED and actual != EXPECTED):
        raise SystemExit("R58_ARCHIVE_SHA_MISMATCH")
    manifest_path = RELEASE / "R58_RELEASE_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text())
    if sha(manifest_path) != (RELEASE / "RELEASE_MANIFEST.sha256").read_text().split()[0]:
        raise SystemExit("R58_MANIFEST_SIDECAR_MISMATCH")
    if (manifest.get("release_id") != RELEASE_ID
            or manifest.get("base_release_id") != CONTRACT["base_release_id"]
            or manifest.get("source_commit") != os.environ.get("GITHUB_SHA")):
        raise SystemExit("R58_RELEASE_IDENTITY_MISMATCH")
    if sha(RELEASE / "BUILD_METADATA.json") != manifest.get("build_metadata_sha256"):
        raise SystemExit("R58_BUILD_METADATA_HASH_MISMATCH")
    metadata = json.loads((RELEASE / "BUILD_METADATA.json").read_text())
    if metadata.get("source_commit") != manifest.get("source_commit"):
        raise SystemExit("R58_BUILD_METADATA_IDENTITY_MISMATCH")

    r57_manifest_path = RELEASE / "R57_RELEASE_MANIFEST.json"
    if sha(r57_manifest_path) != CONTRACT["base_manifest_sha256"]:
        raise SystemExit("R58_R57_BASE_MANIFEST_MISMATCH")
    r57_manifest = json.loads(r57_manifest_path.read_text())
    if r57_manifest.get("source_commit") != CONTRACT["base_source_commit"]:
        raise SystemExit("R58_R57_BASE_COMMIT_MISMATCH")
    for relative, expected in r57_manifest["payload_sha256"].items():
        if relative in CONTRACT["changed_runtime_files"]:
            continue
        target = RELEASE / relative
        if not target.is_file() or sha(target) != expected:
            raise SystemExit("R57_BASE_FILE_CHANGED:" + relative)
    for relative in CONTRACT["changed_runtime_files"]:
        source = ROOT / relative
        target = RELEASE / relative
        if not source.is_file() or not target.is_file() or sha(source) != sha(target):
            raise SystemExit("R58_SOURCE_ARTIFACT_MISMATCH:" + relative)
        if manifest["payload_sha256"].get(relative) != sha(source):
            raise SystemExit("R58_OVERLAY_HASH_MISMATCH:" + relative)

    with tarfile.open(ARCHIVE, "r:gz") as tar:
        prefix = f"{RELEASE_ID}/"
        members = {member.name: member for member in tar.getmembers()}
        root_manifests = [name for name in members if name.startswith(prefix)
                          and name[len(prefix):].count("/") == 0
                          and name.endswith("_RELEASE_MANIFEST.json")]
        if sorted(name.removeprefix(prefix) for name in root_manifests) != [
                "R57_RELEASE_MANIFEST.json", "R58_RELEASE_MANIFEST.json"]:
            raise SystemExit("R58_ROOT_MANIFEST_LAYOUT_INVALID")
        for relative, expected in manifest["payload_sha256"].items():
            member = members.get(prefix + relative)
            if not member or not member.isfile():
                raise SystemExit("R58_PAYLOAD_MISSING:" + relative)
            if hashlib.sha256(tar.extractfile(member).read()).hexdigest() != expected:
                raise SystemExit("R58_ARCHIVE_PAYLOAD_MISMATCH:" + relative)
    print(json.dumps({"result": "PASS", "sha256": actual,
                      "payload_files": len(manifest["payload_sha256"]),
                      "source_commit": manifest["source_commit"],
                      "base_release": CONTRACT["base_release_id"],
                      "changed_runtime_files": CONTRACT["changed_runtime_files"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
