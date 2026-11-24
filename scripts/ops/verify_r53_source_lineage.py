#!/usr/bin/env python3
"""Verify the immutable R53 archive and exact packaged-source lineage."""
import hashlib
import json
import re
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASE = "nexus-capability-actions-20261024-r53"
ARCHIVE = ROOT / "dist" / f"{RELEASE}.tar.gz"
SIDECAR = ROOT / "dist" / f"{RELEASE}.sha256"
PREFIX = RELEASE + "/"
SECRETS = (re.compile(rb"https?://[^/\s:@]+:[^/\s@]+@", re.I),
           re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
           re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
           re.compile(rb"\bsk-[A-Za-z0-9]{24,}\b"))


def main() -> int:
    digest = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    if SIDECAR.read_text().split()[0] != digest:
        raise SystemExit("R53_ARCHIVE_SIDECAR_MISMATCH")
    with tarfile.open(ARCHIVE, "r:gz") as tar:
        members = [m for m in tar.getmembers() if m.isfile()]
        manifest = json.load(tar.extractfile(PREFIX + "R53_RELEASE_MANIFEST.json"))
        metadata = json.load(tar.extractfile(PREFIX + "BUILD_METADATA.json"))
        if manifest.get("release_id") != RELEASE or metadata.get("release_id") != RELEASE:
            raise SystemExit("R53_RELEASE_ID_MISMATCH")
        runtime = manifest.get("runtime_files", [])
        expected = {PREFIX + name for name in runtime} | {
            PREFIX + "R53_RELEASE_MANIFEST.json", PREFIX + "BUILD_METADATA.json",
            PREFIX + "certification/r53_certification.xml"}
        if {m.name for m in members} != expected:
            raise SystemExit("R53_ARCHIVE_CONTENT_SET_MISMATCH")
        for name, expected_hash in manifest.get("payload_sha256", {}).items():
            content = tar.extractfile(PREFIX + name).read()
            if hashlib.sha256(content).hexdigest() != expected_hash or content != (ROOT / name).read_bytes():
                raise SystemExit("R53_SOURCE_ARCHIVE_LINEAGE_MISMATCH:" + name)
        for member in members:
            content = tar.extractfile(member).read()
            if any(pattern.search(content) for pattern in SECRETS):
                raise SystemExit("R53_ARCHIVE_SECRET_SCAN_FAILED")
            if b"research_runtime_states.jsonl" in member.name.encode() or b"runtime.env" in member.name.encode():
                raise SystemExit("R53_PROHIBITED_RUNTIME_CONTENT")
    print(json.dumps({"release_id": RELEASE, "sha256": digest, "manifest_valid": True,
                      "source_match": True, "secret_scan_pass": True,
                      "runtime_file_count": len(runtime)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
