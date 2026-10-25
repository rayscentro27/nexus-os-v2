#!/usr/bin/env python3
"""Stage exact certified R57 plus the explicitly listed R58 runtime files."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = json.loads((ROOT / "certification/r58_source/contract.json").read_text())
BASE = Path(os.environ["R57_RELEASE_ROOT"]).resolve()
OUTPUT = Path(os.environ["R58_TEST_ROOT"]).resolve()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if BASE.name != CONTRACT["base_release_id"] or not BASE.is_dir():
        raise SystemExit("R57_BASE_ROOT_INVALID")
    if sha(BASE / "R57_RELEASE_MANIFEST.json") != CONTRACT["base_manifest_sha256"]:
        raise SystemExit("R57_BASE_MANIFEST_MISMATCH")
    manifest = json.loads((BASE / "R57_RELEASE_MANIFEST.json").read_text())
    if manifest.get("source_commit") != CONTRACT["base_source_commit"]:
        raise SystemExit("R57_BASE_COMMIT_MISMATCH")
    for relative, expected in manifest["payload_sha256"].items():
        path = BASE / relative
        if not path.is_file() or sha(path) != expected:
            raise SystemExit("R57_BASE_PAYLOAD_MISMATCH:" + relative)
    if OUTPUT.exists():
        raise SystemExit("R58_TEST_ROOT_ALREADY_EXISTS")
    shutil.copytree(BASE, OUTPUT, symlinks=True)
    older_manifest = OUTPUT / "R56_RELEASE_MANIFEST.json"
    if not older_manifest.is_file():
        raise SystemExit("R57_IMMEDIATE_BASE_MANIFEST_MISSING")
    lineage = OUTPUT / "certification/lineage"
    lineage.mkdir(parents=True, exist_ok=True)
    shutil.move(str(older_manifest), str(lineage / older_manifest.name))
    for relative in CONTRACT["changed_runtime_files"]:
        source = ROOT / relative
        if not source.is_file():
            raise SystemExit("R58_RUNTIME_SOURCE_MISSING:" + relative)
        target = OUTPUT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    print(json.dumps({"result": "PASS", "base_release": manifest["release_id"],
                      "test_root": str(OUTPUT),
                      "overlay_files": CONTRACT["changed_runtime_files"]}, sort_keys=True))


if __name__ == "__main__":
    main()
