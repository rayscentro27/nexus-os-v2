"""Canonical Marketing Distribution Layer V1 contracts and fail-closed adapters."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

SOCIAL_CHANNELS = ("facebook", "instagram", "linkedin", "youtube", "tiktok", "x")
SOCIAL_ACTIONS = ("READ", "ANALYZE", "DRAFT", "SCHEDULE", "PUBLISH", "COMMENTS_READ", "COMMENTS_REPLY", "METRICS")
ALL_CHANNELS = ("instagram", "facebook", "tiktok", "youtube", "linkedin", "x", "pinterest", "google_business_profile")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}_{hashlib.sha256(repr(value).encode()).hexdigest()[:16]}"


def social_capability_schema() -> dict[str, Any]:
    return {"schema_version": "nexus.marketing-social-capability.v1", "capability_ids": {f"marketing.social.{c}": list(SOCIAL_ACTIONS) for c in SOCIAL_CHANNELS}, "receipt_required": True, "provider_evidence_required": True}


def social_permission_matrix() -> dict[str, str]:
    return {"READ": "AUTONOMOUS", "ANALYZE": "AUTONOMOUS", "DRAFT": "AUTONOMOUS", "SCHEDULE": "EXISTING_NEXUS_POLICY", "PUBLISH": "EXISTING_NEXUS_POLICY", "PAID_BOOST": "APPROVAL_REQUIRED", "AD_SPEND": "APPROVAL_REQUIRED", "BUDGET_CHANGE": "APPROVAL_REQUIRED"}


def email_capability_schema() -> dict[str, Any]:
    return {"schema_version": "nexus.marketing-email-capability.v1", "capabilities": ["marketing.email.draft", "marketing.email.send_test", "marketing.email.send", "marketing.email.schedule", "marketing.email.segment", "marketing.email.metrics", "marketing.email.unsubscribe"], "receipt_required": True, "delivery_not_inferred_from_acceptance": True}


def email_permission_matrix() -> dict[str, str]:
    return {"TEST_EMAIL": "APPROVED_TEST_RECIPIENT_ONLY", "TRANSACTIONAL_OPERATIONAL_EMAIL": "GOVERNED_EXISTING_PATH", "MARKETING_NURTURE_EMAIL": "CONSENT_AND_APPROVAL_REQUIRED", "BULK_EMAIL": "BLOCKED_FOR_THIS_MISSION", "UNSUBSCRIBE": "ALWAYS_HONORED"}


def channel_adaptation(channel: str, base_hook: str, base_caption: str) -> dict[str, Any]:
    if channel not in SOCIAL_CHANNELS:
        raise ValueError(f"unsupported channel: {channel}")
    presets = {
        "facebook": {"hook_max": 80, "format": "feed/link", "cta": "Learn more", "asset": "1:1 or 4:5", "cadence": "2-3/week"},
        "instagram": {"hook_max": 70, "format": "reel/carousel", "cta": "Save and share", "asset": "4:5 or 9:16", "cadence": "3/week"},
        "linkedin": {"hook_max": 100, "format": "professional feed", "cta": "Review the checklist", "asset": "1:1 or 1.91:1", "cadence": "2/week"},
        "youtube": {"hook_max": 100, "format": "short/video", "cta": "Watch the next step", "asset": "16:9 or 9:16", "cadence": "1-2/week"},
        "tiktok": {"hook_max": 60, "format": "short video", "cta": "Comment your question", "asset": "9:16", "cadence": "3/week"},
        "x": {"hook_max": 70, "format": "short post/thread", "cta": "Read the guide", "asset": "1:1 or 16:9", "cadence": "3-5/week"},
    }
    p = presets[channel]
    return {"channel": channel, "hook": base_hook[:p["hook_max"]], "caption": base_caption, **p}


def social_metric_schema() -> dict[str, Any]:
    return {"schema_version": "nexus.marketing-social-metric.v1", "fields": ["impressions", "reach", "views", "watch_time", "likes", "comments", "shares", "saves", "link_clicks", "profile_visits", "followers_delta"], "availability": "provider_specific", "unknown_is_null": True}


def attribution_schema() -> dict[str, Any]:
    return {"schema_version": "nexus.marketing-attribution.v1", "fields": ["utm_source", "utm_medium", "utm_campaign", "utm_content", "creative_variant", "distribution_id"], "conversion_claim_requires_event": True}


def retry_policy() -> dict[str, Any]:
    return {"schema_version": "nexus.marketing-distribution-retry.v1", "auth_failure": "HOLD_AND_ESCALATE", "rate_limit": "EXPONENTIAL_BACKOFF_MAX_3", "provider_rejection": "HOLD_NO_AUTORETRY_UNLESS_TRANSIENT", "invalid_asset": "HOLD_FOR_REVISION", "network_timeout": "RETRY_MAX_2_THEN_VERIFY", "visibility": "nexus_events_plus_distribution_record", "never": ["duplicate_send_without_idempotency", "claim_delivery_without_provider_receipt"]}


def nurture_sequences(funnel_id: str) -> list[dict[str, Any]]:
    specs = [("new_lead", "lead_created", "orient and offer the next safe readiness step", "Start the readiness review", "lead converts or unsubscribes", "readiness_review_started"), ("incomplete_readiness_review", "review_started_and_incomplete", "help finish missing evidence", "Continue the review", "review completed or unsubscribed", "readiness_review_completed"), ("qualified_lead", "qualification_passed", "move to governed appointment choice", "Request an appointment", "appointment booked or unsubscribed", "appointment_booked"), ("appointment_reminder", "appointment_booked", "reduce missed appointments", "Confirm appointment", "appointment occurs or cancelled", "appointment_completed"), ("non_buyer_nurture", "review_completed_no_purchase", "provide educational next steps without pressure", "Review your next action", "purchase or unsubscribed", "return_visit"), ("post_review_follow_up", "review_completed", "summarize next actions and invite questions", "Open your readiness summary", "follow-up completed or unsubscribed", "follow_up_engaged")]
    return [{"sequence_id": f"goclear_{name}", "funnel_id": funnel_id, "name": name, "trigger": trigger, "message_objective": objective, "cta": cta, "delay_cadence": "bounded_draft_only", "stop_condition": stop, "success_event": success, "status": "DRAFT_NOT_SENT"} for name, trigger, objective, cta, stop, success in specs]


def distribution_record(campaign_id: str, funnel_id: str, channel: str, content_id: str, provider: str | None = None) -> dict[str, Any]:
    return {"distribution_id": stable_id("dist", (campaign_id, funnel_id, channel, content_id)), "campaign_id": campaign_id, "funnel_id": funnel_id, "channel": channel, "content_id": content_id, "provider": provider, "status": "DRAFT", "cost": 0, "retry_state": {"attempts": 0, "state": "NOT_STARTED"}, "created_at": now(), "updated_at": now()}


def content_acquisition_formula() -> dict[str, Any]:
    """The governed Research → Creative → Meta → Marketing learning contract."""
    return {
        "schema_version": "nexus.content-acquisition-formula.v1",
        "stages": ["RESEARCH", "ALPHA", "CREATIVE", "PROMPT_ARCHITECT", "META", "CAMPAIGN_PACKAGE", "POST_CREATION_REVIEW", "MARKETING", "DISTRIBUTION", "ENGAGEMENT_ANALYTICS", "NEXT_POST_DECISION"],
        "research_finds_attention": True,
        "research_provides_mechanisms_not_final_concepts": True,
        "startup_attention_first_doctrine": True,
        "prompt_architect_role": "TRANSLATOR_PACKAGER",
        "prompt_architect_creative_substitutions": 0,
        "marketing_prewrite_creative": False,
        "performance_is_guidance_not_rule": True,
        "auto_publish": False,
        "auto_spend": False,
    }


def external_long_running_job_rule() -> dict[str, Any]:
    return {
        "schema_version": "nexus.external-long-running-job.v1",
        "persist_job_state": True,
        "release_browser_worker": True,
        "reattach_same_session": True,
        "progress_resets_stall_timer": True,
        "elapsed_time_is_not_failure": True,
        "default_meta_recheck_minutes": 10,
        "classifications": ["IN_PROGRESS", "COMPLETED", "TRANSIENT_FAILURE", "RATE_LIMIT", "SESSION_FAILURE", "PROVIDER_ERROR", "STALLED", "HUMAN_REQUIRED"],
        "retry_policy": "bounded; no refresh storms or identity cycling",
    }


def channel_access_registry_schema() -> dict[str, Any]:
    return {
        "schema_version": "nexus.channel-access-registry.v1",
        "fields": ["business_id", "platform", "account_identifier", "account_exists", "auth_status", "read_access", "publish_access", "analytics_access", "comment_access", "dm_access", "token_expiration_if_known", "last_health_check", "connection_method", "credential_reference", "status"],
        "statuses": ["CONNECTED", "READ_ONLY", "PUBLISH_READY", "ANALYTICS_READY", "AUTH_EXPIRED", "NOT_CONNECTED", "UNKNOWN", "BLOCKED_EXTERNAL"],
        "credential_values_never_exposed": True,
    }


def engagement_schema() -> dict[str, Any]:
    return {
        "schema_version": "nexus.marketing-engagement.v1",
        "fields": ["platform", "post_id", "engagement_type", "author_reference", "text", "timestamp", "parent_comment", "sentiment_if_used", "classification", "response_status"],
        "classifications": ["QUESTION", "OBJECTION", "CONFUSION", "INTEREST", "POSITIVE_REACTION", "NEGATIVE_REACTION", "CUSTOMER_PROBLEM", "CONTENT_IDEA", "PRODUCT_QUESTION", "FUNDING_QUESTION", "CREDIT_QUESTION", "BUSINESS_SETUP_QUESTION", "SPAM", "OTHER"],
        "public_auto_reply": False,
    }


def distribution_plan_record(campaign_id: str, asset_id: str, channel: str, *, purpose: str, audience: str, caption: str, cta: str, destination: str | None, schedule_window: str, timezone: str = "America/Phoenix") -> dict[str, Any]:
    if channel not in ALL_CHANNELS:
        raise ValueError(f"unsupported channel: {channel}")
    return {
        "distribution_id": stable_id("dist", (campaign_id, asset_id, channel, purpose)),
        "campaign_id": campaign_id,
        "asset_id": asset_id,
        "channel": channel,
        "purpose": purpose,
        "audience": audience,
        "caption": caption,
        "cta": cta,
        "destination": destination,
        "schedule_window": schedule_window,
        "timezone": timezone,
        "approval_status": "NOT_SUBMITTED",
        "publish_status": "DRAFT",
        "auto_publish": False,
        "publication_receipt": None,
    }


def next_post_decision(metrics: list[dict[str, Any]] | None = None, engagement: list[dict[str, Any]] | None = None, research: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Return an evidence-aware recommendation without fabricating causality."""
    rows = metrics or []
    if not rows:
        return {"schema_version": "nexus.next-post-decision.v1", "status": "NO_FIRST_PARTY_DATA", "observation": "No published GoClear performance rows are available.", "hypothesis": None, "test": "Collect first-party post metrics after an approved publication.", "supported_learning": None, "recommendation": "HOLD_FOR_FIRST_PARTY_DATA", "fabricated_metrics": False}
    return {"schema_version": "nexus.next-post-decision.v1", "status": "REVIEW_REQUIRED", "observation": "Metrics available; attribution and sample quality require review.", "hypothesis": "UNFORMED", "test": "Compare like-format assets with platform context.", "supported_learning": None, "recommendation": "RESEARCH_ALPHA_REVIEW_REQUIRED", "fabricated_metrics": False}


def campaign_package_schema() -> dict[str, Any]:
    return {"schema_version": "nexus.campaign-package.v1", "fields": ["campaign_id", "business_id", "campaign_objective", "business_foundation", "research_packet", "alpha_review", "creative_opportunity", "exact_meta_brief", "meta_conversation", "meta_assets", "videos", "images", "copy", "captions", "funnel_artifacts", "landing_page_artifacts", "claims_ledger", "creative_review", "compliance_review", "finance_review_if_needed", "marketing_status", "distribution_plan", "schedule", "publication_receipts", "engagement_metrics", "performance_analysis", "next_post_decision"], "no_orphan_assets": True}
