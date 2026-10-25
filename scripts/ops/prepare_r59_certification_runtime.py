#!/usr/bin/env python3
"""Stage exact certified R58 and overlay only the declared R59 changes."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = json.loads((ROOT / "certification/r59_source/contract.json").read_text())
BASE = Path(os.environ["R58_RELEASE_ROOT"]).resolve()
OUTPUT = Path(os.environ["R59_TEST_ROOT"]).resolve()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    manifest_path = BASE / "R58_RELEASE_MANIFEST.json"
    if BASE.name != CONTRACT["base_release_id"] or not BASE.is_dir():
        raise SystemExit("R58_BASE_ROOT_INVALID")
    if sha(manifest_path) != CONTRACT["base_manifest_sha256"]:
        raise SystemExit("R58_BASE_MANIFEST_MISMATCH")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("source_commit") != CONTRACT["base_source_commit"]:
        raise SystemExit("R58_BASE_COMMIT_MISMATCH")
    for relative, expected in manifest["payload_sha256"].items():
        path = BASE / relative
        if not path.is_file() or sha(path) != expected:
            raise SystemExit("R58_BASE_PAYLOAD_MISMATCH:" + relative)
    if OUTPUT.exists():
        raise SystemExit("R59_TEST_ROOT_ALREADY_EXISTS")
    shutil.copytree(BASE, OUTPUT, symlinks=True)
    old_manifest = OUTPUT / "R57_RELEASE_MANIFEST.json"
    lineage = OUTPUT / "certification/lineage"
    lineage.mkdir(parents=True, exist_ok=True)
    if not old_manifest.is_file():
        raise SystemExit("R58_IMMEDIATE_BASE_MANIFEST_MISSING")
    shutil.move(str(old_manifest), str(lineage / old_manifest.name))
    shutil.move(str(OUTPUT / "R58_RELEASE_MANIFEST.json"), str(lineage / "R58_RELEASE_MANIFEST.json"))
    (OUTPUT / "RELEASE_MANIFEST.sha256").unlink(missing_ok=True)
    (OUTPUT / "BUILD_METADATA.json").unlink(missing_ok=True)
    for relative in CONTRACT["changed_runtime_files"]:
        source = ROOT / relative
        if not source.is_file():
            raise SystemExit("R59_OVERLAY_FILE_MISSING:" + relative)
        target = OUTPUT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    print(json.dumps({"result": "PASS", "base_release": manifest["release_id"],
                      "test_root": str(OUTPUT), "overlay_files": CONTRACT["changed_runtime_files"]}, sort_keys=True))


if __name__ == "__main__":
    main()
