"""Contract tests for Nexus Creative Provider Router."""
import pytest
from scripts.creative.creative_provider_router import (
    CREATIVE_ROUTING_TABLE,
    DISALLOWED_CREATIVE_PROVIDERS,
    DETERMINISTIC_MEDIA_PRODUCTION_ROUTABLE,
    LOCAL_CREATIVE_SUBSTITUTE_ALLOWED,
    select_creative_provider,
    handle_provider_failure,
)


def test_deterministic_media_not_routable_for_production():
    """Verify deterministic/local media is NOT a production creative fallback."""
    assert DETERMINISTIC_MEDIA_PRODUCTION_ROUTABLE is False
    assert LOCAL_CREATIVE_SUBSTITUTE_ALLOWED is False
    assert "deterministic_media" in DISALLOWED_CREATIVE_PROVIDERS
    assert "slideshow_substitute" in DISALLOWED_CREATIVE_PROVIDERS
    assert "local_ffmpeg_substitute" in DISALLOWED_CREATIVE_PROVIDERS

    for category, routing in CREATIVE_ROUTING_TABLE.items():
        assert routing.get("fallback") != "deterministic_media", (
            f"Category {category} must not have deterministic_media as fallback"
        )
        assert routing.get("primary") != "deterministic_media"
        assert routing.get("secondary") != "deterministic_media"


def test_provider_selection_without_substitute_fallback():
    """When all providers fail, router must return PROVIDER_UNAVAILABLE rather than fallback."""
    decision = select_creative_provider(
        "PRODUCT_IMAGES",
        failed_providers=["meta_ai_browser_creative", "modal"]
    )
    assert decision["status"] == "PROVIDER_UNAVAILABLE"
    assert decision["selected_provider"] is None


def test_vertical_shorts_routing_prefers_modal():
    """Vertical shorts (9:16) routes to Modal as primary when spend approved."""
    decision = select_creative_provider("VERTICAL_SHORTS", approved_spend=1.0)
    assert decision["status"] == "ROUTED"
    assert decision["selected_provider"] == "modal"


def test_vertical_shorts_requires_approval_if_unfunded():
    """Vertical shorts requires Ray approval when approved spend is 0."""
    decision = select_creative_provider("VERTICAL_SHORTS", approved_spend=0.0)
    assert decision["status"] == "WAITING_FOR_RAY_APPROVAL"
    assert decision["selected_provider"] == "modal"


def test_failure_rerouting_preserves_lineage_and_prohibits_substitutes():
    """Reroute handles failure cleanly without permitting local substitute media."""
    res = handle_provider_failure(
        creative_request_id="cr_test_12345",
        category="PRODUCT_IMAGES",
        failed_provider="meta_ai_browser_creative",
        error_reason="CDP connection dropped"
    )
    assert res["creative_request_id"] == "cr_test_12345"
    assert res["failed_provider"] == "meta_ai_browser_creative"
    assert res["local_agent_substitute_permitted"] is False
    assert "meta_ai_browser_creative" in res["attempted_providers"]
