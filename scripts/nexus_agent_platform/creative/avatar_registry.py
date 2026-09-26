"""Versioned Creative avatar and canonical brand-asset contracts.

The registry protects identity and canonical brand assets while leaving campaign
story, mood, wardrobe, setting, and usage optional to Creative.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Mapping

AVATAR_SCHEMA_VERSION = "nexus.creative-avatar-contract.v1"
BRAND_SCHEMA_VERSION = "nexus.creative-brand-asset-registry.v1"
AVATAR_USAGE_OPTIONAL = True

AVATAR_FIELDS = (
    "avatar_id", "avatar_name", "brand", "role", "style", "version",
    "reference_images", "reference_video", "face_reference", "body_reference",
    "voice_id", "voice_provider", "voice_reference", "core_appearance",
    "age_range", "hair", "facial_features", "skin_tone", "body_type",
    "default_wardrobe", "optional_wardrobe_variants", "personality",
    "gesture_style", "voice_style", "brand_color_relationship", "allowed_variation",
    "prohibited_identity_changes", "created_at", "updated_at", "status",
)

IDENTITY_FIELDS = ("core_appearance", "age_range", "hair", "facial_features", "skin_tone", "body_type", "voice_id")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_avatar_contract(values: Mapping[str, Any]) -> dict[str, Any]:
    result = {"schema_version": AVATAR_SCHEMA_VERSION}
    result.update({key: deepcopy(values.get(key)) for key in AVATAR_FIELDS})
    result["version"] = result["version"] or "AVATAR_V1"
    result["created_at"] = result["created_at"] or _now()
    result["updated_at"] = result["updated_at"] or result["created_at"]
    result["status"] = result["status"] or "DRAFT"
    result["avatar_usage_optional"] = True
    result["identity_persistence_policy"] = "preserve_identity; version any material identity change"
    missing = [key for key in ("avatar_id", "brand", "style", "version", "reference_images") if not result.get(key)]
    if missing:
        raise ValueError("missing avatar fields: " + ",".join(missing))
    return result


def identity_version_increment_required(previous: Mapping[str, Any], current: Mapping[str, Any]) -> bool:
    return any(previous.get(key) != current.get(key) for key in IDENTITY_FIELDS)


def validate_avatar_contract(value: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("avatar_id", "brand", "version", "reference_images", "prohibited_identity_changes"):
        if not value.get(key):
            errors.append(f"missing:{key}")
    if value.get("avatar_usage_optional") is not True:
        errors.append("avatar-usage-must-be-optional")
    return errors


def build_brand_registry(values: Mapping[str, Any]) -> dict[str, Any]:
    result = {"schema_version": BRAND_SCHEMA_VERSION, "brands": deepcopy(dict(values))}
    for brand_id, brand in result["brands"].items():
        if not brand.get("brand_id"):
            brand["brand_id"] = brand_id
        brand["random_brand_reinvention"] = "BLOCKED"
    return result


def canonical_brand_asset(registry: Mapping[str, Any], brand_id: str, asset_key: str) -> str | None:
    brand = (registry.get("brands") or {}).get(brand_id) or {}
    return (brand.get("canonical_assets") or {}).get(asset_key)


def avatar_namespaces() -> dict[str, str]:
    return {"NEXUS_OS": "avatar.nexus.primary", "GOCLEAR": "avatar.goclear.primary"}
