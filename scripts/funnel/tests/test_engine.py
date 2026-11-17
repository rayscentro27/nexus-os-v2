from __future__ import annotations

import os

import pytest

from scripts.funnel import engine as fe

OID = "opp_test0000000000000000000000000000"


def _marketing(offer="AFFILIATE referral"):
    return {
        "opportunity_id": OID, "campaign_id": "camp_test0000000000000000000000000000",
        "audience": "small-business owners", "customer_problem": "missed calls lose revenue",
        "value_proposition": "Answer every call automatically", "offer": offer,
        "cta": "See how it works", "landing_page_objective": "convert a visitor into a tracked lead",
        "landing_page_requirements": {"OBJECTIVE": "convert"},
        "measurement_plan": {"DEFINITION_OF_DONE": "Qualified conversions"},
        "paid_test": {"STOP_CONDITION": "reach MAXIMUM_SPEND"},
    }


def _creative():
    return {"OPPORTUNITY_ID": OID, "ASSETS": [{
        "ASSET_ID": "asset_test0000000000000000000000000000", "ASSET_TYPE": "LANDING_PAGE_COPY",
        "MARKETING_HANDOFF_READY": True,
        "COPY": {"INTERRUPT": "Stop losing customers to missed calls", "BODY": "Answer every call automatically",
                 "CLEAR_ACTION": "See how it works", "FABRICATION": "none"}}]}


def test_build_affiliate_review_page(tmp_path):
    db = tmp_path / "funnel.sqlite3"
    p = fe.build_page(OID, marketing=_marketing(), creative=_creative(), database_path=db)["page"]
    assert p["PAGE_TYPE"] == "AFFILIATE_REVIEW_PAGE"
    assert p["PAGE_STRUCTURE"][0] == "HERO" and "CTA_AFFILIATE" in p["PAGE_STRUCTURE"]
    assert p["QA_STATUS"] == "PASS"


def test_output_contract_fields(tmp_path):
    db = tmp_path / "funnel.sqlite3"
    p = fe.build_page(OID, marketing=_marketing(), creative=_creative(), database_path=db)["page"]
    for f in ("PAGE_ID", "FUNNEL_ID", "PAGE_TYPE", "PAGE_ROUTE", "PAGE_STRUCTURE", "COPY_USED", "ASSETS_USED",
              "CTA", "FORM_STATUS", "TRACKING_STATUS", "QA_STATUS", "DEPLOY_STATUS", "APPROVAL_REQUIRED",
              "NEXT_ACTION", "ATTRIBUTION", "AB_SPEC", "PREVIEW_DIR", "DEPLOY_COMMAND"):
        assert f in p, f


def test_deploy_is_prepared_not_executed(tmp_path):
    db = tmp_path / "funnel.sqlite3"
    p = fe.build_page(OID, marketing=_marketing(), creative=_creative(), database_path=db)["page"]
    assert p["DEPLOY_STATUS"] == "PREVIEW_PREPARED_PENDING_APPROVAL"
    assert p["APPROVAL_REQUIRED"] is True
    assert p["DEPLOY_COMMAND"].startswith("netlify deploy --dir")
    assert p["NEXT_ACTION"] == "REQUEST_RAY_APPROVAL_FOR_PREVIEW_DEPLOY"


def test_attribution_wired(tmp_path):
    db = tmp_path / "funnel.sqlite3"
    p = fe.build_page(OID, marketing=_marketing(), creative=_creative(), database_path=db)["page"]
    keys = p["ATTRIBUTION"]["KEYS"]
    assert keys["OPPORTUNITY_ID"] == OID
    for k in ("CAMPAIGN_ID", "LANDING_PAGE_ID", "CREATIVE_ID", "OFFER_ID", "CONTENT_ID", "CHANNEL"):
        assert k in keys
    assert p["TRACKING_STATUS"] == "WIRED"


def test_generated_markup_has_required_elements(tmp_path):
    db = tmp_path / "funnel.sqlite3"
    p = fe.build_page(OID, marketing=_marketing(), creative=_creative(), database_path=db)["page"]
    markup = open(os.path.join(p["PREVIEW_DIR"], "index.html")).read()
    assert "<html" in markup and 'name="viewport"' in markup
    assert 'id="primary-cta"' in markup
    assert 'rel="sponsored nofollow noopener"' in markup
    assert "utm_source" in markup and "data-landing-page-id" in markup
    assert "EVIDENCE_PLACEHOLDER" in markup  # no fabricated proof
    assert os.path.exists(os.path.join(p["PREVIEW_DIR"], "funnel-qa.spec.ts"))


def test_lead_capture_wires_form(tmp_path):
    db = tmp_path / "funnel.sqlite3"
    p = fe.build_page(OID, funnel_type="LEAD_CAPTURE_PAGE", marketing=_marketing("SERVICE lead"),
                      creative=_creative(), database_path=db)["page"]
    assert p["PAGE_TYPE"] == "LEAD_CAPTURE_PAGE"
    assert p["FORM_STATUS"] == "WIRED"
    markup = open(os.path.join(p["PREVIEW_DIR"], "index.html")).read()
    assert "<form" in markup and 'name="email"' in markup


def test_only_supported_funnel_types(tmp_path):
    db = tmp_path / "funnel.sqlite3"
    # unknown override falls back to a supported type (no crash, no unsupported type persisted)
    p = fe.build_page(OID, funnel_type="GIANT_PLATFORM_FUNNEL", marketing=_marketing("SERVICE"),
                      creative=_creative(), database_path=db)["page"]
    assert p["PAGE_TYPE"] in fe.FUNNEL_TYPES


def test_ab_spec_present(tmp_path):
    db = tmp_path / "funnel.sqlite3"
    p = fe.build_page(OID, marketing=_marketing(), creative=_creative(), database_path=db)["page"]
    assert p["AB_SPEC"]["STATUS"] == "SPEC_ONLY_V1"
    assert [v["id"] for v in p["AB_SPEC"]["VARIANTS"]] == ["A", "B"]


def test_nova_summary_and_suppression(tmp_path):
    db = tmp_path / "funnel.sqlite3"
    fe.build_page(OID, marketing=_marketing(), creative=_creative(), database_path=db)
    ns = fe.nova_summary(opportunity_id=OID, database_path=db)["nova_summary"]
    for f in ("PAGE_TYPE", "STATUS", "QA_STATUS", "DEPLOY_STATUS", "APPROVAL_REQUIRED", "RECOMMENDED_NEXT_ACTION"):
        assert f in ns, f
    assert "OPPORTUNITY_ID" not in ns
    plain = fe.get_page(opportunity_id=OID, database_path=db)["page"]
    assert "PAGE_ID" not in plain
    diag = fe.get_page(opportunity_id=OID, database_path=db, include_internal_ids=True)["page"]
    assert diag["OPPORTUNITY_ID"] == OID


def test_idempotent_per_opportunity_and_type(tmp_path):
    db = tmp_path / "funnel.sqlite3"
    a = fe.build_page(OID, marketing=_marketing(), creative=_creative(), database_path=db)["page"]
    b = fe.build_page(OID, marketing=_marketing(), creative=_creative(), database_path=db)["page"]
    assert a["PAGE_ID"] == b["PAGE_ID"]
    assert fe.list_pages(database_path=db)["count"] == 1


def test_no_marketing_campaign_rejected(tmp_path):
    db = tmp_path / "funnel.sqlite3"
    r = fe.build_page(OID, marketing={}, creative=_creative(), database_path=db)
    assert r["status"] == "REJECTED"


def test_health(tmp_path):
    db = tmp_path / "funnel.sqlite3"
    fe.initialize(db)
    h = fe.health(database_path=db)
    assert h["status"] == "PASS"
    assert h["authority"]["LOCAL_SQLITE_IS_AUTHORITATIVE"] == "YES"
