#!/usr/bin/env python3
"""Fetch and verify the exact certified R57 Actions artifact for R58 composition."""
from __future__ import annotations

import hashlib
import json
import os
import tarfile
import urllib.error
import urllib.request
import zipfile
from io import BytesIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = json.loads((ROOT / "certification/r58_source/contract.json").read_text())
REPO = os.environ["GITHUB_REPOSITORY"]
TOKEN = os.environ["GITHUB_TOKEN"]
API = os.environ.get("GITHUB_API_URL", "https://api.github.com")
RUN = CONTRACT["base_run_id"]
NAME = CONTRACT["base_artifact_name"]
EXPECTED = CONTRACT["base_artifact_sha256"]
OUT = ROOT / "dist/r57-certified.tar.gz"
EXTRACT = Path(os.environ["R57_ARTIFACT_EXTRACT_ROOT"])


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _get_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def _download_artifact(url: str) -> bytes:
    request = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"})
    try:
        with urllib.request.build_opener(_NoRedirect).open(request, timeout=30) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        if error.code != 302 or not error.headers.get("Location"):
            raise
        with urllib.request.urlopen(error.headers["Location"], timeout=60) as response:
            return response.read()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    if OUT.exists() or EXTRACT.exists():
        raise SystemExit("R57_FETCH_OUTPUT_EXISTS")
    listing = _get_json(f"{API}/repos/{REPO}/actions/runs/{RUN}/artifacts?per_page=100")
    matches = [item for item in listing.get("artifacts", [])
               if item.get("name") == NAME and not item.get("expired")]
    if len(matches) != 1:
        raise SystemExit("CERTIFIED_R57_ARTIFACT_NOT_UNIQUE")
    with zipfile.ZipFile(BytesIO(_download_artifact(matches[0]["archive_download_url"]))) as zf:
        names = [name for name in zf.namelist() if name.endswith(f"/{NAME}.tar.gz") or name == f"{NAME}.tar.gz"]
        if len(names) != 1:
            raise SystemExit("CERTIFIED_R57_ARCHIVE_MEMBER_NOT_UNIQUE")
        archive_bytes = zf.read(names[0])
    if _sha(archive_bytes) != EXPECTED:
        raise SystemExit("CERTIFIED_R57_ARCHIVE_SHA_MISMATCH")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(archive_bytes)
    EXTRACT.mkdir(parents=True)
    with tarfile.open(OUT, "r:gz") as archive:
        members = archive.getmembers()
        prefix = f"{NAME}/"
        for member in members:
            path = Path(member.name)
            if path.is_absolute() or ".." in path.parts or not (member.isdir() or member.isfile()):
                raise SystemExit("UNSAFE_R57_ARCHIVE_MEMBER")
            if member.name == NAME and member.isdir():
                continue
            if not member.name.startswith(prefix):
                raise SystemExit("R57_ARCHIVE_ROOT_MISMATCH")
        archive.extractall(EXTRACT, members=members)
    release = EXTRACT / NAME
    manifest_path = release / "R57_RELEASE_MANIFEST.json"
    if _sha(manifest_path.read_bytes()) != CONTRACT["base_manifest_sha256"]:
        raise SystemExit("CERTIFIED_R57_MANIFEST_SHA_MISMATCH")
    manifest = json.loads(manifest_path.read_text())
    if (manifest.get("source_commit") != CONTRACT["base_source_commit"]
            or manifest.get("release_id") != NAME
            or manifest.get("certification", {}).get("result") != "PASS"):
        raise SystemExit("CERTIFIED_R57_LINEAGE_MISMATCH")
    for relative, expected in manifest["payload_sha256"].items():
        path = release / relative
        if not path.is_file() or _sha(path.read_bytes()) != expected:
            raise SystemExit("CERTIFIED_R57_PAYLOAD_MISMATCH:" + relative)
    print(json.dumps({"result": "PASS", "release_root": str(release),
                      "archive_sha256": EXPECTED, "payload_files": len(manifest["payload_sha256"])}))


if __name__ == "__main__":
    main()
