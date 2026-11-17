from __future__ import annotations

import pytest

from scripts.creative import creative_engine as ce

OID = "opp_test0000000000000000000000000000"


def _brief(channel="SEO_SEARCH_CONSOLE", assets=None):
    return {
        "OPPORTUNITY_ID": OID, "CAMPAIGN_ID": "camp_test0000000000000000000000000000",
        "AUDIENCE": "small-business owners", "CUSTOMER_PROBLEM": "missed calls lose revenue",
        "EMOTIONAL_DRIVER": "Relief from lost customers", "POSITIONING": "AI phone answering that never misses",
        "OFFER": "AFFILIATE referral", "CHANNEL": channel,
        "CONTENT_FORMAT": "Channel-native short content + landing page copy",
        "HOOK": "Stop losing customers to missed calls", "MESSAGE": "Answer every call automatically",
        "CTA": "See how it works",
        "ASSET_REQUIREMENTS": assets if assets is not None else ["TBD by Marketing engine"],
        "LANDING_PAGE_REQUIREMENTS": {"OBJECTIVE": "convert a visitor into a tracked lead"},
        "CAMPAIGN_OBJECTIVE": "Acquire tracked leads", "SUCCESS_METRIC": "Qualified conversions",
    }


def test_intake_consumes_request_and_produces_asset_plan(tmp_path):
    path = tmp_path / "creative.sqlite3"
    res = ce.intake(OID, request=_brief(), database_path=path)
    assert res["status"] == "OK"
    c = res["creative"]
    assert c["ASSET_COUNT"] >= 1
    assert c["CHANNEL"] == "SEO_SEARCH_CONSOLE"


def test_output_contract_fields_present(tmp_path):
    path = tmp_path / "creative.sqlite3"
    c = ce.intake(OID, request=_brief(), database_path=path)["creative"]
    for a in c["ASSETS"]:
        for f in ("OPPORTUNITY_ID", "CAMPAIGN_ID", "CREATIVE_REQUEST_ID", "ASSET_ID", "ASSET_TYPE", "CHANNEL",
                  "FORMAT", "DIMENSIONS_OR_DURATION", "AUDIENCE", "HOOK", "MESSAGE", "CTA", "SCRIPT", "COPY",
                  "VISUAL_DIRECTION", "AUDIO_DIRECTION", "VOICE_DIRECTION", "BRAND_DIRECTION", "SOURCE_ASSETS",
                  "GENERATED_ASSETS", "FINAL_ASSET_LOCATION", "VERSION", "STATUS", "QUALITY_CHECK",
                  "COMPLIANCE_CHECK", "APPROVAL_REQUIRED", "APPROVAL_REASON", "MARKETING_SUCCESS_METRIC",
                  "MARKETING_HANDOFF_READY"):
            assert f in a, f


def test_text_assets_ready_media_assets_approval_gated(tmp_path):
    path = tmp_path / "creative.sqlite3"
    c = ce.intake(OID, request=_brief(), database_path=path)["creative"]
    text = [a for a in c["ASSETS"] if a["ASSET_TYPE"] in ce._TEXT_ASSET_TYPES]
    media = [a for a in c["ASSETS"] if a["ASSET_TYPE"] in ce._MEDIA_ASSET_TYPES]
    assert any(a["MARKETING_HANDOFF_READY"] for a in text)
    assert media and all(a["APPROVAL_REQUIRED"] and not a["MARKETING_HANDOFF_READY"] for a in media)


def test_copy_has_no_fabricated_evidence(tmp_path):
    path = tmp_path / "creative.sqlite3"
    c = ce.intake(OID, request=_brief(), database_path=path)["creative"]
    lp = next(a for a in c["ASSETS"] if a["ASSET_TYPE"] == "LANDING_PAGE_COPY")
    assert "EVIDENCE_PLACEHOLDER" in lp["COPY"]["EVIDENCE"]
    assert lp["COPY"]["FABRICATION"] == "none"
    assert lp["COMPLIANCE_CHECK"]["fabrication_detected"] is False


def test_compliance_flags_fabricated_claims():
    bad = ce._compliance_check({"copy": {"BODY": "Guaranteed #1 results, as seen on TV, thousands of happy customers"},
                                "script": None, "hook": "x", "message": "y"})
    assert bad["status"] == "FLAGGED"
    assert bad["fabrication_detected"] is True


def test_compliance_flags_fake_scarcity():
    bad = ce._compliance_check({"copy": {"BODY": "Only 3 left, act now, limited time"}, "script": None,
                                "hook": "x", "message": "y"})
    assert "scarcity_requires_real_deadline" in bad["flags"]


def test_video_channel_produces_script_and_gated_video(tmp_path):
    path = tmp_path / "creative.sqlite3"
    c = ce.intake(OID, request=_brief(channel="TIKTOK"), database_path=path)["creative"]
    types = [a["ASSET_TYPE"] for a in c["ASSETS"]]
    assert "SCRIPT" in types and "VIDEO" in types
    vid = next(a for a in c["ASSETS"] if a["ASSET_TYPE"] == "VIDEO")
    assert vid["APPROVAL_REQUIRED"] and not vid["MARKETING_HANDOFF_READY"]
    scr = next(a for a in c["ASSETS"] if a["ASSET_TYPE"] == "SCRIPT")
    assert scr["SCRIPT"] and "HOOK" in scr["SCRIPT"]


def test_quality_check_flags_unknown_brief_fields(tmp_path):
    path = tmp_path / "creative.sqlite3"
    brief = _brief()
    brief["HOOK"] = "UNKNOWN"
    c = ce.intake(OID, request=brief, database_path=path)["creative"]
    a = c["ASSETS"][0]
    assert any("hook" in f for f in a["QUALITY_CHECK"]["flags"])


def test_marketing_handoff_ready_and_pending(tmp_path):
    path = tmp_path / "creative.sqlite3"
    ce.intake(OID, request=_brief(), database_path=path)
    mh = ce.marketing_handoff(opportunity_id=OID, database_path=path)["creative_marketing_handoff"]
    assert mh["MARKETING_HANDOFF_READY"] is True
    assert mh["READY_COUNT"] >= 1
    assert mh["PENDING_COUNT"] >= 1


def test_nova_summary_and_suppression(tmp_path):
    path = tmp_path / "creative.sqlite3"
    ce.intake(OID, request=_brief(), database_path=path)
    ns = ce.nova_summary(opportunity_id=OID, database_path=path)["nova_summary"]
    for f in ("CHANNEL", "STATUS", "TOTAL_ASSETS", "READY_FOR_MARKETING", "WAITING_FOR_APPROVAL",
              "RECOMMENDED_NEXT_ACTION"):
        assert f in ns, f
    assert "OPPORTUNITY_ID" not in ns


def test_feedback_loop_roundtrip(tmp_path):
    path = tmp_path / "creative.sqlite3"
    ce.intake(OID, request=_brief(), database_path=path)
    ce.record_feedback(OID, winning_hook="Stop losing customers", winning_format="vertical_video",
                       ctr=0.04, what_worked="pain-led hook", database_path=path)
    fb = ce.feedback(opportunity_id=OID, database_path=path)
    assert fb["count"] == 1
    assert fb["items"][0]["winning_format"] == "vertical_video"


def test_idempotent_per_opportunity(tmp_path):
    path = tmp_path / "creative.sqlite3"
    a = ce.intake(OID, request=_brief(), database_path=path)["creative"]
    b = ce.intake(OID, request=_brief(), database_path=path)["creative"]
    assert a["CREATIVE_REQUEST_ID"] == b["CREATIVE_REQUEST_ID"]
    assert ce.list_creative(database_path=path)["count"] == 1


def test_internal_ids_suppressed_by_default(tmp_path):
    path = tmp_path / "creative.sqlite3"
    ce.intake(OID, request=_brief(), database_path=path)
    plain = ce.get_creative(opportunity_id=OID, database_path=path)["creative"]
    assert "OPPORTUNITY_ID" not in plain
    diag = ce.get_creative(opportunity_id=OID, database_path=path, include_internal_ids=True)["creative"]
    assert diag["OPPORTUNITY_ID"] == OID


def test_health_and_data_authority(tmp_path):
    path = tmp_path / "creative.sqlite3"
    ce.initialize(path)
    h = ce.health(database_path=path)
    assert h["status"] == "PASS"
    assert h["authority"]["LOCAL_SQLITE_IS_AUTHORITATIVE"] == "YES"
    assert h["authority"]["SUPABASE_IS_RAW_MEDIA_WAREHOUSE"] == "NO"
