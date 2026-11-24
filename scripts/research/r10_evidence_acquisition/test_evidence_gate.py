from nexus_research_r10.service import _evidence_admission

def _yt(err=None): return {"source_type":"youtube","source_id":"s1","error_state":err}
def _ev(text): return [{"source_id":"s1","text":text}]
SUB="This video reviews the Acme AI avatar tool in detail: it generates talking-head videos from a script in two minutes, pricing is $49/month, and the creator argues faceless AI channels will grow in 2026 based on several examples shown."

# EVIDENCE_READY -> allow deep model
def test_gate_allows_evidence_ready():
    r=_evidence_admission([_yt()],_ev(SUB),"TREND")
    assert r["state"]=="EVIDENCE_READY" and r["allow"] is True

# METADATA_ONLY (thin/boilerplate) -> block deep Codex
def test_gate_blocks_metadata_only_thin():
    r=_evidence_admission([_yt()],_ev("Subscribe! Link in bio. Follow me https://x.com/a"),"TREND")
    assert r["state"]=="METADATA_ONLY" and r["allow"] is False

# SOURCE_UNAVAILABLE -> block
def test_gate_blocks_source_unavailable():
    r=_evidence_admission([_yt("YOUTUBE_METADATA_UNAVAILABLE:HTTPError")],_ev(""),"TREND")
    assert r["state"]=="SOURCE_UNAVAILABLE" and r["allow"] is False

# ACQUISITION_ERROR -> block (preserve/retry, no Codex)
def test_gate_blocks_acquisition_error():
    r=_evidence_admission([_yt("LIVE_METADATA_UNAVAILABLE_USING_R9_SNAPSHOT:ReadTimeout")],_ev(""),"TREND")
    assert r["state"]=="ACQUISITION_ERROR" and r["allow"] is False

# NOT gated: business deep research passes unchanged (no false block)
def test_gate_not_gated_business_multi_source():
    srcs=[{"source_type":"web","source_id":"a"},{"source_type":"web","source_id":"b"}]
    r=_evidence_admission(srcs,[],"BUSINESS")
    assert r["state"]=="NOT_GATED" and r["allow"] is True

def test_gate_not_gated_multi_source_trend():
    srcs=[{"source_type":"youtube","source_id":"a"},{"source_type":"youtube","source_id":"b"}]
    assert _evidence_admission(srcs,[],"TREND")["allow"] is True

# title-only -> METADATA_ONLY -> blocked (prevents the historical waste pattern)
def test_title_only_blocked_from_codex():
    r=_evidence_admission([_yt()],_ev("Public YouTube oEmbed metadata only; transcript not retrieved."),"TREND")
    assert r["allow"] is False

# REGRESSION: the NEXUS_VIDEO_EVIDENCE_V1 JSON blob must NOT pad a thin video past the
# gate. A title-only video whose only bulk is the ~3.6k-char structural blob is METADATA_ONLY.
_BLOB='{"schema_version": "NEXUS_VIDEO_EVIDENCE_V1", "video_id": "x", "title": "T", "summary": null, "claims": [], "topics": []}'+("x"*3600)
def test_gate_not_fooled_by_video_evidence_blob():
    ev=[{"source_id":"s1","locator":{"schema":"NEXUS_VIDEO_EVIDENCE_V1"},"text":_BLOB},
        {"source_id":"s1","locator":{"segment":1},"text":"Most men need to hear this"}]
    r=_evidence_admission([_yt()],ev,"TREND")
    assert r["state"]=="METADATA_ONLY" and r["allow"] is False

# A real caption transcript (schema None) still admits even with a thin description.
def test_gate_admits_on_transcript_despite_thin_description():
    ev=[{"source_id":"s1","locator":{"schema":"NEXUS_VIDEO_EVIDENCE_V1"},"text":_BLOB},
        {"source_id":"s1","locator":{"segment":1},"text":"Most men need to hear this"},
        {"source_id":"s1","locator":{"segment":2},"text":"TRANSCRIPT ONLY — captions.\n"+("real spoken content about the subject. "*20)}]
    r=_evidence_admission([_yt()],ev,"TREND")
    assert r["state"]=="EVIDENCE_READY" and r["allow"] is True
