"""Read-only Creative performance intelligence contracts.

This module stores observations and hypotheses.  It does not select creative,
rewrite prompts, or turn performance patterns into mandatory instructions.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

PERFORMANCE_SCHEMA_VERSION = "nexus.creative-performance-observation.v1"
PATTERN_SCHEMA_VERSION = "nexus.creative-pattern-observation.v1"
HANDOFF_SCHEMA_VERSION = "nexus.research-alpha-marketing-creative-handoff.v1"

PERFORMANCE_FIELDS = (
    "creative_asset_id", "campaign_id", "platform", "format", "creative_type",
    "duration", "aspect_ratio", "hook_description", "creative_style",
    "character_type", "avatar_id", "has_voice", "has_music", "cta_type",
    "impressions", "views", "chose_to_view", "thumb_stop_rate", "hook_rate",
    "three_second_view_rate", "retention", "completion_rate", "ctr",
    "comments", "shares", "saves", "leads", "conversions", "cost", "cpl",
    "source", "observed_at",
)

PATTERN_FIELDS = (
    "pattern_id", "platform", "format", "observation", "evidence_count",
    "source_references", "time_window", "confidence", "applicability",
    "saturation_signal", "notes",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record(schema_version: str, fields: tuple[str, ...], values: Mapping[str, Any]) -> dict[str, Any]:
    """Keep unknown fields out while preserving null for unavailable metrics."""
    result = {"schema_version": schema_version}
    result.update({key: values.get(key) for key in fields})
    return result


def build_performance_observation(values: Mapping[str, Any]) -> dict[str, Any]:
    """Build one normalized, read-only platform observation."""
    result = _record(PERFORMANCE_SCHEMA_VERSION, PERFORMANCE_FIELDS, values)
    result["observed_at"] = values.get("observed_at") or _now()
    if not result["creative_asset_id"] or not result["platform"] or not result["source"]:
        raise ValueError("creative_asset_id, platform, and source are required")
    return result


def build_pattern_observation(values: Mapping[str, Any]) -> dict[str, Any]:
    """Build a hypothesis/observation; this is guidance, never a rule."""
    result = _record(PATTERN_SCHEMA_VERSION, PATTERN_FIELDS, values)
    result["performance_pattern_is_guidance_not_rule"] = True
    if not result["pattern_id"] or not result["observation"]:
        raise ValueError("pattern_id and observation are required")
    return result


def build_research_alpha_marketing_creative_handoff(
    *, research: Mapping[str, Any], alpha: Mapping[str, Any], marketing: Mapping[str, Any],
    relevant_patterns: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Describe the bounded handoff without prescribing a creative answer."""
    return {
        "schema_version": HANDOFF_SCHEMA_VERSION,
        "research": dict(research),
        "alpha": dict(alpha),
        "marketing": dict(marketing),
        "relevant_performance_patterns": [dict(item) for item in (relevant_patterns or [])],
        "creative_can_depart_from_observed_pattern": True,
        "performance_pattern_is_guidance_not_rule": True,
        "creative_owns": [
            "concept", "story", "artistic_direction", "emotional_treatment", "hook",
            "visual_language", "character_usage", "avatar_usage", "animation", "humor",
            "cinematography", "sound", "pacing", "creative_execution",
        ],
    }


def feedback_loop_contract() -> dict[str, Any]:
    return {
        "stages": ["CREATIVE", "PRODUCTION", "DISTRIBUTION", "PERFORMANCE", "RESEARCH_ANALYTICS", "ALPHA", "CREATIVE_LEARNING"],
        "read_only_performance_intelligence": True,
        "single_metric_optimization": False,
        "ctr_is_universal_quality_rule": False,
        "human_or_governed_creative_review_required": True,
    }


def validate_performance_observation(value: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ("creative_asset_id", "platform", "source", "observed_at"):
        if not value.get(field):
            errors.append(f"missing:{field}")
    return errors


def validate_pattern_observation(value: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ("pattern_id", "observation"):
        if not value.get(field):
            errors.append(f"missing:{field}")
    if value.get("performance_pattern_is_guidance_not_rule") is not True:
        errors.append("pattern-must-remain-guidance")
    return errors
