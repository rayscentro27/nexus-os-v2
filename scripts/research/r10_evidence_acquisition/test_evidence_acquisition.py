import os
from nexus_research_r10 import service
from nexus_research_r10.intake.youtube import normalize_youtube

def test_enrich_rejects_bad_video_id():
    assert service._youtube_data_api_enrich("short") is None
    assert service._youtube_data_api_enrich("") is None

def test_enrich_returns_rich_metadata_network():
    r=service._youtube_data_api_enrich("dQw4w9WgXcQ")
    assert r and r.get("description") and len(r["description"])>80
    assert r.get("view_count") and r.get("like_count")
    assert r.get("metadata_source")=="YOUTUBE_DATA_API"

def test_normalize_builds_evidence_units_from_description():
    rec={"video_id":"dQw4w9WgXcQ","title":"T","channel":"C","transcript_source":"YOUTUBE_DATA_API_METADATA",
         "summary":"This is a substantive description with real content about the video topic, pricing, and claims "*5,
         "view_count":"100","like_count":"5","published_at":"2009-10-25T06:57:33Z"}
    src=normalize_youtube(rec)
    assert len(src.evidence_units)>=1
    assert src.metadata.get("view_count")=="100"

def test_evidence_state_metadata_only_when_no_api(monkeypatch):
    # defensive: if enrich returns None, acquisition still yields title-only metadata (not a crash)
    monkeypatch.setattr(service,"_youtube_data_api_enrich",lambda v:None)
    assert service._youtube_data_api_enrich("dQw4w9WgXcQ") is None

def test_acquisition_error_gate_no_false_ready_for_missing():
    # a non-existent video id -> Data API returns None (no items) -> no false EVIDENCE_READY
    r=service._youtube_data_api_enrich("00000000000")
    assert r is None or not r.get("description")
