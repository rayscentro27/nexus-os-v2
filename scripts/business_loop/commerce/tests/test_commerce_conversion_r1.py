"""NEXUS_COMMERCE_CONVERSION_AND_MEASUREMENT_R1 offline contracts (no network, no spend)."""
from __future__ import annotations

import json
import re
from urllib.parse import parse_qs, urlsplit

import pytest

from business_loop.commerce import funnel as F
from business_loop.commerce import governed_clients as G
from business_loop.commerce import stripe_test_checkout as S
from business_loop.commerce import storefront_patch as P

IDS = {"project_id": F.PROJECT_ID}


def ev(t, sid, variant="h1_fa", source="facebook", **kw):
    return {"event_type": t, "session_id": sid, "source": source, "content_variant": variant, "utm_source": source, "utm_content": variant,
            "verified": kw.get("verified", False), "is_test": kw.get("is_test", False), "detail": {}, "created_at": kw.get("at", "2026-11-16T00:00:00Z")}


def fetcher(events, leads=(), orders=()):
    def f(path):
        return list(events) if path.startswith("commerce_events") else list(leads) if path.startswith("commerce_leads") else list(orders)
    return f


# 1-3, 5, 6: tracking + attribution
def test_funnel_counts_and_attribution_by_variant():
    events = [ev("PAGE_VIEW", "a"), ev("CTA_CLICK", "a"), ev("INTEREST_FORM_STARTED", "a"), ev("INTEREST_FORM_SUBMITTED", "a"),
              ev("PAGE_VIEW", "b", "h2_in", "instagram"), ev("CTA_CLICK", "b", "h2_in", "instagram")]
    leads = [{"session_id": "a", "source": "facebook", "content_variant": "h1_fa", "is_test": False, "email_normalized": "x@y.co", "created_at": "z"}]
    m = F.measure(fetcher(events, leads))
    assert (m["PAGE_VIEWS"], m["CTA_CLICKS"], m["INTEREST_FORM_STARTS"], m["INTEREST_SUBMISSIONS"]) == (2, 2, 1, 1)
    v = m["CONTENT_VARIANT_BREAKDOWN"]
    assert v["h1_fa"]["interest_submissions"] == 1 and v["h2_in"]["interest_submissions"] == 0 and v["h2_in"]["cta_clicks"] == 1
    assert m["SOURCE_BREAKDOWN"]["instagram"]["sessions"] == 1


def test_tracked_urls_deterministic_and_distinguishable():
    urls = F.tracked_urls()
    assert set(urls) == {f"{p}_{h}" for p in ("FACEBOOK", "INSTAGRAM", "TIKTOK") for h in ("H1", "H2")}
    contents = {parse_qs(urlsplit(u).query)["utm_content"][0] for u in urls.values()}
    assert len(contents) == 6 and all(parse_qs(urlsplit(u).query)["utm_campaign"] == [F.CAMPAIGN_ID] for u in urls.values())
    assert urls == F.tracked_urls()


# 4, 7: duplicate + invalid email are enforced in page JS (server side proven live via RLS/unique checks)
def test_page_js_validates_email_and_handles_duplicates():
    js = P.script_block("")
    assert "RE.test(email)" in js and "r.status===409" in js and "nx_lead_" in js and "nx-company" in js
    assert "not yet available for purchase" in P.FORM_HTML.lower()


# 8: NOT_AVAILABLE vs zero
def test_unavailable_store_is_not_zero():
    def down(_):
        raise RuntimeError("supabase down")
    m = F.measure(down)
    assert m["PAGE_VIEWS"] == F.NA and m["PURCHASES"] == F.NA and m["REVENUE"] == F.NA
    empty = F.measure(fetcher([]))
    assert empty["PAGE_VIEWS"] == 0 and empty["CONVERSION_RATE"]["interest_per_session"] == F.NA


def test_test_traffic_excluded_from_real_metrics():
    m = F.measure(fetcher([ev("PAGE_VIEW", "nexus-cert-1"), ev("PAGE_VIEW", "real", is_test=False), ev("PAGE_VIEW", "x", is_test=True)]))
    assert m["PAGE_VIEWS"] == 1


def test_ab_minimum_evidence_rule_blocks_premature_winner():
    events = [ev("PAGE_VIEW", f"s{i}", "h1_fa") for i in range(30)] + [ev("PAGE_VIEW", f"t{i}", "h2_in", "instagram") for i in range(30)]
    a = F.analyze(F.measure(fetcher(events)))
    assert a["WHICH_HOOK_PERFORMED_BEST"] == "INSUFFICIENT_EVIDENCE" and a["NO_AUTOMATIC_SPEND"]


def test_ab_declares_winner_only_with_evidence():
    events, leads = [], []
    for i in range(200):
        events.append(ev("PAGE_VIEW", f"s{i}", "h1_fa")); events.append(ev("PAGE_VIEW", f"t{i}", "h2_in", "instagram"))
    leads += [{"session_id": f"s{i}", "is_test": False, "email_normalized": f"a{i}@x.co"} for i in range(40)]
    leads += [{"session_id": f"t{i}", "is_test": False, "email_normalized": f"b{i}@x.co"} for i in range(12)]
    a = F.analyze(F.measure(fetcher(events, leads)))
    assert a["WHICH_HOOK_PERFORMED_BEST"] == "h1_fa" and a["NEXT_BEST_ACTION"]["owner"] == "CREATIVE"


# 9, 10, 14: checkout gating + no spend
def test_live_stripe_key_is_refused():
    with pytest.raises(G.CommerceGuard):
        G.StripeTest(key="sk_live_" + "x" * 20)
    with pytest.raises(G.CommerceGuard):
        G.StripeTest(key="pk_test_" + "x" * 20)


class FakeStripe:
    def __init__(self):
        self.calls = []

    def post(self, path, params):
        self.calls.append(path)
        return 200, {"id": {"/products": "prod_t", "/prices": "price_t", "/payment_links": "plink_t"}[path], "url": "https://buy.stripe.com/test_x", "livemode": False}

    def get(self, path, params=None):
        return 200, {"data": [{"id": "cs_test_1", "livemode": False, "payment_status": "paid", "amount_total": 4800, "currency": "usd",
                               "client_reference_id": "sess1", "created": 1794800000, "metadata": {}},
                              {"id": "cs_live_1", "livemode": True, "payment_status": "paid", "amount_total": 4800, "currency": "usd", "created": 1794800000}]}


def test_test_checkout_order_capture_ignores_live_and_never_counts_test_as_revenue(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "STATE", tmp_path / "s.json")
    writes = []
    monkeypatch.setattr(S, "call", lambda m, p, body=None, **k: (writes.append((m, p, body)) or (201, None)) if m == "POST" else (200, []))
    monkeypatch.setattr(S, "job_context", lambda *_: None)
    st = S.setup(FakeStripe())
    assert st["mode"] == "TEST" and st["livemode"] is False and st["unit_amount_cents"] == 4800
    out = S.sync(FakeStripe())
    assert out["sessions"] == 1 and out["orders_written"] == 1
    orders = [b for m, p, b in writes if p == "commerce_orders"]
    assert len(orders) == 1 and orders[0]["mode"] == "TEST" and orders[0]["provider_session_id"] == "cs_test_1"
    purchase = [b for m, p, b in writes if p == "commerce_events" and b["event_type"] == "PURCHASE_COMPLETED"]
    assert purchase and purchase[0]["verified"] is True and purchase[0]["is_test"] is True
    m = F.measure(fetcher([], [], [{"mode": "TEST", "payment_status": "paid", "amount_total_cents": 4800, "session_id": "sess1"}]))
    assert m["PURCHASES"] == 0 and m["REVENUE"] == 0.0


def test_hidden_test_checkout_and_no_public_sale_claim():
    js = P.script_block("https://buy.stripe.com/test_x")
    assert "qs.get('checkout_test')==='1'" in js and "#nx-test-checkout{display:none" in P.FORM_HTML


# 11, 12: hash-bound approvals
def test_old_approval_cannot_authorize_changed_copy():
    import facebook_live_publisher as fb
    _, old = fb.find_request("apr_req_4fe6eb45cb6cc2fa")
    changed = {**old, "copy": F.copy_package(True)["copy"]["FACEBOOK"]}
    assert "REQUEST_HASH_MISMATCH (protected field or media changed)" in fb.verify_request(changed)
    assert fb.compute_request_hash({**old, "status": "SUPERSEDED"}) == old["request_hash"]  # old hash still binds only old content
    assert any(p.startswith("REQUEST_SUPERSEDED_BY") for p in fb.verify_request({**old, "status": "SUPERSEDED", "superseded_by": "x"}))


def test_copy_cta_matches_reality():
    ok = F.copy_package(True)
    assert ok["CTA_VALIDATED"] and all(c["link_tracked"] for c in ok["checks"].values())
    no_form = F.copy_package(False)
    assert all("register interest" not in t.lower() for t in no_form["copy"].values())


# 13: commerce go-live separately gated
def test_go_live_package_never_executes():
    pr = F.pricing({"us_shipping_first_item_usd": 7.09})
    pkg = F.go_live_package({"blueprint_id": 478}, pr, {}, [])
    assert pkg["status"] == "WAITING_FOR_RAY_APPROVAL" and pkg["live_financial_activation_performed"] is False
    assert pr["base_cost"]["value"] is None and "NOT_VERIFIED" in pr["base_cost"]["status"]
    assert pr["gross_margin_at_recommended"] == "NOT_AVAILABLE until base cost verified"


def test_governor_policy_scope_is_spend_free():
    assert G.LIMITS["money"] == {"per_job": 0, "per_day": 0, "per_month": 0} and G.JOB_TYPE == "COMMERCE_CONVERSION_R1"
