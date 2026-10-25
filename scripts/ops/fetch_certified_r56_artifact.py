#!/usr/bin/env python3
"""Fetch and validate the exact certified R56 Actions artifact for R57 composition."""
from __future__ import annotations
import hashlib, json, os, shutil, tarfile, urllib.error, urllib.request, zipfile
from io import BytesIO
from pathlib import Path

REPO = os.environ["GITHUB_REPOSITORY"]
TOKEN = os.environ["GITHUB_TOKEN"]
API = os.environ.get("GITHUB_API_URL", "https://api.github.com")
RUN = "40201626578"
NAME = "nexus-capability-actions-20261025-r56"
EXPECTED = "a6d1bc14d2b50985f541cf7bc823f8b09e20dc22ecad5b95ba059a78fccfd263"
ROOT = Path.cwd()
OUT = ROOT / "dist/r56-certified.tar.gz"
EXTRACT = Path(os.environ["R56_ARTIFACT_EXTRACT_ROOT"])

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def get_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def download_api(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request, timeout=30) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        if error.code != 302 or not error.headers.get("Location"):
            raise
        with urllib.request.urlopen(error.headers["Location"], timeout=60) as response:
            return response.read()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    if OUT.exists() or EXTRACT.exists():
        raise SystemExit("R56_FETCH_OUTPUT_EXISTS")
    listing = get_json(f"{API}/repos/{REPO}/actions/runs/{RUN}/artifacts?per_page=100")
    matches = [item for item in listing.get("artifacts", []) if item.get("name") == NAME and not item.get("expired")]
    if len(matches) != 1:
        raise SystemExit("CERTIFIED_R56_ARTIFACT_NOT_UNIQUE")
    data = download_api(matches[0]["archive_download_url"])
    with zipfile.ZipFile(BytesIO(data)) as zf:
        names = [n for n in zf.namelist() if n.endswith(f"/{NAME}.tar.gz") or n == f"{NAME}.tar.gz"]
        if len(names) != 1:
            raise SystemExit("CERTIFIED_R56_ARCHIVE_MEMBER_NOT_UNIQUE")
        archive_bytes = zf.read(names[0])
    if sha(archive_bytes) != EXPECTED:
        raise SystemExit("CERTIFIED_R56_ARCHIVE_SHA_MISMATCH")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(archive_bytes)
    EXTRACT.mkdir(parents=True)
    with tarfile.open(OUT, "r:gz") as archive:
        root_name = f"{NAME}/"
        members = archive.getmembers()
        for member in members:
            path = Path(member.name)
            if path.is_absolute() or ".." in path.parts or not (member.isdir() or member.isfile()):
                raise SystemExit("UNSAFE_R56_ARCHIVE_MEMBER")
        archive.extractall(EXTRACT, members=members)
    release = EXTRACT / NAME
    manifest_path = release / "R56_RELEASE_MANIFEST.json"
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != "06db40614cda9cdb1aee78a813d29660a646d2951343deeea05aa9013f2765f9":
        raise SystemExit("CERTIFIED_R56_MANIFEST_SHA_MISMATCH")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("source_commit") != "4de0c1096b509561af75f81519210353d6f90a80" or manifest.get("certification", {}).get("result") != "PASS":
        raise SystemExit("CERTIFIED_R56_LINEAGE_MISMATCH")
    for relative, expected in manifest["payload_sha256"].items():
        path = release / relative
        if not path.is_file() or sha(path.read_bytes()) != expected:
            raise SystemExit("CERTIFIED_R56_PAYLOAD_MISMATCH:" + relative)
    print(json.dumps({"result":"PASS", "release_root":str(release), "archive_sha256":EXPECTED,
                      "payload_files":len(manifest["payload_sha256"])}))

if __name__ == "__main__":
    main()
