from pathlib import Path

from alpha.youtube_provenance import downstream_handoff_allowed, persist_asr_required, persist_transcript_artifact, validation_result


def test_transcript_boolean_without_artifact_is_rejected(tmp_path: Path):
    try:
        persist_transcript_artifact(tmp_path, video={"video_id": "v"}, result={"status": "TRANSCRIPT_RETRIEVED", "transcript": ""})
    except ValueError as exc:
        assert str(exc) == "TRANSCRIPT_EMPTY"
    else:
        raise AssertionError("empty transcript was accepted")


def test_claim_validation_is_always_attempted():
    result = validation_result(claim={"claim_id": "c"}, supporting=[], contradicting=[])
    assert result["validation_attempted"] is True
    assert result["validation_result"] == "UNVERIFIED"
    assert result["evidence_source_count"] == 0


def test_unvalidated_business_handoff_is_forbidden():
    assert downstream_handoff_allowed(validation={"validation_result": "UNVERIFIED"}) is False
    assert downstream_handoff_allowed(validation={"validation_result": "VALIDATED"}) is True


def test_transcript_artifact_contains_durable_provenance(tmp_path: Path):
    item = persist_transcript_artifact(tmp_path, video={"video_id": "v", "channel_name": "C"}, result={"transcript": "real evidence", "transcript_method": "AUTO_CAPTION", "retrieved_at": "now"})
    assert item["transcript_status"] == "TRANSCRIPT_RETRIEVED"
    assert item["transcript_length_chars"] == len("real evidence")
    assert (tmp_path / item["transcript_artifact_path"]).exists()


def test_caption_failure_is_queueable_without_portfolio_stop(monkeypatch):
    captured = []
    monkeypatch.setattr("alpha.youtube_provenance.append_record", lambda collection, record: captured.append((collection, record)))
    row = persist_asr_required(video={"video_id": "v", "video_url": "https://youtube.com/watch?v=v", "channel_name": "C", "created_at": "now"}, failure_reason="CAPTION_TIMEOUT")
    assert row["status"] == "ASR_REQUIRED"
    assert captured[0][0] == "youtube_asr_jobs"
