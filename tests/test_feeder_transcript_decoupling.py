from nexus_agent_platform import feeder_runtime as feeder
from nexus_agent_platform import transcript_artifacts


def test_questionnaire_prefers_local_artifact_and_never_reads_legacy_column(tmp_path, monkeypatch):
    monkeypatch.setattr(transcript_artifacts, "ROOT", tmp_path / "artifacts")
    source_id = "source-yt-1"
    text = "source transcript for local analysis"
    transcript_artifacts.store_transcript(source_id, text, source_type="YOUTUBE")
    calls = []

    def request(path, method="GET", body=None, prefer="return=minimal"):
        calls.append((path, method, body))
        if "nexus_feeder_templates?" in path:
            return [{"version": "v1", "prompt_body": "fixed questionnaire"}]
        return []

    analyzed = []
    monkeypatch.setattr(feeder, "_request", request)
    monkeypatch.setattr(feeder, "_analyze_unstructured_source", lambda row, template: analyzed.append(row["transcript_or_extract"]) or {"SOURCE_CLAIMS": []})
    monkeypatch.setattr(feeder, "_gaps", lambda *_: [])
    monkeypatch.setattr(feeder, "create_handoff", lambda *args, **kwargs: None)
    monkeypatch.setattr(feeder, "create_research_handoff", lambda *args, **kwargs: None)
    row = {"source_id": source_id, "feeder_type": "BUSINESS_FUNDING_FEEDER", "source_type": "YOUTUBE",
           "source_title": "Funding source", "source_url": "https://youtube.com/watch?v=one",
           "notebook_output": {}, "structured_input": {}}
    feeder.run_questionnaire(source_id, row=row)
    assert analyzed == [text]
    assert not any("select=transcript_or_extract" in path for path, _, _ in calls)


def test_new_intake_body_never_contains_transcript_column(tmp_path, monkeypatch):
    monkeypatch.setattr(transcript_artifacts, "ROOT", tmp_path / "artifacts")
    writes = []

    def request(path, method="GET", body=None, prefer="return=minimal"):
        writes.append((path, method, body))
        return []

    monkeypatch.setattr(feeder, "_request", request)
    monkeypatch.setattr(feeder.sys, "argv", ["feeder_runtime", "intake", "--feeder-type", "OPTIONS_STRATEGY_FEEDER",
        "--source-type", "YOUTUBE", "--title", "Option strategy", "--url", "https://youtube.com/watch?v=two",
        "--transcript", "long transcript body", "--source-id", "source-yt-2"])
    feeder.main()
    body = next(body for path, method, body in writes if method == "POST" and "nexus_feeder_sources" in path)
    assert "transcript_or_extract" not in body
    assert body["transcript_storage_class"] == "LOCAL_ARTIFACT"
    assert transcript_artifacts.load_transcript("source-yt-2") == "long transcript body"
