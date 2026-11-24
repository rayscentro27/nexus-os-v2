import gzip
import hashlib
import json

import pytest

from scripts.nexus_agent_platform import transcript_artifacts as artifacts


def test_transcript_artifact_roundtrip_and_metadata(tmp_path, monkeypatch):
    root = tmp_path / "artifact-root"
    monkeypatch.setattr(artifacts, "ROOT", root)
    text = "A transcript with café and line breaks\nsecond line"
    metadata = artifacts.store_transcript("source-123", text, source_url="https://youtube.com/watch?v=x")
    body = root / "youtube/source-123/transcript.txt.gz"
    assert gzip.decompress(body.read_bytes()).decode("utf-8") == text
    assert metadata["SHA256"] == hashlib.sha256(text.encode()).hexdigest()
    assert metadata["BYTE_COUNT"] == len(text.encode())
    assert artifacts.load_transcript("source-123") == text
    assert json.loads((body.parent / "metadata.json").read_text())["SOURCE_ID"] == "source-123"


def test_transcript_artifact_rejects_corrupt_hash(tmp_path, monkeypatch):
    root = tmp_path / "artifact-root"
    monkeypatch.setattr(artifacts, "ROOT", root)
    artifacts.store_transcript("s1", "safe text")
    metadata_path = root / "youtube/s1/metadata.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["SHA256"] = "0" * 64
    metadata_path.write_text(json.dumps(metadata))
    with pytest.raises(IOError, match="HASH_MISMATCH"):
        artifacts.load_transcript("s1")


def test_transcript_source_id_is_sanitized(tmp_path, monkeypatch):
    monkeypatch.setattr(artifacts, "ROOT", tmp_path / "artifact-root")
    metadata = artifacts.store_transcript("../../unsafe/id", "body")
    assert ".." not in metadata["TRANSCRIPT_REF"]
