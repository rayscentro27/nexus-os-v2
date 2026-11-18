#!/usr/bin/env python3
"""Build a size-bounded ZIP and hash manifest from declared outputs only."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import zipfile
from pathlib import Path

try:
    from secret_guard import redact_text
except ImportError:
    from scripts.systems.secret_guard import redact_text

MAX_FILES = 200
MAX_FILE_BYTES = 100 * 1024 * 1024
MAX_TOTAL_BYTES = 500 * 1024 * 1024
SECRET_NAME_RE = __import__("re").compile(r"(?i)(^|[/_.-])(\.env|credentials?|secrets?|private[_-]?key|token)([/_.-]|$)")


def package_outputs(workdir: Path, job_id: str, outputs: list[str]) -> dict:
    root = workdir.resolve()
    if not outputs or len(outputs) > MAX_FILES or not job_id.replace("-", "").replace("_", "").isalnum():
        raise ValueError("OUTPUT_LIST_INVALID")
    files = []
    total = 0
    for rel in outputs:
        candidate = Path(rel)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError("OUTPUT_PATH_INVALID")
        path = (root / candidate).resolve()
        if root not in path.parents or path.is_symlink() or not path.is_file():
            raise ValueError("OUTPUT_NOT_REGULAR_FILE")
        name = path.relative_to(root).as_posix()
        if SECRET_NAME_RE.search(name):
            raise ValueError("SECRET_NAMED_OUTPUT_REJECTED")
        size = path.stat().st_size
        if size > MAX_FILE_BYTES:
            raise ValueError("OUTPUT_FILE_SIZE_LIMIT")
        total += size
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if path.suffix.lower() in {".txt", ".md", ".json", ".csv", ".log", ".yaml", ".yml"}:
            content = path.read_text(encoding="utf-8", errors="ignore")
            if redact_text(content) != content:
                raise ValueError("POTENTIAL_SECRET_IN_OUTPUT")
        files.append({"path": name, "size_bytes": size, "sha256": digest})
    if total > MAX_TOTAL_BYTES:
        raise ValueError("OUTPUT_TOTAL_SIZE_LIMIT")
    manifest = {"schema_version": "nexus.external-artifact-manifest.v1", "job_id": job_id, "files": files, "total_size_bytes": total}
    out_dir = root / "outputs" / "packages"
    out_dir.mkdir(parents=True, exist_ok=True)
    archive = out_dir / f"{job_id}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for entry in files:
            z.write(root / entry["path"], arcname=entry["path"])
        z.writestr("result_manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    sidecar = {**manifest, "archive": archive.name, "archive_size_bytes": archive.stat().st_size, "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest()}
    sidecar_path = archive.with_suffix(".manifest.json")
    sidecar_path.write_text(json.dumps(sidecar, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return sidecar


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workdir", type=Path, required=True)
    p.add_argument("--job-id", required=True)
    p.add_argument("--output", action="append", required=True)
    a = p.parse_args()
    try:
        print(json.dumps(package_outputs(a.workdir, a.job_id, a.output), sort_keys=True))
        return 0
    except (OSError, ValueError) as exc:
        from secret_guard import redact_text
        print(json.dumps({"status": "FAILED", "error": redact_text(str(exc))}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
