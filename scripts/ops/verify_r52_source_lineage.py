#!/usr/bin/env python3
"""Verify the existing immutable r52 archive against this checkout; never rebuild."""
from __future__ import annotations

import hashlib
import json
import re
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RELEASE_ID = "nexus-capability-actions-20261023-r52"
EXPECTED_ARCHIVE_SHA256 = "701cb202618bbf9be4f0f350f39f25a9babb973bb77e6c467ccd9fb5af9433ec"
ARCHIVE = ROOT / "dist" / f"{RELEASE_ID}.tar.gz"
SIDECAR = ROOT / "dist" / f"{RELEASE_ID}.sha256"
RUNTIME_PREFIX = f"{RELEASE_ID}/"
SECRET_PATTERNS = {
    "uri_userinfo": re.compile(rb"https?://[^/\s:@]+:[^/\s@]+@", re.I),
    "private_key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "provider_key": re.compile(rb"\bsk-[A-Za-z0-9]{24,}\b"),
    "jwt_like": re.compile(rb"\beyJ[A-Za-z0-9_-]{30,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\b"),
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    if not ARCHIVE.is_file() or not SIDECAR.is_file():
        raise SystemExit("R52_EXISTING_ARCHIVE_OR_SIDECAR_MISSING")
    archive_bytes = ARCHIVE.read_bytes()
    archive_sha = sha256(archive_bytes)
    sidecar = SIDECAR.read_text(encoding="utf-8").split()
    if archive_sha != EXPECTED_ARCHIVE_SHA256 or not sidecar or sidecar[0] != EXPECTED_ARCHIVE_SHA256:
        raise SystemExit("R52_EXISTING_ARCHIVE_SHA256_MISMATCH")

    expected_files: set[str] = set()
    with tarfile.open(ARCHIVE, "r:gz") as archive:
        members = [member for member in archive.getmembers() if member.isfile()]
        manifest_member = archive.extractfile(f"{RUNTIME_PREFIX}R52_RELEASE_MANIFEST.json")
        metadata_member = archive.extractfile(f"{RUNTIME_PREFIX}BUILD_METADATA.json")
        if manifest_member is None or metadata_member is None:
            raise SystemExit("R52_ARCHIVE_METADATA_MISSING")
        manifest = json.load(manifest_member)
        metadata = json.load(metadata_member)
        if manifest.get("release_id") != RELEASE_ID or metadata.get("release_id") != RELEASE_ID:
            raise SystemExit("R52_ARCHIVE_RELEASE_ID_MISMATCH")
        runtime = manifest.get("runtime_files")
        payload_hashes = manifest.get("payload_sha256")
        if not isinstance(runtime, list) or len(runtime) != 9 or set(runtime) != set(payload_hashes or {}):
            raise SystemExit("R52_ARCHIVE_RUNTIME_MANIFEST_INVALID")
        expected_files = {f"{RUNTIME_PREFIX}{path}" for path in runtime}
        expected_files |= {
            f"{RUNTIME_PREFIX}R52_RELEASE_MANIFEST.json",
            f"{RUNTIME_PREFIX}BUILD_METADATA.json",
            f"{RUNTIME_PREFIX}certification/r52_certification.xml",
        }
        actual_files = {member.name for member in members}
        if actual_files != expected_files:
            raise SystemExit("R52_ARCHIVE_CONTENT_SET_MISMATCH")

        for relative, expected_hash in payload_hashes.items():
            local = (ROOT / relative).read_bytes()
            packaged_stream = archive.extractfile(f"{RUNTIME_PREFIX}{relative}")
            if packaged_stream is None or sha256(local) != expected_hash or packaged_stream.read() != local:
                raise SystemExit(f"R52_SOURCE_ARCHIVE_LINEAGE_MISMATCH:{relative}")

        secret_counts = {name: 0 for name in SECRET_PATTERNS}
        for member in members:
            stream = archive.extractfile(member)
            data = stream.read() if stream else b""
            for name, pattern in SECRET_PATTERNS.items():
                secret_counts[name] += len(pattern.findall(data))
        if any(secret_counts.values()):
            raise SystemExit("R52_ARCHIVE_SECRET_SCAN_FAILED")
        if any("research_runtime_states.jsonl" in member.name or "runtime.env" in member.name
               for member in members):
            raise SystemExit("R52_ARCHIVE_PROHIBITED_RUNTIME_CONTENT")

    print(json.dumps({"release_id": RELEASE_ID, "archive_sha256": archive_sha,
        "runtime_file_count": len(runtime), "source_payload_match": True,
        "manifest_valid": True, "secret_scan_pass": True,
        "production_state_and_legacy_ledger_absent": True}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
