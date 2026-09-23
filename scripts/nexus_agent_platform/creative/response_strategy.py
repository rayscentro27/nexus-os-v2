"""Response-driven short-form creative contracts."""
from __future__ import annotations

from typing import Any, Mapping

RESPONSE_FIELDS = (
    "target_audience", "funnel_stage", "target_emotion", "target_thought",
    "desired_action", "scroll_stop_trigger", "first_1_second_event",
    "first_3_second_hook", "core_tension", "curiosity_gap", "desire_trigger",
    "trust_trigger", "action_trigger", "primary_objection", "objection_response",
    "ten_second_payoff", "cta_psychological_state",
)

STORY_FIELDS = (
    "character", "situation", "problem", "emotion", "turning_point",
    "transformation", "final_state", "desired_action", "style",
    "zero_to_two_seconds", "two_to_five_seconds", "five_to_eight_seconds",
    "eight_to_ten_seconds",
)

RESPONSE_STRATEGY_DEFAULT_MODE = "OPTIONAL_CREATIVE_GUIDANCE"


def response_guidance_payload(response: Mapping[str, Any], *, approved: bool = False) -> dict[str, Any]:
    """Expose strategy as guidance unless a campaign explicitly approves it."""
    return {
        "mode": "APPROVED_HARD_GUIDANCE" if approved else RESPONSE_STRATEGY_DEFAULT_MODE,
        "fields": {key: response.get(key) for key in RESPONSE_FIELDS if key in response},
    }


def response_strategy_policy() -> dict[str, Any]:
    return {"department": "CREATIVE", "task_class": "creative.response_strategy", "required_quality_tier": "TIER_2", "requires_structured_output": True, "requires_long_context": True, "requires_vision": False, "max_latency_ms": 75000, "max_cost_usd": 0.15, "fallback_policy": "tier_2_then_tier_1"}


def fast_story_policy() -> dict[str, Any]:
    return {"department": "CREATIVE", "task_class": "creative.fast_story_ideation", "required_quality_tier": "TIER_2", "requires_structured_output": True, "requires_long_context": False, "requires_vision": False, "max_latency_ms": 60000, "max_cost_usd": 0.10, "fallback_policy": "tier_2_then_tier_1"}


def valid_response_strategy(value: Any) -> bool:
    return isinstance(value, dict) and all(value.get(k) for k in RESPONSE_FIELDS)


def valid_story(value: Any) -> bool:
    return isinstance(value, dict) and all(value.get(k) for k in STORY_FIELDS)


def continuity_brief(response: Mapping[str, Any]) -> dict[str, Any]:
    return {"video_emotion": response.get("target_emotion"), "video_thought": response.get("target_thought"), "video_action": response.get("desired_action"), "landing_page_emotional_continuation": response.get("ten_second_payoff"), "landing_page_information_job": "Explain what readiness means and what the next useful preparation step is.", "landing_page_trust_job": "Make the education/readiness boundary explicit without promising approval.", "landing_page_primary_cta": response.get("desired_action"), "landing_page_secondary_cta": "See what to prepare first", "free_information_option": "Read the readiness checklist before starting."}
