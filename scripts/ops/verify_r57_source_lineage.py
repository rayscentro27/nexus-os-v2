#!/usr/bin/env python3
"""Verify the exact R57 archive, active manifest, R56 ancestry and added migration."""
from __future__ import annotations
import hashlib, json, os, sys, tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASE_ID = "nexus-capability-actions-20261025-r57"
ARCHIVE = ROOT / "dist" / f"{RELEASE_ID}.tar.gz"
EXPECTED = os.environ.get("R57_EXPECTED_SHA256")

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> int:
    actual = sha(ARCHIVE)
    sidecar = ROOT / "dist" / f"{RELEASE_ID}.sha256"
    if sidecar.read_text().split()[0] != actual or (EXPECTED and actual != EXPECTED):
        raise SystemExit("R57_ARCHIVE_SHA_MISMATCH")
    with tarfile.open(ARCHIVE, "r:gz") as tar:
        root = f"{RELEASE_ID}/"
        manifest_path = root + "R57_RELEASE_MANIFEST.json"
        manifest = json.load(tar.extractfile(manifest_path))
        if manifest["release_id"] != RELEASE_ID or manifest["base_release_id"] != "nexus-capability-actions-20261025-r56":
            raise SystemExit("R57_RELEASE_IDENTITY_MISMATCH")
        checksum = hashlib.sha256(tar.extractfile(manifest_path).read()).hexdigest()
        sidecar_data = tar.extractfile(root + "RELEASE_MANIFEST.sha256").read().decode().split()[0]
        if checksum != sidecar_data:
            raise SystemExit("R57_MANIFEST_SIDECAR_MISMATCH")
        members = {m.name: m for m in tar.getmembers()}
        for relative, expected in manifest["payload_sha256"].items():
            member = members.get(root + relative)
            if not member or not member.isfile():
                raise SystemExit("R57_PAYLOAD_MISSING:" + relative)
            if hashlib.sha256(tar.extractfile(member).read()).hexdigest() != expected:
                raise SystemExit("R57_PAYLOAD_HASH_MISMATCH:" + relative)
        metadata = json.load(tar.extractfile(root + "BUILD_METADATA.json"))
        if hashlib.sha256(tar.extractfile(root + "BUILD_METADATA.json").read()).hexdigest() != manifest["build_metadata_sha256"]:
            raise SystemExit("R57_BUILD_METADATA_HASH_MISMATCH")
        if metadata.get("release_id") != RELEASE_ID or metadata.get("source_commit") != manifest.get("source_commit"):
            raise SystemExit("R57_BUILD_METADATA_IDENTITY_MISMATCH")
        migration = "supabase/migrations/20261025150000_nexus_governor_reservation_ordering_fix.sql"
        source_hash = hashlib.sha256((ROOT / migration).read_bytes()).hexdigest()
        if manifest["payload_sha256"].get(migration) != source_hash:
            raise SystemExit("R57_MIGRATION_SOURCE_MISMATCH")
        if root + "R56_RELEASE_MANIFEST.json" not in members or root + "R55_RELEASE_MANIFEST.json" in members:
            raise SystemExit("R57_ROOT_BASE_MANIFEST_LAYOUT_INVALID")
    release_root = ROOT / "dist" / RELEASE_ID
    sys.path.insert(0, str(release_root / "scripts"))
    os.environ["NEXUS_ACTIVE_RESEARCH_RELEASE"] = str(release_root)
    from nexus_agent_platform.stability_supervisor import _active_state_v2_release
    resolved = _active_state_v2_release()
    if resolved != (RELEASE_ID, True):
        raise SystemExit("R57_ACTIVE_RELEASE_READINESS_RESOLUTION_FAILED:" + repr(resolved))
    print(json.dumps({"result":"PASS", "sha256":actual, "payload_files":len(manifest["payload_sha256"]),
                      "source_commit":manifest["source_commit"], "readiness_resolution":resolved}, sort_keys=True))
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
