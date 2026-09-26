from pathlib import Path

from nexus_agent_platform.creative.avatar_registry import (
    build_avatar_contract,
    build_brand_registry,
    identity_version_increment_required,
    validate_avatar_contract,
)
from nexus_agent_platform.creative.performance_intelligence import (
    build_pattern_observation,
    build_performance_observation,
    validate_pattern_observation,
    validate_performance_observation,
)


def test_performance_metrics_are_nullable_and_pattern_is_guidance():
    observation = build_performance_observation({
        "creative_asset_id": "asset-1", "campaign_id": "campaign-1",
        "platform": "instagram_reels", "source": "read_only_fixture",
    })
    assert observation["views"] is None
    assert validate_performance_observation(observation) == []
    pattern = build_pattern_observation({
        "pattern_id": "pattern-1", "observation": "character-led story",
        "evidence_count": 1,
    })
    assert pattern["performance_pattern_is_guidance_not_rule"] is True
    assert validate_pattern_observation(pattern) == []


def test_avatar_contract_preserves_identity_and_allows_campaign_variation():
    avatar = build_avatar_contract({
        "avatar_id": "avatar.test", "brand": "GOCLEAR", "style": "stylized",
        "reference_images": ["portrait.png"],
        "core_appearance": "same character", "prohibited_identity_changes": ["new face"],
    })
    assert validate_avatar_contract(avatar) == []
    changed = dict(avatar, core_appearance="different character", allowed_variation=["pose"])
    assert identity_version_increment_required(avatar, changed) is True
    assert identity_version_increment_required(avatar, dict(avatar, allowed_variation=["pose"])) is False


def test_brand_registry_blocks_random_reinvention():
    registry = build_brand_registry({"GOCLEAR": {"canonical_assets": {"logo": "logo.svg"}}})
    assert registry["brands"]["GOCLEAR"]["random_brand_reinvention"] == "BLOCKED"
