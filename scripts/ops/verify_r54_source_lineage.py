#!/usr/bin/env python3
"""Verify R54 archive, manifest, and certified source snapshots agree."""
from __future__ import annotations

import hashlib
import json
import os
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASE_ID = "nexus-capability-actions-20261024-r54"
ARCHIVE = ROOT / "dist" / f"{RELEASE_ID}.tar.gz"
SIDECAR = ROOT / "dist" / f"{RELEASE_ID}.sha256"
CONTRACT = ROOT / "config/r54_research_only_release_manifest.v1.json"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> int:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    expected_hash, _ = SIDECAR.read_text(encoding="utf-8").split()
    if digest(ARCHIVE) != expected_hash:
        raise SystemExit("R54_ARCHIVE_SIDECAR_MISMATCH")
    expected_commit = os.environ.get("GITHUB_SHA")
    with tempfile.TemporaryDirectory(prefix="nexus-r54-lineage-") as temp:
        with tarfile.open(ARCHIVE, "r:gz") as tar:
            safe = Path(temp).resolve()
            for member in tar.getmembers():
                target = (safe / member.name).resolve()
                if not target.is_relative_to(safe):
                    raise SystemExit("R54_ARCHIVE_PATH_TRAVERSAL")
            tar.extractall(safe)
        release = Path(temp) / RELEASE_ID
        manifest = json.loads((release / "R54_RELEASE_MANIFEST.json").read_text(encoding="utf-8"))
        metadata = json.loads((release / "BUILD_METADATA.json").read_text(encoding="utf-8"))
        if manifest.get("release_id") != RELEASE_ID or metadata.get("release_id") != RELEASE_ID:
            raise SystemExit("R54_RELEASE_ID_MISMATCH")
        if manifest.get("base_release_id") != "nexus-capability-actions-20261024-r53":
            raise SystemExit("R54_BASE_RELEASE_MISMATCH")
        for relative in contract["runtime_files"]:
            packaged = release / relative
            source = ROOT / contract["source_map"][relative]
            expected = manifest["payload_sha256"].get(relative)
            if not expected or digest(packaged) != expected or digest(source) != expected:
                raise SystemExit(f"R54_SOURCE_ARTIFACT_MISMATCH:{relative}")
        if expected_commit and metadata.get("source_commit") != expected_commit:
            raise SystemExit("R54_SOURCE_COMMIT_MISMATCH")
        print(json.dumps({"release_id": RELEASE_ID, "archive_sha256": expected_hash,
            "source_commit": metadata.get("source_commit"),
            "runtime_file_count": len(contract["runtime_files"]),
            "source_matches_artifact": True, "result": "PASS"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
