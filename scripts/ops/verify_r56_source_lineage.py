#!/usr/bin/env python3
"""Verify the built R56 archive against the pinned R55 base and R56 overlay."""
from __future__ import annotations

import hashlib
import json
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = json.loads((ROOT / "certification/r56_source/contract.json").read_text())
RELEASE_ID = CONTRACT["release_id"]
RELEASE = ROOT / "dist" / RELEASE_ID
ARCHIVE = ROOT / "dist" / f"{RELEASE_ID}.tar.gz"
SIDECAR = ROOT / "dist" / f"{RELEASE_ID}.sha256"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


manifest = json.loads((RELEASE / "R56_RELEASE_MANIFEST.json").read_text())
payload = manifest.get("payload_sha256", {})
if manifest.get("release_id") != RELEASE_ID or len(payload) != manifest.get("payload_file_count"):
    raise SystemExit("R56_RELEASE_MANIFEST_INVALID")
for relative, expected in payload.items():
    path = RELEASE / relative
    if not path.is_file() or sha(path) != expected:
        raise SystemExit(f"R56_RELEASE_PAYLOAD_MISMATCH:{relative}")
base_manifest = json.loads((ROOT / CONTRACT["base_manifest_path"]).read_text())
for relative, expected in base_manifest["payload_sha256"].items():
    if relative in CONTRACT["overlay_runtime_files"]:
        continue
    if sha(RELEASE / relative) != expected:
        raise SystemExit(f"R55_BASE_LINEAGE_MISMATCH:{relative}")
for relative in CONTRACT["overlay_runtime_files"]:
    if sha(RELEASE / relative) != sha(ROOT / CONTRACT["overlay_source_directory"] / relative):
        raise SystemExit(f"R56_OVERLAY_LINEAGE_MISMATCH:{relative}")
side_hash = SIDECAR.read_text().split()[0]
if side_hash != sha(ARCHIVE):
    raise SystemExit("R56_ARCHIVE_SIDECAR_MISMATCH")
with tempfile.TemporaryDirectory(prefix="r56-lineage-") as temp:
    with tarfile.open(ARCHIVE, "r:gz") as tar:
        members = tar.getmembers()
        if any(Path(member.name).is_absolute() or ".." in Path(member.name).parts for member in members):
            raise SystemExit("R56_ARCHIVE_PATH_TRAVERSAL")
        tar.extractall(temp, filter="data")
    extracted = Path(temp) / RELEASE_ID
    for relative, expected in payload.items():
        if sha(extracted / relative) != expected:
            raise SystemExit(f"R56_ARCHIVE_SOURCE_MISMATCH:{relative}")
print(json.dumps({"result": "PASS", "release_id": RELEASE_ID,
                  "artifact_sha256": sha(ARCHIVE), "payload_files": len(payload),
                  "source_artifact_match": True}, sort_keys=True))
