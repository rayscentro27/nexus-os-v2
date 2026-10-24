#!/usr/bin/env python3
"""Verify R55 archive hash, base/overlay lineage, and certified commit."""
from __future__ import annotations

import hashlib
import json
import os
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASE_ID = "nexus-capability-actions-20261024-r55"
ARCHIVE = ROOT / "dist" / f"{RELEASE_ID}.tar.gz"
SIDECAR = ROOT / "dist" / f"{RELEASE_ID}.sha256"
CONTRACT_PATH = ROOT / "config/r55_deployable_release_manifest.v1.json"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha(path: Path) -> str:
    return digest(path.read_bytes())


def main() -> int:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    expected, _ = SIDECAR.read_text(encoding="utf-8").split()
    if sha(ARCHIVE) != expected:
        raise SystemExit("R55_ARCHIVE_SIDECAR_MISMATCH")
    expected_commit = os.environ.get("GITHUB_SHA")
    with tempfile.TemporaryDirectory(prefix="nexus-r55-lineage-") as tmp:
        root = Path(tmp).resolve()
        with tarfile.open(ARCHIVE, "r:gz") as tar:
            for member in tar.getmembers():
                path = (root / member.name).resolve()
                if not path.is_relative_to(root):
                    raise SystemExit("R55_ARCHIVE_PATH_TRAVERSAL")
                if member.issym() or member.islnk():
                    raise SystemExit("R55_ARCHIVE_LINK_REFUSED")
            tar.extractall(root)
        release = root / RELEASE_ID
        manifest = json.loads((release / "R55_RELEASE_MANIFEST.json").read_text())
        metadata = json.loads((release / "BUILD_METADATA.json").read_text())
        if manifest.get("release_id") != RELEASE_ID or metadata.get("release_id") != RELEASE_ID:
            raise SystemExit("R55_RELEASE_ID_MISMATCH")
        if (manifest.get("base_release", {}).get("release_id") != "nexus-capability-actions-20261024-r53"
                or manifest.get("overlay_release", {}).get("release_id") != "nexus-capability-actions-20261024-r54"):
            raise SystemExit("R55_COMPOSITION_LINEAGE_MISMATCH")
        manifest_sidecar, _ = (release / "RELEASE_MANIFEST.sha256").read_text().split()
        if sha(release / "R55_RELEASE_MANIFEST.json") != manifest_sidecar:
            raise SystemExit("R55_MANIFEST_SIDECAR_MISMATCH")
        if expected_commit and metadata.get("source_commit") != expected_commit:
            raise SystemExit("R55_CERTIFIED_COMMIT_MISMATCH")
        errors = []
        for rel, want in manifest.get("payload_sha256", {}).items():
            packaged = release / rel
            if not packaged.is_file() or sha(packaged) != want:
                errors.append(rel)
        if errors:
            raise SystemExit("R55_PACKAGED_PAYLOAD_MISMATCH:" + ",".join(errors))
        overlay = manifest["overlay_release"]
        base = manifest["base_release"]
        replaced_paths = set(overlay["payload_sha256"])
        for rel, want in base["payload_sha256"].items():
            if rel not in replaced_paths and sha(release / rel) != want:
                raise SystemExit(f"R55_BASE_LINEAGE_MISMATCH:{rel}")
        for rel, want in overlay["payload_sha256"].items():
            if sha(release / rel) != want:
                raise SystemExit(f"R55_OVERLAY_LINEAGE_MISMATCH:{rel}")
        launcher = (release / "scripts/ops/nexus_mcp_bridge.sh").read_text()
        if 'ROOT="$(cd "$SCRIPT_DIR/../.." && pwd -P)"' not in launcher:
            raise SystemExit("R55_LAUNCHER_ROOT_NOT_SELF_RESOLVED")
        if 'export PYTHONPATH="$ROOT:$ROOT/scripts"' not in launcher:
            raise SystemExit("R55_LAUNCHER_PYTHONPATH_NOT_SELF")
        for entry in ("scripts/ops/nexus_mcp_bridge.sh", "services/nexus_mcp/http_server.py",
                      "scripts/nexus_agent_platform/job_worker_once.py"):
            if not (release / entry).is_file():
                raise SystemExit(f"R55_ENTRYPOINT_MISSING:{entry}")
        print(json.dumps({"result": "PASS", "archive_sha256": expected,
            "source_commit": metadata.get("source_commit"),
            "runtime_file_count": manifest.get("runtime_file_count"),
            "source_matches_artifact": True,
            "base_release_id": base["release_id"],
            "overlay_release_id": overlay["release_id"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
