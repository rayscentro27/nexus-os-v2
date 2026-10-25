#!/usr/bin/env python3
"""Verify R60 payload hashes, exact R59 ancestry, and source/artifact match."""
from __future__ import annotations

import hashlib
import json
import os
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = json.loads((ROOT / "certification/r60_source/contract.json").read_text())
RELEASE = ROOT / "dist" / CONTRACT["release_id"]
ARCHIVE = ROOT / "dist" / f"{CONTRACT['release_id']}.tar.gz"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    manifest_path = RELEASE / "R60_RELEASE_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text())
    metadata = json.loads((RELEASE / "BUILD_METADATA.json").read_text())
    expected_commit = os.environ.get("GITHUB_SHA", "")
    if manifest.get("source_commit") != expected_commit or metadata.get("source_commit") != expected_commit:
        raise SystemExit("R60_CERTIFIED_SOURCE_COMMIT_MISMATCH")
    if (manifest.get("release_id") != CONTRACT["release_id"]
            or manifest.get("base_release_id") != CONTRACT["base_release_id"]
            or manifest.get("base_source_commit") != CONTRACT["base_source_commit"]
            or manifest.get("base_artifact_sha256") != CONTRACT["base_artifact_sha256"]
            or manifest.get("base_manifest_sha256") != CONTRACT["base_manifest_sha256"]):
        raise SystemExit("R60_R59_BASE_LINEAGE_MISMATCH")
    for relative, expected in manifest["payload_sha256"].items():
        path = RELEASE / relative
        if not path.is_file() or sha(path) != expected:
            raise SystemExit("R60_PAYLOAD_HASH_MISMATCH:" + relative)
    for relative in CONTRACT["changed_runtime_files"]:
        if sha(ROOT / relative) != sha(RELEASE / relative):
            raise SystemExit("R60_RUNTIME_SOURCE_MISMATCH:" + relative)
    with tarfile.open(ARCHIVE, "r:gz") as package:
        roots = {Path(member.name).parts[0] for member in package.getmembers() if member.name}
    if roots != {CONTRACT["release_id"]}:
        raise SystemExit("R60_ARCHIVE_ROOT_MISMATCH")
    print(json.dumps({"result": "PASS", "certified_commit": expected_commit,
        "artifact_sha256": sha(ARCHIVE), "manifest_sha256": sha(manifest_path),
        "payload_files": len(manifest["payload_sha256"]), "source_match": True,
        "base_release": CONTRACT["base_release_id"], "base_artifact_sha256": CONTRACT["base_artifact_sha256"]},
        sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
