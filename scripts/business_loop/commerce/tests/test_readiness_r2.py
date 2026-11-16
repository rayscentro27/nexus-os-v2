"""NEXUS_COMMERCE_PRODUCT_TRUTH_AND_GO_LIVE_READINESS_R2 safety tests (offline; read local artifacts only)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from business_loop.commerce import funnel as F
from business_loop.commerce import governed_clients as G
from business_loop.commerce import printify_draft as D
from business_loop.commerce import storefront_patch as P

ROOT = Path(__file__).resolve().parents[4]
REG = ROOT / "configs/nexus_credential_registry.json"
R2 = ROOT / "reports/business_loop/commerce_readiness_r2_latest.json"


def _reg(cid):
    return next(c for c in json.loads(REG.read_text())["credentials"] if c["credential_id"] == cid)


def test_stripe_labels_cannot_confuse_live_for_test():
    test, live = _reg("credential.stripe.payments.test.v1"), _reg("credential.stripe.payments.live.v1")
    assert test["status"] == "MISSING" and test["required_key_prefix"] == "sk_test_"
    assert "STRIPE_SECRET_KEY" not in json.dumps(test["canonical_aliases"]) + json.dumps(test["legacy_aliases"])
    assert live["environment"] == "live" and live["consumers"] == [] and live["required_key_prefix"] == "sk_live_"
    with pytest.raises(G.CommerceGuard):  # runtime guard independent of label
        G.StripeTest(key="sk_live_" + "x" * 24)


def test_stripe_test_lane_refuses_live_key(tmp_path, monkeypatch):
    import approval_lanes.nexus_stripe_test_checkout_lane as lane
    src = Path(lane.__file__).read_text()
    assert 'startswith(("sk_test_", "rk_test_"))' in src and "REFUSED_NON_TEST_KEY" in src


def test_printify_writer_only_allows_draft_create_paths():
    w = D.PrintifyDraftWriter(token="t")
    for path in ("/shops/29243395/products/x/publish.json", "/shops/29243395/orders.json", "/shops/29243395/products/x.json"):
        with pytest.raises(G.CommerceGuard):
            w.post(path, {})


def test_page_matches_actual_printify_product():
    html = P.PAGE.read_text()
    text = P.visible_text(html)
    assert not P.BANNED.findall(text)
    assert P.MOCKUP in html and "meta_holiday_ceramic_mug_1794355016.webp" not in html and "modal_holiday_ceramic_mug_video" not in html
    assert "15 oz white ceramic" in text.lower() and "not yet for sale" in text.lower() and "$24 (staged)" in text


def test_tracking_and_form_preserved_in_built_page():
    html = P.PAGE.read_text()
    assert 'id="nx-interest"' in html and "commerce_events" in html and "commerce_leads" in html
    assert "utm_content" in html and "nx_cert" in html


def test_r2_report_cost_truth_and_stages():
    r = json.loads(R2.read_text())
    assert r["printify"]["base_cost_usd"] == pytest.approx(6.13) and r["printify"]["published"] is False and r["printify"]["orders"] == 0
    assert r["pricing"]["base_cost"]["status"].startswith("VERIFIED")
    assert {o["RETAIL_PRICE"] for o in r["pricing"]["options"]} == {24.0, 26.0, 29.0, 32.0, 35.0}
    assert r["truth"]["PRODUCT_TRUTH_CHECK"] == "PASS"
    assert r["stages"]["LIVE_SALES_READY"].startswith("NO") and r["costs"]["UNAUTHORIZED_COST"] == 0


def test_superseded_publication_requests_refused_and_new_one_unapproved():
    import facebook_live_publisher as fb
    for old in ("apr_req_4fe6eb45cb6cc2fa", "apr_req_a385caddb64d1c34"):
        _, req = fb.find_request(old)
        assert any(p.startswith("REQUEST_SUPERSEDED_BY") for p in fb.verify_request(req))
    new_id = json.loads(R2.read_text())["publication_approval"]["PUBLICATION_APPROVAL_ID"]
    _, req = fb.find_request(new_id)
    assert fb.verify_request(req) == [] and req["status"] == "WAITING_FOR_RAY_APPROVAL"
    assert not [a for a in fb._latest_approvals_for(new_id) if a.get("status") in ("approved", "consumed")]


def test_golive_separate_from_publication_and_live_checkout_blocked():
    g = json.loads((ROOT / "dist/creative/holiday_commerce_go_live_approval_request.json").read_text())
    assert g["approval_kind"] == "COMMERCE_GO_LIVE" and g["status"] == "WAITING_FOR_RAY_APPROVAL" and g["live_financial_activation_performed"] is False
    assert g["covers"]["TEST_CHECKOUT_STATUS"] == "BLOCKED_MISSING_REAL_TEST_KEY" and g["covers"]["LIVE_CHECKOUT_STATUS"].startswith("BLOCKED")
    assert not g["approval_id"].startswith("apr_req_")  # distinct approval family from social publication


def test_product_lineage_preserved():
    r = json.loads(R2.read_text())
    assert r["product"]["PRODUCT_ID"] == r["product"]["CANONICAL_PRODUCT_ID"] == "prod_stoneware_mug_14oz"
    js = P.script_block("")
    assert '"product_id": "prod_stoneware_mug_14oz"' in js  # events/leads keep the RLS-bound identity
