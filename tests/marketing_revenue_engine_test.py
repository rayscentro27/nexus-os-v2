from nexus_agent_platform.marketing_revenue_engine import (
    build_event,
    build_goclear_funnel,
    build_creative_handoff,
    experiment_plan,
    marketing_visibility,
    native_ab_validation,
    native_cro_contract,
    native_experiment_contract,
    native_landing_page_validation,
    native_marketing_mechanism_contract,
)


def test_goclear_funnel_is_claim_safe_and_structured():
    funnel = build_goclear_funnel()
    assert funnel["schema_version"] == "nexus.marketing-funnel.v1"
    assert funnel["publication_authorized"] is False
    assert funnel["paid_spend_authorized"] is False
    assert "$97" in funnel["offer"]["entry_offer"]
    assert funnel["metrics"]["revenue"] == 0


def test_event_contract_and_handoff_link_to_same_campaign():
    funnel = build_goclear_funnel()
    event = build_event(funnel, "CTA_click", creative_variant="primary")
    handoff = build_creative_handoff(funnel)
    assert event["funnel_id"] == funnel["funnel_id"]
    assert event["campaign_id"] == funnel["campaign_id"]
    assert handoff["funnel_id"] == funnel["funnel_id"]
    assert handoff["publication_authorized"] is False


def test_experiments_and_visibility_are_bounded():
    funnel = build_goclear_funnel()
    experiments = experiment_plan(funnel)
    visibility = marketing_visibility(funnel)
    assert len(experiments) == 3
    assert all(e["minimum_evidence"] for e in experiments)
    assert visibility["live_traffic"] is False
    assert visibility["campaign_live"] is False


def test_native_borrowed_mechanisms_are_executable():
    funnel = build_goclear_funnel()
    html = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>x</title><meta name="description" content="x"><link rel="canonical" href="https://example.com"><meta property="og:title" content="x"><meta property="og:description" content="x"><meta property="og:url" content="https://example.com"><meta property="og:image" content="https://example.com/x.png"></head><body data-build="build:x"><h1>x</h1><script>const TEST="x",AB_ACTIVE=true;document.cookie="__abVariant=A";gtag("event","creative_variant",{ab:"A"})</script></body></html>'
    assert native_landing_page_validation(html)["status"] == "PASS_REAL_BOUNDED"
    assert native_ab_validation(html, "x")["status"] == "PASS_REAL_BOUNDED"
    assert native_cro_contract(funnel)["status"] == "PASS_REAL_BOUNDED"
    assert native_experiment_contract(funnel)["status"] == "PASS_REAL_BOUNDED"
    assert native_marketing_mechanism_contract(funnel)["status"] == "PASS_REAL_BOUNDED"
