"""Focused tests for the certified Research Tier-1 free provider (2026-11-09).
Run with PYTEST_DISABLE_PLUGIN_AUTOLOAD=1. Covers the 7 required categories:
ZERO_COST_ENFORCEMENT, NOVA_MODEL_EXCLUSION, STRUCTURED_JSON_VALIDATION,
RATE_LIMIT_FALLBACK, UNKNOWN_PRESERVATION, FALSE_TREND_CLAIM_DETECTION, NO_PAID_ROUTING.
"""
import json
from nexus_research_r10 import tier_routing as tr

# -------- ZERO_COST_ENFORCEMENT --------
def test_zero_cost_all_chain_models_free():
    assert tr.all_models_free() is True

def test_zero_cost_config_has_no_paid_signal():
    # certified request config never requests a paid tier and caps output
    assert tr.TIER1_REQUEST_CONFIG["max_tokens"] == 1500
    assert tr.TIER1_REQUEST_CONFIG["reasoning"] == {"enabled": False}

# -------- NOVA_MODEL_EXCLUSION --------
def test_nova_excluded_from_chain():
    assert tr.nova_excluded() is True
    assert tr.NOVA_PROTECTED_MODEL not in tr.RESEARCH_TIER1_MODEL_CHAIN

def test_adapter_refuses_nova_model():
    assert tr.tier1_extract("x", model=tr.NOVA_PROTECTED_MODEL)["error"] == "NOVA_MODEL_FORBIDDEN"

def test_certified_primary_and_backup_not_nova():
    assert tr.RESEARCH_TIER1_MODEL != tr.NOVA_PROTECTED_MODEL
    assert tr.RESEARCH_TIER1_BACKUP_MODEL != tr.NOVA_PROTECTED_MODEL

# -------- STRUCTURED_JSON_VALIDATION --------
def test_structured_json_valid_contract():
    good = json.dumps({f: ("UNKNOWN" if f in ("commercial_relevance",) else
                            ("CURRENT_ATTENTION_LOW" if f == "trend_signal" else
                             (0.7 if f == "confidence" else [])))
                       for f in tr.TIER1_CONTRACT_FIELDS})
    r = tr.validate_tier1_json(good)
    assert r["ok"] is True and r["parsed"] is True and r["missing_fields"] == []

def test_structured_json_rejects_missing_fields():
    r = tr.validate_tier1_json('{"summary":"x"}')
    assert r["parsed"] is True and "claims" in r["missing_fields"] and r["ok"] is False

def test_structured_json_rejects_bad_trend_signal():
    obj = {f: [] for f in tr.TIER1_CONTRACT_FIELDS}
    obj["trend_signal"] = "RAPIDLY_GROWING"
    r = tr.validate_tier1_json(json.dumps(obj))
    assert r["bad_trend_signal"] is True and r["ok"] is False

def test_structured_json_rejects_unparseable():
    r = tr.validate_tier1_json("not json at all")
    assert r["parsed"] is False and r["ok"] is False

# -------- RATE_LIMIT_FALLBACK --------
def test_rate_limit_fallback_to_backup(monkeypatch):
    import urllib.error, io
    calls = []
    class _Resp(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): return False
    def fake_urlopen(req, timeout=0):
        body = json.loads(req.data.decode())
        calls.append(body["model"])
        if body["model"] == tr.RESEARCH_TIER1_MODEL:  # primary 429s
            raise urllib.error.HTTPError(req.full_url, 429, "rate", {}, None)
        payload = {"model": body["model"], "usage": {"cost": 0},
                   "choices": [{"message": {"content": '{"summary":"ok","confidence":0.5}'}}]}
        return _Resp(json.dumps(payload).encode())
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    out = tr.tier1_extract("some evidence")
    assert out["ok"] is True
    assert out["model"] == tr.RESEARCH_TIER1_BACKUP_MODEL  # fell back past the 429'd primary
    assert out["zero_cost"] is True
    assert calls[0] == tr.RESEARCH_TIER1_MODEL and calls[1] == tr.RESEARCH_TIER1_BACKUP_MODEL

# -------- UNKNOWN_PRESERVATION --------
def test_unknown_preserved_for_unsupported_fields():
    obj = {"commercial_relevance": "UNKNOWN", "claims": [], "risks_limitations": []}
    assert tr.unknown_preserved(obj, "commercial_relevance") is True
    assert tr.unknown_preserved(obj, "claims") is True

def test_unknown_not_preserved_when_fabricated():
    obj = {"commercial_relevance": "Guaranteed $1M/mo revenue with 400% MoM growth"}
    assert tr.unknown_preserved(obj, "commercial_relevance") is False

# -------- FALSE_TREND_CLAIM_DETECTION --------
def test_false_trend_growth_detected():
    assert len(tr.detect_false_trend_growth("interest is rapidly growing and going viral")) >= 1
    assert len(tr.detect_false_trend_growth({"summary": "demand is growing fast"})) >= 1

def test_valid_current_attention_not_flagged():
    assert tr.detect_false_trend_growth("trend_signal CURRENT_ATTENTION_HIGH; strong current attention") == []

def test_over_attention_on_low_views_flagged():
    assert tr.over_attention_claim("CURRENT_ATTENTION_HIGH", 328) is True
    assert tr.over_attention_claim("CURRENT_ATTENTION_HIGH", 2_000_000) is False
    assert tr.over_attention_claim("CURRENT_ATTENTION_LOW", 328) is False

# -------- QUALITY GATE + ROLE MAPPING (R16 routing) --------
def _good_obj():
    return {"summary":"A tutorial video.","key_findings":["x"],"claims":["Creator shows a workflow"],
            "claim_support":["description"],"commercial_relevance":"UNKNOWN","trend_signal":"CURRENT_ATTENTION_LOW",
            "risks_limitations":["single source"],"open_questions":["scale?"],"confidence":0.75}

def test_quality_gate_passes_clean_output():
    g=tr.tier1_quality_gate(_good_obj(), evidence_text="creator shows a workflow", view_count=328)
    assert g["pass"] is True and g["autofail"]==[]

def test_quality_gate_fails_false_growth():
    o=_good_obj(); o["summary"]="interest is rapidly growing and going viral"
    assert tr.tier1_quality_gate(o, view_count=328)["pass"] is False

def test_quality_gate_fails_over_attention():
    o=_good_obj(); o["trend_signal"]="CURRENT_ATTENTION_HIGH"
    g=tr.tier1_quality_gate(o, view_count=100)
    assert g["pass"] is False and "OVER_ATTENTION_CLAIM" in g["autofail"]

def test_quality_gate_escalation_reason_on_fail():
    o=_good_obj(); o.pop("claims")
    assert tr.tier1_quality_gate(o)["escalation_reason"]=="FAILED_QUALITY_GATE"

def test_role_output_mapping_skips_codex():
    ro=tr.tier1_to_role_outputs(_good_obj())
    assert "RESEARCH_INVESTIGATOR" in ro and "TREND_SCOUT" in ro
    assert ro["RESEARCH_INVESTIGATOR"]["confidence"]==75  # 0.75 -> 75
    assert ro["TREND_SCOUT"]["trend_score"] is None       # no velocity from snapshot
    assert ro["RESEARCH_INVESTIGATOR"]["findings"][0]["claim"]

def test_prompt_uses_current_attention_not_growth_labels():
    assert "CURRENT_ATTENTION" in tr.TIER1_EXTRACTION_PROMPT
    assert "RISING" not in tr.TIER1_EXTRACTION_PROMPT and "DECLINING" not in tr.TIER1_EXTRACTION_PROMPT

# -------- NO_PAID_ROUTING --------
def test_no_paid_routing_models_all_free_suffix():
    for m in tr.RESEARCH_TIER1_MODEL_CHAIN:
        assert m.endswith(":free")

def test_no_paid_routing_provider_is_openrouter_free():
    assert tr.RESEARCH_TIER1_PROVIDER == "openrouter"
    assert tr.all_models_free() is True
