import os
from nexus_research_r10 import tier_routing as tr

# --- prechecks (Phase 2) ---
def test_precheck_example_domain_rejected():
    assert tr.precheck_source("https://example.com/foo")["reason"]=="INVALID_SOURCE_EXAMPLE_DOMAIN"
def test_precheck_hello_world_rejected():
    assert tr.precheck_source("https://github.com/octocat/Hello-World")["reason"]=="TEST_FIXTURE_HELLO_WORLD"
def test_precheck_empty_evidence_rejected():
    assert tr.precheck_source("", evidence=None)["admit"] is False
def test_precheck_legit_site_admitted():
    assert tr.precheck_source("https://stripe.com/pricing")["admit"] is True
def test_precheck_legit_github_admitted():
    assert tr.precheck_source("https://github.com/vercel/next.js")["admit"] is True
def test_precheck_youtube_admitted():
    assert tr.precheck_source("https://www.youtube.com/watch?v=abc123xyz")["admit"] is True

# --- source identity / duplicate reuse (Phase 3) ---
def test_identity_youtube_by_video_id():
    a=tr.source_identity("https://www.youtube.com/watch?v=zbAmmnMh5ew&t=10")
    b=tr.source_identity("https://youtu.be/zbAmmnMh5ew")
    assert a==b=="yt:zbAmmnMh5ew"
def test_identity_github_repo():
    assert tr.source_identity("https://github.com/vercel/next.js").startswith("gh:vercel/next.js")
def test_duplicate_reuse_hits_prior():
    lib=lambda i:{"id":"r1","quality_ok":True,"promoted":True} if i=="yt:X" else None
    assert tr.duplicate_reuse_decision("yt:X", lib)["reuse"] is True
def test_duplicate_reuse_refresh_on_new_evidence():
    lib=lambda i:{"id":"r1","quality_ok":True,"promoted":True}
    assert tr.duplicate_reuse_decision("yt:X", lib, new_evidence=True)["reuse"] is False

# --- low-information gate (Phase 4) ---
def test_lowinfo_gate_blocks_no_evidence():
    r=tr.promotion_gate({"result_summary":"Research completed; no attributable evidence was acquired, so findings remain unverified."})
    assert r["promote"] is False and r["terminal_state"]=="LOW_INFORMATION_OUTPUT"
def test_lowinfo_gate_blocks_failed_metadata():
    r=tr.promotion_gate({"result_summary":"The supplied evidence records failed YouTube metadata retrieval. Video title and content are unknown and the supplied evidence does not support a trend assessment."})
    assert r["promote"] is False
def test_promotion_gate_allows_substantive():
    r=tr.promotion_gate({"source_valid":True,"findings":[{"c":"x"}],"structured":{"findings":[{"claim":"Acme tool cuts editing time in half, pricing $29/mo, trend rising among short-form creators based on the transcript evidence provided here."}]}})
    assert r["promote"] is True

# --- failure circuit breaker (Phase 5/13) ---
def test_breaker_stops_repeated_failure_no_new_evidence():
    assert tr.circuit_breaker({"repeated_failure_reason":"NO_EVIDENCE","new_evidence_added":False})["stop"] is True
def test_breaker_defers_on_provider_block():
    d=tr.circuit_breaker({"provider_condition_unchanged":True,"provider_status":"USAGE_LIMIT_REACHED"})
    assert d["stop"] is True and d.get("defer") is True
def test_breaker_allows_productive_long_run():
    assert tr.circuit_breaker({"model_call_count":9,"elapsed_duration_s":900,"new_evidence_added":True})["stop"] is False

# --- tier classifier (Phase 6) ---
def test_classify_single_video_trend_tier1():
    j={"research_type":"TREND","objective":"Trend Scout pilot on this YouTube item","source_refs":["https://www.youtube.com/watch?v=zbAmmnMh5ew"]}
    assert tr.classify_tier(j)["tier"]=="TIER_1_SIMPLE_RESEARCH"
def test_classify_business_tier3():
    j={"research_type":"BUSINESS","objective":"Deep commercial synthesis and unit economics for opportunity","source_refs":["https://x.com/a","https://y.com/b"]}
    assert tr.classify_tier(j)["tier"]=="TIER_3_DEEP_RESEARCH"
def test_classify_trading_tier3():
    assert tr.classify_tier({"research_type":"TRADING","objective":"EUR/USD strategy","source_refs":["https://tv.com/x"]})["tier"]=="TIER_3_DEEP_RESEARCH"
def test_classify_github_technical_tier3():
    assert tr.classify_tier({"research_type":"TECHNOLOGY","objective":"Evaluate repository architecture","source_refs":["https://github.com/a/b"]})["tier"]=="TIER_3_DEEP_RESEARCH"
def test_classify_invalid_source_tier0():
    assert tr.classify_tier({"research_type":"TREND","objective":"x","source_refs":["https://example.com"]})["tier"]=="TIER_0_DETERMINISTIC"

# --- escalation (Phase 12) ---
def test_escalation_valid_and_invalid():
    assert tr.should_escalate("CONFLICTING_EVIDENCE") is True
    assert tr.should_escalate("I_JUST_FEEL_LIKE_IT") is False

# --- Nova provider isolation (hard requirement) ---
def test_research_model_is_not_nova_model():
    assert tr.RESEARCH_TIER1_MODEL != tr.NOVA_PROTECTED_MODEL
def test_tier1_adapter_refuses_nova_model():
    assert tr.tier1_extract("x", model=tr.NOVA_PROTECTED_MODEL)["error"]=="NOVA_MODEL_FORBIDDEN"
