"""Local source-transcript artifacts; bodies stay outside Supabase and Git."""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_ROOT = Path.home() / ".nexus" / "artifacts" / "transcripts"
ROOT = Path(os.environ.get("NEXUS_TRANSCRIPT_ARTIFACT_ROOT", str(DEFAULT_ROOT))).expanduser().resolve()
_REPO_ROOT = Path(__file__).resolve().parents[2]
try:
    ROOT.relative_to(_REPO_ROOT)
except ValueError:
    pass
else:
    raise RuntimeError("TRANSCRIPT_ARTIFACT_ROOT_MUST_BE_OUTSIDE_GIT")


def _safe_id(source_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", str(source_id)).strip("._")
    if not safe or safe in {".", ".."}:
        raise ValueError("INVALID_TRANSCRIPT_SOURCE_ID")
    return safe[:180]


def _paths(source_id: str, source_type: str = "YOUTUBE") -> tuple[Path, Path, str]:
    source_key = _safe_id(source_id)
    family = "youtube" if "YOUTUBE" in str(source_type).upper() else "sources"
    directory = (ROOT / family / source_key).resolve()
    directory.relative_to(ROOT)
    return directory / "transcript.txt.gz", directory / "metadata.json", f"{family}/{source_key}/transcript.txt.gz"


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(ROOT, 0o700)
        os.chmod(path.parent.parent, 0o700)
        os.chmod(path.parent, 0o700)
    except OSError:
        pass
    fd, temp = tempfile.mkstemp(prefix=".transcript-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp, 0o600)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def store_transcript(source_id: str, transcript: str, *, source_url: str | None = None,
                     source_type: str = "YOUTUBE") -> dict[str, Any]:
    if not isinstance(transcript, str) or not transcript.strip():
        raise ValueError("EMPTY_TRANSCRIPT")
    raw = transcript.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    body_path, metadata_path, reference = _paths(source_id, source_type)
    compressed = gzip.compress(raw, mtime=0)
    metadata = {
        "SOURCE_ID": _safe_id(source_id), "SOURCE_URL": source_url,
        "CREATED_AT": datetime.now(timezone.utc).isoformat(),
        "CHAR_COUNT": len(transcript), "BYTE_COUNT": len(raw), "SHA256": digest,
        "FORMAT": "UTF-8_TEXT", "COMPRESSION": "GZIP", "COMPRESSED_BYTE_COUNT": len(compressed),
        "TRANSCRIPT_REF": reference,
    }
    _atomic_write(body_path, compressed)
    _atomic_write(metadata_path, (json.dumps(metadata, ensure_ascii=False, separators=(",", ":")) + "\n").encode())
    verified = load_transcript(source_id, metadata=metadata, source_type=source_type)
    if verified != transcript:
        raise IOError("TRANSCRIPT_ARTIFACT_READBACK_MISMATCH")
    return metadata


def load_transcript(source_id: str, *, metadata: dict[str, Any] | None = None,
                    source_type: str = "YOUTUBE") -> str | None:
    body_path, metadata_path, _ = _paths(source_id, source_type)
    if not body_path.is_file():
        return None
    stored = metadata
    if stored is None:
        try:
            stored = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            stored = None
    raw = gzip.decompress(body_path.read_bytes())
    text = raw.decode("utf-8")
    if stored:
        digest = hashlib.sha256(raw).hexdigest()
        if stored.get("SOURCE_ID") not in (None, _safe_id(source_id)) or stored.get("SHA256") not in (None, digest):
            raise IOError("TRANSCRIPT_ARTIFACT_HASH_MISMATCH")
        if stored.get("BYTE_COUNT") not in (None, len(raw)):
            raise IOError("TRANSCRIPT_ARTIFACT_SIZE_MISMATCH")
    return text


def metadata_for(source_id: str, *, source_type: str = "YOUTUBE") -> dict[str, Any] | None:
    _, path, _ = _paths(source_id, source_type)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
